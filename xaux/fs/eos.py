# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
from subprocess import run, PIPE, CalledProcessError
from pathlib import Path, PurePosixPath, PureWindowsPath
import warnings

from .fs import FsPath, _non_strict_resolve

EOS_CELL = 'cern.ch'

_eos_path = Path('/eos')

_eos_arg_for_find = 'find'
_eos_installed = False
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

_eos_mounted = _eos_path.exists()
eos_accessible = _eos_mounted or _eos_installed

def _assert_eos_accessible(mess=None):
    if not eos_accessible:
        mess = f" {mess}" if mess is not None else mess
        raise OSError(f"EOS is not installed on your system.{mess}")

def _on_eos(*args):
    if isinstance(args[0], str):
        if args[0].startswith('/eos/'):
            return True
        elif args[0].startswith('root://eos'):
            return True
        elif args[0].startswith('root:'):
            raise ValueError(f"Unknown path specification {args}.")
        elif args[0] == '/' and len(args) > 1 \
        and (args[1] == 'eos' or args[1] == 'eos/'):
            return True
    parents = _non_strict_resolve(Path(*args).absolute().parent).parents
    return len(parents) > 1 and parents[-2] == _eos_path

def _parse_instance(eos_instance):
    if eos_instance == 'home':
        return 'user'
    return eos_instance.lower()

def _parse_mgm(_eos_mgm):
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
                       + f"Please set `xaux.fs.eos.EOS_CELL = {mgm_parts[1:]}` "
                       + f"after importing xaux.")
    mgm = f'root://eos{eos_instance}.{EOS_CELL.lower()}'
    eos_path = '/'.join(parts[3:]) if len(parts) >= 3 else None
    return mgm, eos_instance, eos_path

def _run_eos(eos_cmds, **kwargs):
    # Try to run the eos command. Returns a bool success and the stdout.
    _skip_eos  = kwargs.pop('_skip_eos', False)
    _force_eos = kwargs.pop('_force_eos', False)
    _false_if_stderr_contains = kwargs.pop('_false_if_stderr_contains', None)
    if _eos_installed and not _skip_eos:
        stderr = f"Failed {' '.join(eos_cmds)}.\n"
        try:
            cmd = run(eos_cmds, stdout=PIPE, stderr=PIPE)
        except Exception as e:
            stderr += repr(e)
            if _eos_mounted:
                # We can retry with local FS
                warnings.warn(stderr, RuntimeWarning)
                return False, ''
            else:
                raise RuntimeError(stderr)
        if cmd.returncode == 0:
            stdout = cmd.stdout.decode('UTF-8').strip()
            return True, stdout
        else:
            stderr += cmd.stderr.decode('UTF-8').strip()
            if _false_if_stderr_contains is not None:
                if _false_if_stderr_contains in stderr:
                    return True, False
            if _eos_mounted:
                # We can retry with local FS
                warnings.warn(stderr, RuntimeWarning)
                return False, ''
            else:
                raise RuntimeError(stderr)
    elif _force_eos:
        raise OSError("EOS is not installed on your system.")


class EosPath(FsPath, Path):
    """Path subclass for EOS paths.

    Instantiating an FsPath should call this class.
    """
    __slots__ = ('mgm', 'eos_instance', 'eos_path', 'eos_path_full')


    @classmethod
    def _new(cls, *args, _eos_checked=False):
        self = cls._from_parts(args)
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
            self = cls._new(eos_path)
            self._set_eos_path(_eos_instance=eos_instance)
            if _eos_mgm is not None and mgm != _parse_mgm(_eos_mgm)[0]:
                raise ValueError(f"The specified MGM {_eos_mgm} does not match "
                               + f"the resolved one {mgm}.")
            self.mgm = mgm
        else:
            self = cls._new(*args)
            if _eos_mgm is not None:
                mgm, eos_instance, _ = _parse_mgm(_eos_mgm)
                self._set_eos_path(_eos_instance=eos_instance)
                self.mgm = mgm
            else:
                self._set_eos_path()
                self.mgm = f'root://eos{self.eos_instance}.{EOS_CELL.lower()}'        
        self.eos_path_full = f'{self.mgm}/{self.eos_path}'

        if not self._flavour.is_supported:
            raise OSError(f"Cannot instantiate {cls.__name__} "
                         + "on your system.")

        return self


    def _set_eos_path(self, _eos_instance=None):
        parts = _non_strict_resolve(self.parent, _as_posix=True).split('/')
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
            return self.resolve().exists()
        _assert_eos_accessible("Cannot check for existence of EOS paths.")
        d = ['-d'] if self.is_dir() else []
        result = _run_eos(['eos', self.mgm, 'ls', *d, self.eos_path], 
                           _false_if_stderr_contains='No such file or directory', **kwargs)
        if result[0]:
            if not result[1]:
                return False
            return result[1] == self.name or result[1].endswith('/' + self.name)
        return Path(self.eos_path).exists(*args, **kwargs)

    def stat(self, *args, **kwargs):
        _assert_eos_accessible("Cannot stat EOS paths.")
        result = _run_eos(['eos', self.mgm, 'stat', self.eos_path],
                           _false_if_stderr_contains='failed to stat', **kwargs)
        if result[0]:
            if not result[1]:
                raise FileNotFoundError
            return result[1]
        return Path.stat(self, *args, **kwargs)

    def is_file(self, *args, **kwargs):
        if self.is_symlink():
            return self.resolve().is_file()
        _assert_eos_accessible("Cannot test if EOS path is file.")
        result = _run_eos(['eos', self.mgm, 'stat', self.eos_path],
                           _false_if_stderr_contains='failed to stat', **kwargs)
        if result[0]:
            if not result[1]:
                return False
            return result[1].endswith(' regular file')
        return Path.is_file(self, *args, **kwargs)

    def is_dir(self, *args, **kwargs):
        if self.is_symlink():
            return self.resolve().is_dir()
        _assert_eos_accessible("Cannot test if EOS path is dir.")
        result = _run_eos(['eos', self.mgm, 'stat', self.eos_path],
                           _false_if_stderr_contains='failed to stat', **kwargs)
        if result[0]:
            if not result[1]:
                return False
            return result[1].endswith(' directory')
        return Path.is_dir(self, *args, **kwargs)

    def is_symlink(self, *args, **kwargs):
        _assert_eos_accessible("Cannot test if EOS path is symlink.")
        result = _run_eos(['eos', self.mgm, 'stat', self.eos_path],
                           _false_if_stderr_contains='failed to stat', **kwargs)
        if result[0]:
            if not result[1]:
                return False
            return result[1].endswith(' symbolic link')
        return Path.is_symlink(self, *args, **kwargs)

    def touch(self, *args, **kwargs):
        _assert_eos_accessible("Cannot touch EOS paths.")
        result = _run_eos(['eos', self.mgm, 'touch', self.eos_path], **kwargs)
        if result[0]:
            return result[1]
        return Path.touch(self, *args, **kwargs)

    def symlink_to(self, target, target_is_directory=False, **kwargs):
        _assert_eos_accessible("Cannot create symlinks on EOS paths.")
        target = FsPath(target)
        result = _run_eos(['eos', self.mgm, 'ln', '-fns', self.eos_path,
                           target.as_posix()], **kwargs)
        if result[0]:
            return result[1]
        return Path.symlink_to(self, target, target_is_directory)

    def unlink(self, *args, **kwargs):
        _assert_eos_accessible("Cannot unlink EOS paths.")
        if self.is_dir():
            raise IsADirectoryError(f"{self} is a directory.")
        result = _run_eos(['eos', self.mgm, 'rm', self.eos_path], **kwargs)
        if result[0]:
            return result[1]
        return Path.unlink(self, *args, **kwargs)

    def rmdir(self, *args, **kwargs):
        _assert_eos_accessible("Cannot rmdir EOS paths.")
        if not self.is_dir():
            raise NotADirectoryError(f"{self} is not a directory.")
        result = _run_eos(['eos', self.mgm, 'rmdir', self.eos_path], **kwargs)
        if result[0]:
            return result[1]
        return Path.rmdir(self, *args, **kwargs)


    # Overwrite FsPath methods
    # ======================

    def rmtree(self, *args, **kwargs):
        _assert_eos_accessible("Cannot rmtree EOS paths.")
        if not self.is_dir():
            raise NotADirectoryError(f"{self} is not a directory.")
        result = _run_eos(['eos', self.mgm, 'rm', '-r', self.eos_path], **kwargs)
        if result[0]:
            return result[1]
        return FsPath.rmtree(self, *args, **kwargs)

    def size(self, *args, **kwargs):
        _assert_eos_accessible("Cannot get size of EOS paths.")
        if not self.is_file():
            return 0
        result = _run_eos(['eos', self.mgm, 'stat', self.eos_path], **kwargs)
        if result[0]:
            return int(result[1].split()[3])
        return FsPath.size(self, *args, **kwargs)


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

