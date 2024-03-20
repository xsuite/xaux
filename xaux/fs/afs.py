# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath

from .fs import FsPath, _non_strict_resolve


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

afs_accessible = _afs_path.exists()

def _assert_afs_accessible(mess=None):
    if not afs_accessible:
        mess = f" {mess}" if mess is not None else mess
        raise OSError(f"AFS is not installed on your system.{mess}")

def _on_afs(*args):
    if isinstance(args[0], str):
        if args[0].startswith('/afs/'):
            return True
        elif args[0] == '/' and len(args) > 1 \
        and (args[1] == 'afs' or args[1] == 'afs/'):
            return True
    parents = _non_strict_resolve(Path(*args).absolute().parent).parents
    return len(parents) > 1 and parents[-2] == _afs_path


class AfsPath(FsPath, Path):
    """Path subclass for AFS paths.

    Instantiating an FsPath should call this class.
    """
    __slots__ = ('afs_cell')

    def __new__(cls, *args, _afs_checked=False):
        if cls is AfsPath:
            cls = AfsWindowsPath if os.name == 'nt' else AfsPosixPath
        self = cls._from_parts(args)
        self.afs_cell = _non_strict_resolve(self, _as_posix=True).split('/')[2].upper()
        if not self._flavour.is_supported:
            raise OSError(f"cannot instantiate {cls.__name__} "
                         + "on your system.")
        if not _afs_checked and not _on_afs(self):
            raise ValueError("The path is not on AFS.")
        return self

    # Overwrite Path methods
    # ======================

    def exists(self, *args, **kwargs):
        _assert_afs_accessible("Cannot check for existence of AFS paths.")
        return Path.exists(self, *args, **kwargs)

    def touch(self, *args, **kwargs):
        _assert_afs_accessible("Cannot touch AFS paths.")
        return Path.touch(self, *args, **kwargs)

    def symlink_to(self, *args, **kwargs):
        _assert_afs_accessible("Cannot create symlinks on AFS paths.")
        return Path.symlink_to(self, *args, **kwargs)

    # New methods
    # ======================

    @property
    def acl(self):
        _assert_fs_installed("Cannot get ACL of AFS paths.")
        cmd = subprocess.run(['fs', 'la', self.as_posix()],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cmd.returncode == 0:
            acl = {}
            output = cmd.stdout.decode('UTF-8').strip()
            lines = output.split('\n')
            if FsPath(lines[0].split()[-2]).resolve() != self.resolve():
                raise RuntimeError(f"Cannot interpret ACL output.\n{output}")
            for line in lines[1:]:
                if line.startswith('  '):
                    parts = line.split()
                    acl[parts[0]] = parts[1]
                    if len(parts) > 2:
                        raise RuntimeError(f"Cannot interpret ACL output.\n{output}")
                elif line != 'Normal rights:':
                    raise RuntimeError(f"Cannot interpret ACL output.\n{output}")
            if acl == {}:
                raise RuntimeError(f"Cannot interpret ACL output.\n{output}")
            return acl
        else:
            stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
            raise RuntimeError(f"Failed to retrieve ACL on {self}.\n{stderr}")

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
            cmd = subprocess.run(['fs', 'sa', self.as_posix(), user, acl],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if cmd.returncode != 0:
                stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
                raise RuntimeError(f"Failed to set ACL to {acl} on {self} for user "
                                 + f"{user}.\n{stderr}")

    @acl.deleter
    def acl(self):
        _assert_fs_installed("Cannot delete ACL of AFS paths.")
        cmd = subprocess.run(['fs', 'sa', self.as_posix(), 'none'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cmd.returncode != 0:
            stderr = cmd.stderr.decode('UTF-8').strip().split('\n')
            raise RuntimeError(f"Failed to delete ACL on {self}.\n{stderr}")


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


