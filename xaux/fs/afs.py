# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os, sys
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath

from .fs import FsPath, _non_strict_resolve
from .fs_methods import _xrdcp_installed


_afs_path = Path('/afs')

try:
    cmd = subprocess.run(['fs', '--version'], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    _fs_installed =  cmd.returncode == 0
except (subprocess.CalledProcessError, FileNotFoundError):
    _fs_installed = False

def _assert_fs_installed(mess=None):
    if not _fs_installed:
        mess = f" {mess}" if mess is not None else mess
        raise OSError(f"`fs` is not installed on your system.{mess}")

_afs_mounted = _afs_path.exists()
afs_accessible = _afs_mounted or _xrdcp_installed

def _assert_afs_accessible(mess=None):
    if not afs_accessible:
        mess = f" {mess}" if mess is not None else mess
        raise OSError(f"AFS is not installed on your system.{mess}")

def _on_afs(*args):
    if isinstance(args[0], str):
        if args[0] == '/afs' or args[0].startswith('/afs/'):
            return True
        elif args[0] == '/' and len(args) > 1 \
        and (args[1] == 'afs' or args[1] == 'afs/'):
            return True
    absolute = _non_strict_resolve(Path(*args).expanduser().absolute().parent)
    if absolute == _afs_path:
        return True
    parents = list(absolute.parents)
    return len(parents) > 1 and parents[-2] == _afs_path


class AfsPath(FsPath, Path):
    """Path subclass for AFS paths.

    Instantiating an FsPath should call this class.
    """
    __slots__ = ('afs_cell')

    def __new__(cls, *args, _afs_checked=False):
        if sys.version_info >= (3, 12):
            raise RuntimeError("This class is not yet compatible with Python 3.12 or higher.")
        if cls is AfsPath:
            cls = AfsWindowsPath if os.name == 'nt' else AfsPosixPath
        with cls._in_constructor():
            try:
                self = cls._from_parts(args)
            except AttributeError:
                self = object.__new__(cls)
            if not _afs_checked and not _on_afs(self):
                raise ValueError("The path is not on AFS.")
        return self

    def __init__(self, *args):
        with self.__class__._in_constructor():
            super().__init__()
        with self.__class__._in_constructor(_force=True):
            parent = self.parent
        if parent == _afs_path:
            self.afs_cell = self.name
        else:
            self.afs_cell = _non_strict_resolve(parent, _as_posix=True).split('/')[2].upper()

    # Overwrite Path methods
    # ======================

    def exists(self, *args, **kwargs):
        _assert_afs_accessible("Cannot check for existence of AFS paths.")
        return Path.exists(self.expanduser(), *args, **kwargs)

    def touch(self, *args, **kwargs):
        _assert_afs_accessible("Cannot touch AFS paths.")
        return Path.touch(self, *args, **kwargs)

    def symlink_to(self, *args, **kwargs):
        _assert_afs_accessible("Cannot create symlinks on AFS paths.")
        return Path.symlink_to(self.expanduser(), *args, **kwargs)

    # New methods
    # ======================

    @property
    def acl(self):
        _assert_fs_installed("Cannot get ACL of AFS paths.")
        cmd = subprocess.run(['fs', 'la', self.expanduser().as_posix()],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cmd.returncode == 0:
            acl = {}
            output = cmd.stdout.decode('UTF-8').strip()
            lines = output.split('\n')
            if FsPath(lines[0].split()[-2]).resolve() != self.resolve():
                raise OSError(f"Cannot interpret ACL output.\n{output}")
            for line in lines[1:]:
                if line.startswith('  '):
                    parts = line.split()
                    acl[parts[0]] = parts[1]
                    if len(parts) > 2:
                        raise OSError(f"Cannot interpret ACL output.\n{output}")
                elif line != 'Normal rights:':
                    raise OSError(f"Cannot interpret ACL output.\n{output}")
            if acl == {}:
                raise OSError(f"Cannot interpret ACL output.\n{output}")
            return acl
        else:
            stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
            raise OSError(f"Failed to retrieve ACL on {self}.\n{stderr}")

    @acl.setter
    def acl(self, val):
        _assert_fs_installed("Cannot set ACL of AFS paths.")
        if not isinstance(val, dict):
            raise ValueError("ACL has to be a dictionary of users and permissions.")
        for user, acl in val.items():
            if acl is None or acl == '':
                acl = 'none'
            if not isinstance(user, str):
                raise ValueError("User in ACL has to be a string.")
            if not isinstance(acl, str):
                raise ValueError("ACL has to be a string or `None`.")
            cmd = subprocess.run(['fs', 'sa', self.expanduser().as_posix(), user, acl],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if cmd.returncode != 0:
                stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
                raise OSError(f"Failed to set ACL to {acl} on {self} for user "
                                 + f"{user}.\n{stderr}")

    @acl.deleter
    def acl(self):
        _assert_fs_installed("Cannot delete ACL of AFS paths.")
        cmd = subprocess.run(['fs', 'sa', self.expanduser().as_posix(), 'none'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cmd.returncode != 0:
            stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
            raise OSError(f"Failed to delete ACL on {self}.\n{stderr}")


class AfsPosixPath(AfsPath, PurePosixPath):
    """AfsPath subclass for AFS paths on non-Windows systems.

    On a POSIX system, instantiating an FsPath or an AfsPath
    should return this object.
    """
    __slots__ = ()

    if os.name == 'nt':
        def __new__(cls, *args, **kwargs):
            raise OSError(
                f"Cannot instantiate {cls.__name__!r} on your system")


class AfsWindowsPath(AfsPath, PureWindowsPath):
    """AfsPath subclass for AFS paths on Windows systems.

    On a Windows system, instantiating an FsPath or an AfsPath
    should return this object.
    """
    __slots__ = ()

    if os.name != 'nt':
        def __new__(cls, *args, **kwargs):
            raise OSError(
                f"Cannot instantiate {cls.__name__!r} on your system")


