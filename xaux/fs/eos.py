# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
from pathlib import Path, PurePosixPath, PureWindowsPath

from .fs import FsPath, _non_strict_resolve
from .eos_methods import _eos_path, _eos_exists, _eos_stat, _eos_lstat, _eos_is_file, \
                         _eos_is_dir, _eos_is_symlink, _eos_touch, _eos_symlink_to, \
                         _eos_unlink, _eos_mkdir, _eos_rmdir, _eos_rmtree, _eos_size

def _on_eos(*args):
    if isinstance(args[0], str):
        if args[0] == '/eos' or args[0].startswith('/eos/'):
            return True
        elif args[0].startswith('root://eos'):
            return True
        elif args[0].startswith('root:'):
            raise ValueError(f"Unknown path specification {args}.")
        elif args[0] == '/' and len(args) > 1 \
        and (args[1] == 'eos' or args[1] == 'eos/'):
            return True
    parents = list(_non_strict_resolve(Path(*args).expanduser().absolute().parent).parents)
    return len(parents) > 1 and parents[-2] == _eos_path

def _parse_instance(eos_instance):
    if eos_instance == 'home':
        return 'user'
    return eos_instance.lower()

def _parse_mgm(_eos_mgm):
    from xaux.fs import EOS_CELL
    if not isinstance(_eos_mgm, str):
        raise ValueError("The variable `_eos_mgm` should be a string.")
    if not _eos_mgm.startswith('root:'):
        raise ValueError("The variable `_eos_mgm` should start with 'root:'!")
    parts = _eos_mgm.split('/')
    if parts[1] != '' or not parts[2].startswith('eos'):
        raise ValueError(f"Invalid EOS path specification: {_eos_mgm}. "
                        + "The full path should start with 'root://eos...'.")
    if len(parts) >= 3 and parts[3] != '':
        raise ValueError(f"Invalid EOS path specification: {_eos_mgm}. "
                        + "The full path should have a double slash // "
                        + "in between the MGM and the path itself. \n"
                        + "Example: 'root://eosuser.cern.ch//eos/user/s/...'.")
    mgm_parts = parts[2].split('.')
    eos_instance = _parse_instance(mgm_parts[0].replace('eos', ''))
    if '.'.join(mgm_parts[1:]).lower() != EOS_CELL.lower():
        raise ValueError(f"This instance is on the cell {mgm_parts[1:]}, "
                       + f"but the code is configured for cell {EOS_CELL}. "
                       + f"Please set `xaux.fs.EOS_CELL = {mgm_parts[1:]}` "
                       + f"after importing xaux.")
    mgm = f'root://eos{eos_instance}.{EOS_CELL.lower()}'
    eos_path = '/'.join(parts[3:]) if len(parts) >= 3 else None
    return mgm, eos_instance, eos_path


class EosPath(FsPath, Path):
    """Path subclass for EOS paths.

    Instantiating an FsPath should call this class.
    """
    __slots__ = ('mgm', 'eos_instance', 'eos_path', 'eos_path_full')


    @classmethod
    def _new(cls, *args, _eos_checked=False):
        try:
            self = cls._from_parts(args).expanduser()
        except AttributeError:
            self = object.__new__(cls).expanduser()
        if not _eos_checked and not _on_eos(self):
            raise ValueError("The path is not on EOS.")
        return self


    def __new__(cls, *args, _eos_checked=False, _eos_mgm=None):
        if cls is EosPath:
            cls = EosWindowsPath if os.name == 'nt' else EosPosixPath
        if isinstance(args[0], str) \
        and args[0].startswith('root:'):
            if len(args) > 1:
                raise ValueError("When specifying the instance `root://eos...` "
                               + "in the path, the latter has to be given as "
                               + "one complete string.")
            mgm, eos_instance, eos_path = _parse_mgm(args[0])
            if eos_path is None:
                raise ValueError("When specifying the instance `root://eos...` "
                               + "in the path, the latter has to be given as "
                               + "one complete string.")
            self = cls._new(eos_path, _eos_checked=_eos_checked)
            self._set_eos_path(_eos_instance=eos_instance)
            if _eos_mgm is not None and mgm != _parse_mgm(_eos_mgm)[0]:
                raise ValueError(f"The specified MGM {_eos_mgm} does not match "
                               + f"the resolved one {mgm}.")
            self.mgm = mgm
        else:
            self = cls._new(*args, _eos_checked=_eos_checked)
            if _eos_mgm is not None:
                mgm, eos_instance, _ = _parse_mgm(_eos_mgm)
                self._set_eos_path(_eos_instance=eos_instance)
                self.mgm = mgm
            else:
                from xaux.fs import EOS_CELL
                self._set_eos_path()
                self.mgm = f'root://eos{self.eos_instance}.{EOS_CELL.lower()}'
        self.eos_path_full = f'{self.mgm}/{self.eos_path}'
        # try:
        #     self._accessor.scandir = scandir
        # except AttributeError:
        #     self._scandir = scandir
        return self


    def _set_eos_path(self, _eos_instance=None):
        parts = _non_strict_resolve(self.parent, _as_posix=True).split('/')
        if len(parts) == 2:
            parts = _non_strict_resolve(self, _as_posix=True).split('/')
        instance_parts = parts[2].split('-')
        eos_instance = _parse_instance(instance_parts[0])
        if _eos_instance is not None and eos_instance != _eos_instance:
            raise ValueError(f"This path is on the EOS instance {eos_instance}, "
                           + f"however, the MGM specified it as {_eos_instance}.")
        if len(instance_parts) > 1:
            if len(instance_parts) > 2:
                raise ValueError(f"EOS instance {parts[2]} has more than one dash.")
            else:
                parts = ['', 'eos', eos_instance, instance_parts[1], *parts[3:]]
        else:
            parts = ['', 'eos', eos_instance, *parts[3:]]
        self.eos_path = '/'.join(parts) + '/' + self.name
        self.eos_instance = eos_instance


    # Overwrite Path methods
    # ======================

    def exists(self, *args, **kwargs):
        if self.is_symlink():
            return self.resolve().exists(*args, **kwargs)
        return _eos_exists(self, *args, **kwargs)

    def stat(self, *args, **kwargs):
        # if self.is_symlink():
        #     return self.resolve().stat(*args, **kwargs)
        return _eos_stat(self, *args, **kwargs)

    def lstat(self, *args, **kwargs):
        return _eos_lstat(self, *args, **kwargs)

    def is_file(self, *args, **kwargs):
        if self.is_symlink():
            return self.resolve().is_file(*args, **kwargs)
        return _eos_is_file(self, *args, **kwargs)

    def is_dir(self, *args, **kwargs):
        if self.is_symlink():
            return self.resolve().is_dir(*args, **kwargs)
        return _eos_is_dir(self, *args, **kwargs)

    def is_symlink(self, *args, **kwargs):
        return _eos_is_symlink(self, *args, **kwargs)

    def touch(self, *args, **kwargs):
        return _eos_touch(self, *args, **kwargs)

    def unlink(self, *args, **kwargs):
        return _eos_unlink(self, *args, **kwargs)

    def mkdir(self, *args, **kwargs):
        return _eos_mkdir(self, *args, **kwargs)

    def rmdir(self, *args, **kwargs):
        return _eos_rmdir(self, *args, **kwargs)

    def glob(self, *args, **kwargs):
        raise NotImplementedError

    def rglob(self, *args, **kwargs):
        raise NotImplementedError


    # Overwrite FsPath methods
    # ======================

    def symlink_to(self, target, target_is_directory=False, **kwargs):
        target = FsPath(target)
        return _eos_symlink_to(self, FsPath, target, target_is_directory=target_is_directory, **kwargs)

    def rmtree(self, *args, **kwargs):
        return _eos_rmtree(self, FsPath, *args, **kwargs)

    def size(self, *args, **kwargs):
        return _eos_size(self, FsPath, *args, **kwargs)


class EosPosixPath(EosPath, PurePosixPath):
    """EosPath subclass for EOS paths on non-Windows systems.

    On a POSIX system, instantiating an FsPath or an EosPath
    should return this object.
    """
    __slots__ = ()

    if os.name == 'nt':
        def __new__(cls, *args, **kwargs):
            raise OSError(
                f"Cannot instantiate {cls.__name__!r} on your system")


class EosWindowsPath(EosPath, PureWindowsPath):
    """EosPath subclass for EOS paths on Windows systems.

    This is currently not supported.
    """
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "Windows currently not supported by EosPath.")

    if os.name != 'nt':
        def __new__(cls, *args, **kwargs):
            raise OSError(
                f"Cannot instantiate {cls.__name__!r} on your system")

