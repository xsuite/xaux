# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath

from .fs import FsPath, _non_strict_resolve

EOS_CELL = 'cern.ch'

_eos_path = Path('/eos')
try:
    cmd = subprocess.run(['eos', '--version'], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, check=True)
    # Temporary hack as the eos command wrongly returns 255
    _eos_installed =  cmd.returncode == 0 or cmd.returncode == 255
except (subprocess.CalledProcessError, FileNotFoundError):
    _eos_installed = False

try:
    cmd = subprocess.run(["xrdcp", "--version"], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, check=True)
    _xrdcp_installed = cmd.returncode == 0
except (subprocess.CalledProcessError, FileNotFoundError):
    _xrdcp_installed = False

eos_accessible = _eos_path.exists() or _eos_installed or _xrdcp_installed

def _assert_eos_accessible(mess=None):
    if not eos_accessible:
        mess = f" {mess}" if mess is not None else mess
        raise EnvironmentError(f"EOS is not installed on your system.{mess}")

def _on_eos(*args):
    if isinstance(args[0], str):
        if args[0].startswith('/eos/'):
            return True
        elif args[0].startswith('root://eos'):
            return True
        elif args[0].startswith('root:'):
            raise ValueError("Unknown path specification {args}.")
        elif args[0] == '/' and len(args) > 1 \
        and (args[1] == 'eos' or args[1] == 'eos/'):
            return True
    parents = _non_strict_resolve(Path(*args)).parents
    return len(parents) > 1 and parents[-2] == _eos_path

 
class EosPath(FsPath, Path):
    """Path subclass for EOS paths.

    Instantiating an FsPath should call this class.
    """
    __slots__ = ('mgm', 'eos_instance', 'eos_path', 'eos_path_full')

    def __new__(cls, *args, _eos_checked=False):
        if cls is EosPath:
            cls = EosWindowsPath if os.name == 'nt' else EosPosixPath
        if isinstance(args[0], str) \
        and args[0].startswith('root:'):
            if len(args) > 1:
                raise ValueError("When specifying the instance `root://eos...` "
                               + "in the path, the latter has to be given as "
                               + "one complete string.")
            parts = args[0].split('/')
            if parts[1] != '' or not parts[2].startswith('eos') or parts[3] != '':
                raise ValueError(f"Invalid EOS path specification: {args[0]}. "
                                + "The full path should start with 'root://eos...'"
                                + " and have a double slash // in between the MGM and "
                                + "the path itself. \nExample: 'root://eosuser.cern.ch/"
                                + "/eos/user/s/...'.")
            mgm = '/'.join(parts[:3])
            eos_instance = mgm.split('/')[2].split('.')[0].replace('eos', '')
            self = cls._from_parts(['/'.join(parts[3:])])
            self.mgm = mgm
            self.eos_instance = eos_instance
            assert self.mgm == f'root://eos{self.eos_instance}.{EOS_CELL}'
        else:
            self = cls._from_parts(args)
            self.eos_instance = _non_strict_resolve(self, _as_posix=True
                                                    ).split('/')[2].split('-')[0]
        if not self._flavour.is_supported:
            raise RuntimeError(f"cannot instantiate {cls.__name__} "
                              + "on your system.")
        if not _eos_checked and not _on_eos(self):
            raise ValueError("The path is not on EOS.")
        if self.eos_instance == 'home':
            self.eos_instance = 'user'
        self.mgm = f'root://eos{self.eos_instance}.{EOS_CELL}'
        parts = _non_strict_resolve(self, _as_posix=True).split('/')
        instance_parts = parts[2].split('-')
        if len(instance_parts) > 1:
            if len(instance_parts) > 2:
                raise ValueError(f"EOS instance {parts[2]} has more than one dash.")
            else:
                parts = ['', 'eos', self.eos_instance, instance_parts[1], *parts[3:]]
        else:
            parts = ['', 'eos', self.eos_instance, *parts[3:]]
        self.eos_path = '/'.join(parts)
        self.eos_path_full = f'{self.mgm}/{self.eos_path}'
        return self

    def resolve(self, *args, **kwargs):
        return EosPath(Path(self.eos_path).resolve(), *args, **kwargs)

    def exists(self, *args, **kwargs):
        _assert_eos_accessible("Cannot check for existence of EOS paths.")
        return Path(self.eos_path).exists(*args, **kwargs)

    def touch(self, *args, **kwargs):
        _assert_eos_accessible("Cannot touch EOS paths.")
        return Path.touch(self, *args, **kwargs)

    def symlink_to(self, *args, **kwargs):
        _assert_eos_accessible("Cannot create symlinks on EOS paths.")
        return Path.symlink_to(self, *args, **kwargs)


class EosPosixPath(EosPath, PurePosixPath):
    """EosPath subclass for EOS paths on non-Windows systems.

    On a POSIX system, instantiating an FsPath or an EosPath
    should return this object.
    """
    __slots__ = ()

    if os.name == 'nt':
        def __new__(cls, *args, **kwargs):
            raise RuntimeError(
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
            raise RuntimeError(
                f"Cannot instantiate {cls.__name__!r} on your system")

