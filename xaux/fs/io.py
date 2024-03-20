# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
import numpy as np
from shutil import copy2, copytree
from subprocess import run, PIPE, CalledProcessError
import warnings

from .fs import FsPath
from .eos import EosPath, _assert_eos_accessible, _eos_installed
from .temp import _tempdir

# TODO: check symlinks etc


_xrdcp_installed = False
if os.name != 'nt':
    try:
        cmd = run(["xrdcp", "--version"], stdout=PIPE, stderr=PIPE)
        _xrdcp_installed = cmd.returncode == 0
    except (CalledProcessError, FileNotFoundError):
        _xrdcp_installed = False


# If follow_symlinks=False, same as cp -P (hence a link is copied instead of its contents)
def cp(*args, recursive=False, follow_symlinks=True, _force_xrdcp=False, _force_eos=False, **kwargs):
    if len(args) < 2:
        return
    stdout = ""
    stderr = ""
    failed = False
    args = [FsPath(arg) for arg in args]
    # If we are copying a directory, we need to specify `recursive=True`
    if not recursive:
        for arg in args[:-1]:
            if arg.is_dir():
                raise IsADirectoryError(f"Cannot copy directory {arg}. Need to "
                               + f"specify `recursive=True`.")
    # If we are copying to EOS, we need a special treatment
    if np.any([isinstance(arg, EosPath) for arg in args]):
        # If either of the eos software is installed, we will use the full eos paths
        if _xrdcp_installed or _eos_installed:
            path_args = [arg.eos_path_full if isinstance(arg, EosPath)
                         else arg.as_posix() for arg in args]
            # We ensure that directories have a trailing '/'
            if args[-1].is_dir() and path_args[-1][-1] != '/':
                path_args[-1] = path_args[-1] + '/'
            r = ['-r'] if recursive else []
        # We first try to use xrdcp, and if that fails, we try eos
        if _xrdcp_installed and not _force_eos:
            p = ['--parallel', f"{min(len(args) - 1, 8)}"] if len(args) > 2 or recursive else []
            # Option --xattr is not supported on all machines
            opts = ['--cksum', 'adler32', '--rm-bad-cksum', *p] # --silent
            if len(args) == 2:
                cmds = ['xrdcp', *r, *opts, *path_args]
            else:
                # Multiple files are copied using a list of files
                _temp = FsPath(_tempdir.name, "list_of_files").resolve()
                with _temp.open('w') as fid:
                    for arg in path_args[:-1]:
                        fid.write(arg + '\n')
                cmds = ['xrdcp', *r, *opts, '--infiles', _temp.as_posix(), path_args[-1]]
            cmd_mess = ' '.join(cmds)
            try:
                cmd = run(cmds, stdout=PIPE, stderr=PIPE)
                if cmd.returncode == 0:
                    stdout += cmd.stdout.decode('UTF-8').strip()
                else:
                    failed = True
                    stderr  += f"Failed {cmd_mess}.\n"
                    stderr  += cmd.stderr.decode('UTF-8').strip()
            except Exception as e:
                stderr += f"Failed {cmd_mess}.\n"
                stderr += str(e) + '\n'
            else:
                if not failed:
                    if stderr != "":
                        warnings.warn(f"Previous try failed:\n{stderr=}", RuntimeWarning)
                    return stdout
            finally:
                # We clean up the temporary file
                if len(args) > 2:
                    _temp.unlink()
        if _eos_installed and not _force_xrdcp:
            p = ['--streams', f"{min(len(args) - 1, 8)}"] if len(args) > 2 or recursive  else []
            opts = [*p] # --silent
            cmds = ['eos', 'cp', *r, *opts, *path_args]
            cmd_mess = ' '.join(cmds)
            try:
                cmd = run(cmds, stdout=PIPE, stderr=PIPE)
                if cmd.returncode == 0:
                    stdout += cmd.stdout.decode('UTF-8').strip()
                else:
                    failed = True
                    stderr  += f"Failed {cmd_mess}.\n"
                    stderr  += cmd.stderr.decode('UTF-8').strip()
            except Exception as e:
                stderr += f"Failed {cmd_mess}.\n"
                stderr += str(e) + '\n'
            else:
                if not failed:
                    if stderr != "":
                        warnings.warn(f"Previous try failed:\n{stderr=}", RuntimeWarning)
                    return stdout
        # If we got here, then neither `xrdcp` nor `eos` were successful.
        # We can try to copy using a local mount, if it exists.
        _assert_eos_accessible(f"Cannot copy EOS paths.\n{stderr}")
    if not _force_xrdcp and not _force_eos:
        if not recursive:
            for arg in args[:-1]:
                try:
                    copy2(arg, args[-1], follow_symlinks=follow_symlinks)
                except Exception as e:
                    stderr += f"Failed {cmd_mess}.\n"
                    stderr += str(e) + '\n'
                    break
        else:
            for arg in args[:-1]:
                try:
                    copytree(arg, args[-1], symlinks=not follow_symlinks,
                             copy_function=copy2)
                except Exception as e:
                    stderr += f"Failed {cmd_mess}.\n"
                    stderr += str(e) + '\n'
                    break
        return
    # If we got here, then the copy was not successful
    raise RuntimeError(stderr)


# If follow_symlinks=False, same as cp -P (hence a link is copied instead of its contents)
def mv(*args, recursive=False, follow_symlinks=True, _force_xrdcp=False, _force_eos=False, **kwargs):
    cp(*args, recursive=recursive, follow_symlinks=follow_symlinks, _force_xrdcp=_force_xrdcp,
       _force_eos=_force_eos, **kwargs)
    # If we got here, then the copy was successful
    _assert_eos_accessible(f"Copy was succesful, but cannot remove EOS paths.")
    for arg in args[:-1]:
        if arg.is_dir():
            arg.rmtree()
        else:
            arg.unlink()

