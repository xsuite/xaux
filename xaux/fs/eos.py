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
            raise ValueError("Unknown path specification {args}.")
        elif args[0] == '/' and len(args) > 1 \
        and (args[1] == 'eos' or args[1] == 'eos/'):
            return True
    parents = _non_strict_resolve(Path(*args).absolute().parent).parents
    return len(parents) > 1 and parents[-2] == _eos_path

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
            raise OSError(f"Cannot instantiate {cls.__name__} "
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


    # Overwrite Path methods
    # ======================

    # Resolving EOS paths can be tricky due to different mount points.
    # Luckily, the path is already resolved at instantiation.
    # TODO: should be with eos?
    def resolve(self, *args, **kwargs):
        # We first resolve all internal symlinks
        new_path = FsPath(_non_strict_resolve(Path(self.eos_path), as_posix=True), *args, **kwargs)
        # And then we get back the correct EOS path
        if isinstance(new_path, EosPath):
            return EosPath(new_path.eos_path)
        else:
            return new_path

    def exists(self, *args, **kwargs):
        _assert_eos_accessible("Cannot check for existence of EOS paths.")
        result = _run_eos(['eos', self.mgm, 'ls', self.eos_path], 
                           _false_if_stderr_contains='No such file or directory', **kwargs)
        if result[0]:
            return result[1]
        return Path(self.eos_path).exists(self, *args, **kwargs)

    def stat(self, *args, **kwargs):
        _assert_eos_accessible("Cannot stat EOS paths.")
        if _eos_installed and not kwargs.get('_skip_eos', False):
            if kwargs.get('follow_symlinks', True):
                # TODO: need a follow link method or so
                print(f"Warning: `follow_symlinks` is not yet implemented for EOS paths.")
        result = _run_eos(['eos', self.mgm, 'stat', self.eos_path],
                           _false_if_stderr_contains='failed to stat', **kwargs)
        if result[0]:
            if not result[1]:
                raise FileNotFoundError
            return result[1]
        return Path.stat(self, *args, **kwargs)

    def is_file(self, *args, **kwargs):
        # TODO: need to follow symlink?
        _assert_eos_accessible("Cannot test if EOS path is file.")
        result = _run_eos(['eos', self.mgm, 'stat', self.eos_path],
                           _false_if_stderr_contains='failed to stat', **kwargs)
        if result[0]:
            if not result[1]:
                return False
            return result[1].endswith(' regular file')
        return Path.is_file(self, *args, **kwargs)

    def is_dir(self, *args, **kwargs):
        # TODO: need to follow symlink?
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

