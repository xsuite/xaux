# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
from shutil import rmtree
from pathlib import Path, PurePosixPath, PureWindowsPath


def _non_strict_resolve(path, _as_posix=False):
    # This function is resolving without strict=True as this 
    # might lead to infinite loops in case of broken links.
    if not isinstance(path, Path):
        path = Path(path)
    cls = path.__class__
    path = path.expanduser().as_posix()
    path = os.path.realpath(path, strict=False)
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
        if isinstance(new_path, EosPath):
            return EosPath(new_path.eos_path)
        else:
            return new_path

    def exists(self, *args, **kwargs):
        if self.is_symlink():
            return self.resolve().exists()
        return Path.exists(self, *args, **kwargs)


    # New methods
    # ===========

    def lexists(self):
        return self.is_symlink() or self.exists()

    def is_broken_symlink(self):
        return self.is_symlink() and not self.exists()

    def rmtree(self, *args, **kwargs):
        if not self.is_dir():
            raise NotADirectoryError(f"{self} is not a directory.")
        rmtree(self.resolve().as_posix(), *args, **kwargs)

    def copy_to(self, dst, *args, **kwargs):
        from .io import cp
        cp(self, dst, *args, **kwargs)

    def move_to(self, dst, *args, **kwargs):
        from .io import mv
        mv(self, dst, *args, **kwargs)

    def size(self, *args, **kwargs):
        return self.stat().st_size


# To give regular Path objects the same functionality as FsPath objects
class LocalPath(FsPath, Path):
    """Path subclass for local paths.

    Instantiating an FsPath should call this class.
    """

    def __new__(cls, *args):
        if cls is LocalPath:
            cls = LocalWindowsPath if os.name == 'nt' else LocalPosixPath
        self = cls._from_parts(args)
        if not self._flavour.is_supported:
            raise OSError(f"cannot instantiate {cls.__name__} "
                         + "on your system.")
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

