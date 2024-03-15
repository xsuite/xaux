# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
from subprocess import run, PIPE, CalledProcessError
from pathlib import Path, PurePosixPath, PureWindowsPath

from .fs import FsPath, _non_strict_resolve

EOS_CELL = 'cern.ch'

_eos_path = Path('/eos')

_eos_arg_for_find = 'find'
_eos_installed = False
_xrdcp_installed = False
if os.name != 'nt':
    try:
        cmd = run(['eos', '--version'], stdout=PIPE, stderr=PIPE)
        # Temporary hack as the eos command wrongly returns 255
        _eos_installed =  cmd.returncode == 0 or cmd.returncode == 255

        if _eos_installed:
            # The command `eos find` has the wrong behaviour on new machines (running eos 5.2).
            # For this reason, the command `eos oldfind` has been introduced.
            # However, this command does not exist on the old machines, so in that case we
            # default back to `eos find`. This function gives the correct argument for eos find.
            cmd = run(['eos', 'oldfind'], stdout=PIPE,
                                stderr=PIPE)
            if cmd.returncode != 255:
                # Command found; we are running on a machine running new eos >= 5.2
                _eos_arg_for_find = 'oldfind'
    except (CalledProcessError, FileNotFoundError):
        _eos_installed = False

    try:
        cmd = run(["xrdcp", "--version"], stdout=PIPE,
                            stderr=PIPE, check=True)
        _xrdcp_installed = cmd.returncode == 0
    except (CalledProcessError, FileNotFoundError):
        _xrdcp_installed = False

eos_accessible = _eos_path.exists() or _eos_installed

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
    parents = [_non_strict_resolve(p) for p in Path(*args).absolute().parents]
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

    # Resolving EOS paths can be tricky due to different mount points.
    # Luckily, the path is already resolved at instantiation.
    # TODO: should be with eos
    def resolve(self, *args, follow_symlink=True, **kwargs):
        # TODO: this does not resolve internal links; what if the file itself is a link...
        return EosPath(self.eos_path, *args, **kwargs)

    # TODO: should be with eos
    def stat(self, *args, **kwargs):
        # print("stat in EosPath")
        # _assert_eos_accessible("Cannot stat EOS paths.")
        # if _eos_installed:
        #     cmd = run(['eos', self.mgm, 'stat', self.eos_path],
        #                 stdout=PIPE, stderr=PIPE, check=True)
        #     if cmd.returncode != 0:
        #         stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
        #         raise RuntimeError(f"Failed to stat {self}.\n{stderr}")
        # else:
        return Path.stat(self, *args, **kwargs)

    # TODO: should be with eos
    def exists(self, *args, **kwargs):
        _assert_eos_accessible("Cannot check for existence of EOS paths.")
        return Path(self.eos_path).exists(*args, **kwargs)

    def touch(self, *args, **kwargs):
        _assert_eos_accessible("Cannot touch EOS paths.")
        if _eos_installed:
            cmd = run(['eos', self.mgm, 'touch', self.eos_path],
                        stdout=PIPE, stderr=PIPE, check=True)
            if cmd.returncode != 0:
                stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
                raise RuntimeError(f"Failed to touch {self}.\n{stderr}")
        else:
            return Path.touch(self, *args, **kwargs)

    # TODO: should be with eos
    def symlink_to(self, *args, **kwargs):
        _assert_eos_accessible("Cannot create symlinks on EOS paths.")
        return Path.symlink_to(self, *args, **kwargs)

    def unlink(self, *args, **kwargs):
        _assert_eos_accessible("Cannot unlink EOS paths.")
        if _eos_installed:
            cmd = run(['eos', self.mgm, 'rm', self.eos_path],
                        stdout=PIPE, stderr=PIPE, check=True)
            if cmd.returncode != 0:
                stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
                raise RuntimeError(f"Failed to unlink {self}.\n{stderr}")
        else:
            return Path.unlink(self, *args, **kwargs)

    def rmdir(self, *args, **kwargs):
        _assert_eos_accessible("Cannot rmdir EOS paths.")
        if not self.is_dir():
            raise NotADirectoryError(f"{self} is not a directory.")
        if _eos_installed:
            cmd = run(['eos', self.mgm, 'rmdir', self.eos_path],
                        stdout=PIPE, stderr=PIPE, check=True)
            if cmd.returncode != 0:
                stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
                raise RuntimeError(f"Failed to rmdir {self}.\n{stderr}")
        else:
            return Path.rmdir(self, *args, **kwargs)

    def rmtree(self, *args, **kwargs):
        _assert_eos_accessible("Cannot rmtree EOS paths.")
        if not self.is_dir():
            raise NotADirectoryError(f"{self} is not a directory.")
        if _eos_installed:
            cmd = run(['eos', self.mgm, 'rm', '-r', self.eos_path],
                        stdout=PIPE, stderr=PIPE, check=True)
            if cmd.returncode != 0:
                stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
                raise RuntimeError(f"Failed to rmtree {self}.\n{stderr}")
        else:
            return FsPath.rmtree(self, *args, **kwargs)


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

