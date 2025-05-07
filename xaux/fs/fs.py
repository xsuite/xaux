# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os, sys
from subprocess import run, PIPE, CalledProcessError
from time import sleep
from shutil import rmtree
from contextlib import contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath


def _non_strict_resolve(path, _as_posix=False):
    # This function is resolving without strict=True as this 
    # might lead to infinite loops in case of broken links.
    if not isinstance(path, Path):
        path = Path(path)
    cls = path.__class__
    path = path.expanduser().as_posix()
    try:
        path = os.path.realpath(path, strict=False)
    except TypeError:
        path = os.path.realpath(path)
    if _as_posix:
        return path
    else:
        return cls(path)


class FsPath:
    """Factory that generates either an EosPath, AfsPath, or LocalPath
    depending on the file system the path is on. Note that a LocalPath
    is just a regular Path object but with access to the FsPath methods.
    """
    __slots__ = ()

    def __new__(cls, *args):
        from .eos import EosPath, _on_eos
        from .afs import AfsPath, _on_afs
        if len(args) == 0:
            args = ('.',)
        if _on_eos(*args):
            return EosPath.__new__(EosPath, *args, _eos_checked=True)
        elif _on_afs(*args):
            return AfsPath.__new__(AfsPath, *args, _afs_checked=True)
        else:
            return LocalPath.__new__(LocalPath, *args)

    # FsPath is not a subclass of Path. We get the instance methods
    # from Path via the derived classes (EosPath etc), but we have to
    # define the public class methods manually.

    @classmethod
    def cwd(cls):
        return cls(Path.cwd())

    @classmethod
    def home(cls):
        return cls(Path.home())


    # PurePath methods
    # ================

    if sys.version_info >= (3, 12):
        def with_segments(self, *pathsegments, _cast_as_fspath=True, _force_path=False):
            if _cast_as_fspath:
                return FsPath(*pathsegments)
            elif _force_path:
                return Path(*pathsegments)
            else:
                return type(self)(*pathsegments)

        # We create a contextmanager to avoid casting to FsPath in the constructor
        @classmethod
        @contextmanager
        def _in_constructor(cls, _force=False):
            original_with_segments = cls.with_segments
            def new_with_segments(self, *args, **kwargs):
                return original_with_segments(self, *args, _cast_as_fspath=False,
                                              _force_path=_force, **kwargs)
            cls.with_segments = new_with_segments
            try:
                yield
            finally:
                cls.with_segments = original_with_segments
                # cls.parent = original_parent

    else:
        @classmethod
        def _from_parts(cls, args, _cast_as_fspath=True, _force_path=False, **kwargs):
            if _cast_as_fspath:
                return FsPath(super(Path, cls)._from_parts(args, **kwargs))
            elif _force_path:
                return Path(super(Path, cls)._from_parts(args, **kwargs))
            else:
                return super(Path, cls)._from_parts(args, **kwargs)

        @classmethod
        def _from_parsed_parts(cls, *args, _cast_as_fspath=True, _force_path=False, **kwargs):
            if _cast_as_fspath:
                return FsPath(super(Path, cls)._from_parsed_parts(*args, **kwargs))
            elif _force_path:
                return Path(super(Path, cls)._from_parsed_parts(*args, **kwargs))
            else:
                return super(Path, cls)._from_parsed_parts(*args, **kwargs)

        # We create a contextmanager to avoid casting to FsPath in the constructor
        @classmethod
        @contextmanager
        def _in_constructor(cls, _force=False):
            original_from_parts = cls._from_parts
            @classmethod
            def new_from_parts(cls, args, **kwargs):
                return original_from_parts(args, _cast_as_fspath=False,
                                           _force_path=_force, **kwargs)
            cls._from_parts = new_from_parts
            original_from_parsed_parts = cls._from_parsed_parts
            @classmethod
            def new_from_parsed_parts(cls, *args, **kwargs):
                return original_from_parsed_parts(*args, _cast_as_fspath=False,
                                                  _force_path=_force, **kwargs)
            cls._from_parsed_parts = new_from_parsed_parts
            try:
                yield
            finally:
                cls._from_parts = original_from_parts
                cls._from_parsed_parts = original_from_parsed_parts


    # Overwrite Path methods
    # ======================

    # Resolving EOS paths can be tricky due to different mount points.
    # Luckily, the path is already resolved at instantiation.
    def resolve(self, *args, **kwargs):
        # We first resolve all internal symlinks
        from .eos import EosPath
        if isinstance(self, EosPath):
            new_path = FsPath(_non_strict_resolve(Path(self.eos_path), _as_posix=True))
        else:
            new_path = FsPath(Path.resolve(Path(self).expanduser()))
        # And then we get back the correct EOS path
        # This extra step is needed because the final path might not be on EOS
        if isinstance(new_path, EosPath):
            return EosPath(new_path.eos_path)
        else:
            return new_path

    def is_file(self, *args, **kwargs):
        return Path.is_file(self.expanduser(), *args, **kwargs)

    def is_dir(self, *args, **kwargs):
        return Path.is_dir(self.expanduser(), *args, **kwargs)

    def is_symlink(self, *args, **kwargs):
        return Path.is_symlink(self.expanduser(), *args, **kwargs)

    def exists(self, *args, **kwargs):
        if self.is_symlink(*args, **kwargs):
            return self.resolve(*args, **kwargs).exists(*args, **kwargs)
        return Path.exists(self.expanduser(), *args, **kwargs)

    def symlink_to(self, target, target_is_directory=False, **kwargs):
        target = FsPath(target)
        return Path.symlink_to(self.expanduser().resolve(**kwargs), target.expanduser(),
                               target_is_directory=target.is_dir(**kwargs), **kwargs)

    def unlink(self, *args, **kwargs):
        if not self.is_symlink(*args, **kwargs) and self.is_dir(*args, **kwargs):
            raise IsADirectoryError(f"{self} is a directory.")
        Path.unlink(self.expanduser(), *args, **kwargs)

    def rmdir(self, *args, **kwargs):
        if not self.is_dir(*args, **kwargs):
            raise NotADirectoryError(f"{self} is not a directory.")
        Path.rmdir(self.expanduser(), *args, **kwargs)

    def __eq__(self, other):
        other = FsPath(other).expanduser().resolve()
        self = self.expanduser().resolve()
        return self.as_posix() == other.as_posix()

    def __ne__(self, other):
        return not self.__eq__(other)


    # New methods
    # ===========

    def getfid(self):
        cmd = run(['ls', '-i', self.expanduser().as_posix()],
                    stdout=PIPE, stderr=PIPE)
        if cmd.returncode == 0:
            stdout = cmd.stdout.decode('UTF-8').strip()
            return int(stdout.split()[0])
        return -1

    def flush(self):
        cmd = run(['sync', self.expanduser().as_posix()],
                    stdout=PIPE, stderr=PIPE)
        if cmd.returncode:
            sleep(1)
        self.touch()

    def lexists(self, *args, **kwargs):
        return self.is_symlink(*args, **kwargs) or self.exists(*args, **kwargs)

    def is_broken_symlink(self, *args, **kwargs):
        return self.is_symlink(*args, **kwargs) and not self.exists(*args, **kwargs)

    def rmtree(self, *args, **kwargs):
        if not self.is_dir(*args, **kwargs):
            raise NotADirectoryError(f"{self} is not a directory.")
        return rmtree(self.expanduser().resolve(*args, **kwargs).as_posix(*args, **kwargs), *args, **kwargs)

    def copy_to(self, dst, recursive=None, *args, **kwargs):
        from .io import cp
        if recursive is None:
            recursive = self.is_dir(*args, **kwargs)
        return cp(self, dst, *args, recursive=recursive, **kwargs)

    def move_to(self, dst, *args, **kwargs):
        from .io import mv
        return mv(self, dst, *args, **kwargs)

    def size(self, *args, **kwargs):
        return self.expanduser().stat(*args, **kwargs).st_size


# To give regular Path objects the same functionality as FsPath objects
class LocalPath(FsPath, Path):
    """Path subclass for local paths.

    Instantiating an FsPath should call this class.
    """

    def __new__(cls, *args):
        if cls is LocalPath:
            cls = LocalWindowsPath if os.name == 'nt' else LocalPosixPath
        with cls._in_constructor():
            try:
                self = cls._from_parts(args)
            except AttributeError:
                self = Path.__new__(cls, *args)
        return self

    def __init__(self, *args):
        with self.__class__._in_constructor():
            if sys.version_info >= (3, 12):
                Path.__init__(self, *args)
            else:
                Path.__init__(self)


class LocalPosixPath(LocalPath, PurePosixPath):
    """LocalPath subclass for local paths on non-Windows systems.

    On a POSIX system, instantiating an FsPath or a LocalPath
    should return this object.
    """
    __slots__ = ()

    if os.name == 'nt':
        def __new__(cls, *args, **kwargs):
            raise OSError(
                f"Cannot instantiate {cls.__name__!r} on your system")


class LocalWindowsPath(LocalPath, PureWindowsPath):
    """LocalPath subclass for local paths on Windows systems.

    On a Windows system, instantiating an FsPath or a LocalPath
    should return this object.
    """
    __slots__ = ()

    if os.name != 'nt':
        def __new__(cls, *args, **kwargs):
            raise OSError(
                f"Cannot instantiate {cls.__name__!r} on your system")

