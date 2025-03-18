# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os, sys
from pathlib import Path, PurePosixPath, PureWindowsPath

from .fs import FsPath, _non_strict_resolve
from .eos_methods import _eos_path, _eos_exists, _eos_stat, _eos_lstat, _eos_is_file, \
                         _eos_is_dir, _eos_is_symlink, _eos_touch, _eos_symlink_to, \
                         _eos_unlink, _eos_mkdir, _eos_rmdir, _eos_rmtree, _eos_size

# Note: /eos itself is not on EOS (it is a mountpoint on the local disk)
def _on_eos(*args):
    if isinstance(args[0], str):
        if args[0].startswith('root://eos'):
            return True
        elif args[0].startswith('root:'):
            raise ValueError(f"Unknown EosPath specification {args}.")
    #     # We cannot recognise path file systems by string because of symlinks
    #     elif args[0].startswith('/eos/'):
    #         return True
    #     elif args[0] == '/' and len(args) > 1 \
    #     and (args[1].startswith('eos/') or \
    #         (args[1] == 'eos' and len(args) > 2)):
    #         return True
    absolute = _non_strict_resolve(Path(*args).expanduser().absolute().parent)
    if absolute == _eos_path:
        return True
    parents = list(absolute.parents)
    return len(parents) > 1 and parents[-2] == _eos_path

def _parse_instance(eos_instance):
    if eos_instance == 'home':
        return 'user'
    return eos_instance.lower()

def _parse_mgm(_eos_mgm):
    from xaux.fs.eos_methods import EOS_CELL
    if not isinstance(_eos_mgm, str):
        raise ValueError("The variable `_eos_mgm` should be a string.")
    if not _eos_mgm.startswith('root:'):
        raise ValueError("The variable `_eos_mgm` should start with 'root:'!")
    parts = _eos_mgm.split('/')
    if parts[1] != '' or not parts[2].startswith('eos'):
        raise ValueError(f"Invalid EosPath specification: {_eos_mgm}. "
                        + "The full path should start with 'root://eos...'.")
    if len(parts) >= 3 and parts[3] != '':
        raise ValueError(f"Invalid EosPath specification: {_eos_mgm}. "
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
    __slots__ = ('mgm', 'eos_instance', 'eos_path', 'eos_path_full', '_init_args')


    @classmethod
    def _new(cls, *args, _eos_checked=False):
        if cls is EosPath:
            cls = EosWindowsPath if os.name == 'nt' else EosPosixPath
        with cls._in_constructor():
            try:
                self = cls._from_parts(args)
            except AttributeError:
                self = Path.__new__(cls, *args)
        with cls._in_constructor(_force=True):
            if not _eos_checked and not _on_eos(*args):
                raise ValueError("The path is not on EOS.")
        return self

    def __new__(cls, *args, _eos_checked=False, _eos_mgm=None):
        if len(args) == 0:
            args = ('.',)
        if isinstance(args[0], str) \
        and args[0].startswith('root:'):
            if len(args) > 1:
                raise ValueError("When specifying the instance `root://eos...` "
                               + "in the path, the latter has to be given as "
                               + "one complete string.")
            mgm, eos_instance, eos_path = _parse_mgm(args[0])
            if eos_path is None:
                raise ValueError("Incomplete MGM path (only MGM instance was given).")
            self = cls._new(eos_path, _eos_checked=_eos_checked)
            self.eos_instance = eos_instance # Temporary (verified in _set_eos_path in init)
            if sys.version_info >= (3, 12):
                self._init_args = [eos_path]
            if _eos_mgm is not None and mgm != _parse_mgm(_eos_mgm)[0]:
                raise ValueError(f"The specified MGM {_eos_mgm} does not match "
                               + f"the resolved one {mgm}.")
            self.mgm = mgm
        else:
            self = cls._new(*args, _eos_checked=_eos_checked)
            if sys.version_info >= (3, 12):
                self._init_args = args
            if _eos_mgm is not None:
                mgm, eos_instance, _ = _parse_mgm(_eos_mgm)
                self.eos_instance = eos_instance # Temporary (verified in _set_eos_path in init)
                self.mgm = mgm
            else:
                self.eos_instance = None
                self.mgm = None
        return self

    def __init__(self, *args):
        with self.__class__._in_constructor():
            if sys.version_info >= (3, 12):
                Path.__init__(self, *self._init_args)
            else:
                Path.__init__(self)
        if self.eos_instance is None:
            self._set_eos_path()
        else:
            self._set_eos_path(_eos_instance=self.eos_instance)
        if self.mgm is None:
            from xaux.fs.eos_methods import EOS_CELL
            self.mgm = f'root://eos{self.eos_instance}.{EOS_CELL.lower()}'
        self.eos_path_full = f'{self.mgm}/{self.eos_path}'

    def _set_eos_path(self, _eos_instance=None):
        with self.__class__._in_constructor(_force=True):
            parts = _non_strict_resolve(self.expanduser().parent, _as_posix=True).split('/')
            if len(parts) == 2:
                parts = _non_strict_resolve(self.expanduser(), _as_posix=True).split('/')
        instance_parts = parts[2].split('-')
        eos_instance = _parse_instance(instance_parts[0])
        if _eos_instance is not None and eos_instance != _eos_instance:
            raise ValueError(f"This path is on the EOS instance {eos_instance}, "
                           + f"however, the MGM specified it as {_eos_instance}.")
        if len(instance_parts) > 1:
            if len(instance_parts) > 2:
                raise ValueError(f"EOS instance {parts[2]} has more than one dash.")
            else:
                if len(instance_parts[1]) > 1:
                    # This happens e.g. on SWAN where home is cast to home-i04 etc.
                    # We then just completely ignore the i04 part.
                    parts = ['', 'eos', eos_instance, *parts[3:]]
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
        return _eos_exists(self.expanduser(), *args, **kwargs)

    def stat(self, *args, **kwargs):
        # if self.is_symlink():
        #     return self.resolve().stat(*args, **kwargs)
        return _eos_stat(self.expanduser(), *args, **kwargs)

    def lstat(self, *args, **kwargs):
        return _eos_lstat(self.expanduser(), *args, **kwargs)

    def is_file(self, *args, **kwargs):
        if self.is_symlink():
            return self.resolve().is_file(*args, **kwargs)
        return _eos_is_file(self.expanduser(), *args, **kwargs)

    def is_dir(self, *args, **kwargs):
        if self.is_symlink():
            return self.resolve().is_dir(*args, **kwargs)
        return _eos_is_dir(self.expanduser(), *args, **kwargs)

    def is_symlink(self, *args, **kwargs):
        return _eos_is_symlink(self.expanduser(), *args, **kwargs)

    def touch(self, *args, **kwargs):
        return _eos_touch(self.expanduser(), *args, **kwargs)

    def unlink(self, *args, **kwargs):
        return _eos_unlink(self.expanduser(), *args, **kwargs)

    def mkdir(self, *args, **kwargs):
        return _eos_mkdir(self.expanduser(), *args, **kwargs)

    def rmdir(self, *args, **kwargs):
        return _eos_rmdir(self.expanduser(), *args, **kwargs)

    def as_posix(self, *args, **kwargs):
        if hasattr(self, 'eos_path'):
            return self.eos_path
        return Path.as_posix(self, *args, **kwargs)

    # def glob(self, *args, **kwargs):
    #     raise NotImplementedError

    # def rglob(self, *args, **kwargs):
    #     raise NotImplementedError


    # Overwrite FsPath methods
    # ======================

    def symlink_to(self, target, target_is_directory=False, **kwargs):
        target = FsPath(target)
        return _eos_symlink_to(self.expanduser(), FsPath, target.expanduser(), target_is_directory=target_is_directory, **kwargs)

    def rmtree(self, *args, **kwargs):
        return _eos_rmtree(self.expanduser(), FsPath, *args, **kwargs)

    def size(self, *args, **kwargs):
        return _eos_size(self.expanduser(), FsPath, *args, **kwargs)


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

