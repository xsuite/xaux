# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
import stat
from subprocess import run, PIPE, CalledProcessError
from pathlib import Path
import warnings

from .fs_methods import make_stat_result, size_expand, _xrdcp_installed

EOS_CELL = 'cern.ch'
default_eos_instance = 'public'

_eos_path = Path('/eos')

_eos_version = -1
_eos_version_int = -1
_eos_arg_for_find = 'find'
_eoscmd_installed = False
if os.name != 'nt':
    try:
        cmd = run(['eos', '--version'], stdout=PIPE, stderr=PIPE)
        # Temporary hack as the eos command wrongly returns 255
        _eoscmd_installed =  cmd.returncode == 0 or cmd.returncode == 255

        if _eoscmd_installed:
            _eos_version = cmd.stdout.decode('UTF-8').strip().split()
            if _eos_version == []:
                _eos_version = cmd.stderr.decode('UTF-8').strip().split()
            _eos_version = _eos_version[1]
            _eos_version_int = _eos_version.split('.')
            _eos_version_int = int(1.e6*int(_eos_version_int[0]) + 1.e3*int(_eos_version_int[1]) \
                                + int(_eos_version_int[2]))
            # The command `eos find` has the wrong behaviour on new machines (running eos 5.2).
            # For this reason, the command `eos oldfind` has been introduced.
            # However, this command does not exist on the old machines, so in that case we
            # default back to `eos find`. This function gives the correct argument for eos find.
            eos_env = {**os.environ, 'EOS_MGM_URL':  f'root://eos{default_eos_instance}.{EOS_CELL}'}
            cmd = run(['eos', 'oldfind'], stdout=PIPE, stderr=PIPE, env=eos_env)
            if cmd.returncode != 255:
                # Command found; we are running on a machine running new eos >= 5.2
                _eos_arg_for_find = 'oldfind'
    except (CalledProcessError, FileNotFoundError):
        _eoscmd_installed = False

_eos_mounted = _eos_path.exists()
eos_accessible = _eos_mounted or _eoscmd_installed or _xrdcp_installed

def _assert_eos_accessible(mess=None):
    if not eos_accessible:
        mess = f" {mess}" if mess is not None else mess
        raise OSError(f"EOS is not installed on your system.{mess}")


def _run_eos(eos_cmds, mgm, _force=False, **kwargs):
    from xaux.fs import _skip_eos_software, _force_eoscmd, _force_xrdcp
    # Try to run the eos command. Returns a bool success and the stdout.
    if _eoscmd_installed and not _skip_eos_software:
        _false_if_stderr_contains = kwargs.pop('_false_if_stderr_contains', None)
        stderr = f"Failed {' '.join(eos_cmds)}.\n"
        eos_env = {**os.environ, 'EOS_MGM_URL': mgm}
        try:
            cmd = run(eos_cmds, stdout=PIPE, stderr=PIPE, env=eos_env)
        except Exception as e:
            stderr += repr(e)
            if _eos_mounted and not _force_eoscmd:
                # We can retry with local FS
                warnings.warn(stderr, RuntimeWarning)
                return False, ''
            else:
                raise OSError(stderr)
        if cmd.returncode == 0:
            stdout = cmd.stdout.decode('UTF-8').strip()
            return True, stdout
        else:
            stderr += cmd.stderr.decode('UTF-8').strip()
            if _false_if_stderr_contains is not None:
                if _false_if_stderr_contains in stderr:
                    return True, False
            if _eos_mounted and not _force_eoscmd:
                # We can retry with local FS
                warnings.warn(stderr, RuntimeWarning)
                return False, ''
            else:
                raise OSError(stderr)
    elif _force:
        raise OSError("The command `eos` is not installed on your system.")
    else:
        return False, None


def is_egroup_member(egroup, verbose=False):
    success, result = _run_eos(['eos', 'member', egroup], _force=True,
                               mgm=f'root://eos{default_eos_instance}.{EOS_CELL}')
    out = result.split()
    is_member = [f.split('=')[1] for f in out if f.startswith('member=')][0] == 'true'
    if verbose:
        mem = 'a' if is_member else 'not a'
        usr = [f.split('=')[1] for f in out if f.startswith('user=')][0]
        egr = [f.split('=')[1] for f in out if f.startswith('egroup=')][0]
        lft = [f.split('=')[1] for f in out if f.startswith('lifetime=')][0]
        print(f"User {usr} is {mem} member of e-group {egr} (lifetime {lft}).")
    return is_member


# Overwrite Path methods
# ======================

def _eos_exists(path, *args, **kwargs):
    _assert_eos_accessible("Cannot stat EOS paths.")
    try:
        ftype, _ = _get_type(path, *args, **kwargs)
    except FileNotFoundError:
        return False
    if ftype is not None:
        return True
    return Path(path.eos_path).exists(*args, **kwargs)


def _get_type(path, *args, **kwargs):
    success, result = _run_eos(['eos', 'stat', path.eos_path], mgm=path.mgm,
                        _false_if_stderr_contains='failed to stat', **kwargs)
    if success:
        if not result:
            raise FileNotFoundError
        if result.endswith(' regular file'):
            parts = result.split()
            size = int(parts[parts.index('Size:')+1])
            return stat.S_IFREG, size
        elif result.endswith(' directory'):
            return stat.S_IFDIR, None
        elif result.endswith(' symbolic link'):
            return stat.S_IFLNK, None
        else:
            raise NotImplementedError(f"File type not known. Output:\n{result}")
    return None, None

def _eos_is_file(path, *args, **kwargs):
    _assert_eos_accessible("Cannot stat EOS paths.")
    try:
        ftype, _ = _get_type(path, *args, **kwargs)
    except FileNotFoundError:
        return False
    if ftype is not None:
        return ftype == stat.S_IFREG
    return Path.is_file(path, *args, **kwargs)

def _eos_is_dir(path, *args, **kwargs):
    _assert_eos_accessible("Cannot stat EOS paths.")
    try:
        ftype, _ = _get_type(path, *args, **kwargs)
    except FileNotFoundError:
        return False
    if ftype is not None:
        return ftype == stat.S_IFDIR
    return Path.is_dir(path, *args, **kwargs)

def _eos_is_symlink(path, *args, **kwargs):
    _assert_eos_accessible("Cannot stat EOS paths.")
    try:
        ftype, _ = _get_type(path, *args, **kwargs)
    except FileNotFoundError:
        return False
    if ftype is not None:
        return ftype == stat.S_IFLNK
    return Path.is_symlink(path, *args, **kwargs)


def _parse_fileinfo(fileinfo, ftype=None, st_size=None):
    data = fileinfo.split()
    stat_dict = {}
    # Get the file type and permissions
    if 'Flags:' in data:
        st_mode = int(data[data.index('Flags:')+1], base=8)
    else:
        st_mode = 0
    if ftype is None:
        ftype = st_mode & 0o770000  # mask to get file type bits
        if ftype == 0:              # parse manually from text
            if data[0] == 'Directory:':
                ftype = stat.S_IFDIR
            elif data[0] == 'File:':
                ftype = stat.S_IFREG
            else:
                raise NotImplementedError(f"Unknown file type {data[0]}.")
    else:
        if st_mode & 0o770000 == 0: # check that it doesn't exist yet in the flags
            st_mode += ftype
        elif ftype != st_mode & 0o770000:
            raise ValueError(f"Provided file type {ftype} and the bit in the flags "
                          + f"{st_mode & 0o770000} do not match!")
    stat_dict['st_mode'] = st_mode
    # Get the size if file or if provided
    if st_size is not None:
        stat_dict['st_size'] = st_size
    elif ftype == stat.S_IFREG and 'Size:' in data:
        stat_dict['st_size'] = size_expand(data[data.index('Size:')+1])
    # Get the other metadata
    if 'Modify:' in data:
        stat_dict['st_mtime'] = float(data[data.index('Timestamp:', data.index('Modify:'))+1])
        stat_dict['st_mtime_ns'] = int(1.e9*stat_dict['st_mtime'])
    if 'Change:' in data:
        stat_dict['st_ctime'] = float(data[data.index('Timestamp:', data.index('Change:'))+1])
        stat_dict['st_ctime_ns'] = int(1.e9*stat_dict['st_ctime'])
    if 'Access:' in data:
        stat_dict['st_atime'] = float(data[data.index('Timestamp:', data.index('Access:'))+1])
        stat_dict['st_atime_ns'] = int(1.e9*stat_dict['st_atime'])
    if 'Birth:' in data:
        stat_dict['st_birthtime'] = float(data[data.index('Timestamp:', data.index('Birth:'))+1])
        stat_dict['st_birthtime_ns'] = int(1.e9*stat_dict['st_birthtime'])
    if 'CUid:' in data:
        stat_dict['st_uid'] = int(data[data.index('CUid:')+1])
    if 'CGid:' in data:
        stat_dict['st_gid'] = int(data[data.index('CGid:')+1])
    if 'Blocksize:' in data:
        stat_dict['st_blksize'] = size_expand(data[data.index('Blocksize:')+1], binary=True)
    # TODO: Not set: st_ino, st_dev, st_nlink, st_flags, st_blocks, st_gen, st_rdev,
    #       st_fstype, st_rsize, st_creator, st_type, st_file_attributes, st_reparse_tag
    return make_stat_result(stat_dict)

def _eos_lstat(path, *args, **kwargs):
    _assert_eos_accessible("Cannot stat EOS paths.")
    ftype, st_size = _get_type(path, *args, **kwargs)
    if ftype is None:
        return Path.lstat(path, *args, **kwargs)
    elif ftype == stat.S_IFLNK:
        # Special treatment: do NOT follow link
        # Temporary solution: no way to retrieve other info currently
        return make_stat_result({'st_mode': ftype+0o0777, 'st_size': st_size})
    else:
        success, result = _run_eos(['eos', 'fileinfo', path.eos_path], mgm=path.mgm,
                           _false_if_stderr_contains='No such file or directory', **kwargs)
        if not success:
            return Path.lstat(path, *args, **kwargs)
        else:
            if not result:
                raise FileNotFoundError
            return _parse_fileinfo(result, ftype, st_size)

def _eos_stat(path, *args, **kwargs):
    _assert_eos_accessible("Cannot stat EOS paths.")
    ftype, st_size = _get_type(path, *args, **kwargs)
    # The command `eos fileinfo` automatically resolves symlinks
    success, result = _run_eos(['eos', 'fileinfo', path.eos_path], mgm=path.mgm,
                        _false_if_stderr_contains='No such file or directory', **kwargs)
    if not success:
        return Path.stat(path, *args, **kwargs)
    if not result:
        raise FileNotFoundError
    return _parse_fileinfo(result, ftype)


def _eos_touch(path, *args, **kwargs):
    _assert_eos_accessible("Cannot touch EOS paths.")
    success, result = _run_eos(['eos', 'touch', path.eos_path], mgm=path.mgm, **kwargs)
    if success:
        return result
    return Path.touch(path, *args, **kwargs)

def _eos_unlink(path, *args, **kwargs):
    _assert_eos_accessible("Cannot unlink EOS paths.")
    if not path.is_symlink() and path.is_dir():
        raise IsADirectoryError(f"{path} is a directory.")
    success, result = _run_eos(['eos', 'rm', path.eos_path], mgm=path.mgm, **kwargs)
    if success:
        return result
    return Path.unlink(path, *args, **kwargs)

def _eos_mkdir(path, *args, **kwargs):
    _assert_eos_accessible("Cannot rmdir EOS paths.")
    success, result = _run_eos(['eos', 'mkdir', path.eos_path], mgm=path.mgm, **kwargs)
    if success:
        return result
    return Path.mkdir(path, *args, **kwargs)

def _eos_rmdir(path, *args, **kwargs):
    _assert_eos_accessible("Cannot rmdir EOS paths.")
    if path.is_symlink() or not path.is_dir():
        raise NotADirectoryError(f"{path} is not a directory.")
    success, result = _run_eos(['eos', 'rmdir', path.eos_path], mgm=path.mgm, **kwargs)
    if success:
        return result
    return Path.rmdir(path, *args, **kwargs)


# Overwrite FsPath methods
# ======================

def _eos_symlink_to(path, def_cls, target, target_is_directory=False, **kwargs):
    _assert_eos_accessible("Cannot create symlinks on EOS paths.")
    success, result = _run_eos(['eos', 'ln', '-fns', path.eos_path, target.as_posix()],
                               mgm=path.mgm, **kwargs)
    if success:
        return result
    from xaux.fs import FsPath
    return FsPath.symlink_to(path, target, target_is_directory)

def _eos_rmtree(path, def_cls, *args, **kwargs):
    _assert_eos_accessible("Cannot rmtree EOS paths.")
    if not path.is_dir():
        raise NotADirectoryError(f"{path} is not a directory.")
    success, result = _run_eos(['eos', 'rm', '-r', path.eos_path], mgm=path.mgm, **kwargs)
    if success:
        return result
    return def_cls.rmtree(path, *args, **kwargs)

def _eos_size(path, def_cls, *args, **kwargs):
    _assert_eos_accessible("Cannot get size of EOS paths.")
    if not path.is_file():
        return 0
    success, result = _run_eos(['eos', 'stat', path.eos_path], mgm=path.mgm, **kwargs)
    if success:
        return int(result.split()[3])
    return def_cls.size(path, *args, **kwargs)

