# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
from shutil import rmtree
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath


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
    def __new__(cls, *args):
        from .eos import EosPath, _on_eos
        from .afs import AfsPath, _on_afs
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

    @classmethod
    def _from_parts(cls, args, in__new__=False, init=True):
        # We need to call _parse_args on the instance, so as to get the
        # right flavour.
        self = object.__new__(cls)
        drv, root, parts = self._parse_args(args)
        self._drv = drv
        self._root = root
        self._parts = parts
        if init and hasattr(self, '_init'):
            self._init()
        if in__new__:
            return self
        else:
            return FsPath(self)

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, in__new__=False, init=True):
        self = object.__new__(cls)
        self._drv = drv
        self._root = root
        self._parts = parts
        if init and hasattr(self, '_init'):
            self._init()
        if in__new__:
            return self
        else:
            return FsPath(self)

    @property
    def _unnested_parent(self):
        drv = self._drv
        root = self._root
        parts = self._parts
        if len(parts) == 1 and (drv or root):
            return self
        return self._from_parsed_parts(drv, root, parts[:-1], in__new__=True)


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
            new_path = FsPath(Path.resolve(self))
        # And then we get back the correct EOS path
        # This extra step is needed because the final path might not be on EOS
        if isinstance(new_path, EosPath):
            return EosPath(new_path.eos_path)
        else:
            return new_path

    def exists(self, *args, **kwargs):
        if self.is_symlink(*args, **kwargs):
            return self.resolve(*args, **kwargs).exists(*args, **kwargs)
        return Path.exists(self, *args, **kwargs)

    def symlink_to(self, target, target_is_directory=False, **kwargs):
        target = FsPath(target)
        return Path.symlink_to(self.resolve(**kwargs), target,
                                 target_is_directory=target.is_dir(**kwargs), **kwargs)

    def unlink(self, *args, **kwargs):
        if not self.is_symlink(*args, **kwargs) and self.is_dir(*args, **kwargs):
            raise IsADirectoryError(f"{self} is a directory.")
        Path.unlink(self, *args, **kwargs)

    def rmdir(self, *args, **kwargs):
        if not self.is_dir(*args, **kwargs):
            raise NotADirectoryError(f"{self} is not a directory.")
        Path.rmdir(self, *args, **kwargs)

    # TODO mv and rename replace etc

    # New methods
    # ===========

    def lexists(self, *args, **kwargs):
        return self.is_symlink(*args, **kwargs) or self.exists(*args, **kwargs)

    def is_broken_symlink(self, *args, **kwargs):
        return self.is_symlink(*args, **kwargs) and not self.exists(*args, **kwargs)

    def rmtree(self, *args, **kwargs):
        if not self.is_dir(*args, **kwargs):
            raise NotADirectoryError(f"{self} is not a directory.")
        return rmtree(self.resolve(*args, **kwargs).as_posix(*args, **kwargs), *args, **kwargs)

    def copy_to(self, dst, recursive=None, *args, **kwargs):
        from .io import cp
        if recursive is None:
            recursive = self.is_dir(*args, **kwargs)
        return cp(self, dst, *args, recursive=recursive, **kwargs)

    def move_to(self, dst, *args, **kwargs):
        from .io import mv
        return mv(self, dst, *args, **kwargs)

    def size(self, *args, **kwargs):
        return self.stat(*args, **kwargs).st_size


# To give regular Path objects the same functionality as FsPath objects
class LocalPath(FsPath, Path):
    """Path subclass for local paths.

    Instantiating an FsPath should call this class.
    """

    def __new__(cls, *args):
        if cls is LocalPath:
            cls = LocalWindowsPath if os.name == 'nt' else LocalPosixPath
        try:
            self = cls._from_parts(args, in__new__=True).expanduser()
        except AttributeError:
            self = object.__new__(cls).expanduser()
        return self


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

