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
from .eos import EosPath
from .eos_methods import _assert_eos_accessible, _xrdcp_installed, _eos_installed
from .temp import _tempdir

# TODO: check symlinks etc


# If follow_symlinks=False, same as cp -P (hence a link is copied instead of its contents)
# TODO: follow_symlinks is not implemented when using xrcdp or eos
def cp(*args, recursive=False, follow_symlinks=True, **kwargs):
    if len(args) < 2:
        return
    from xaux.fs import _skip_eos, _force_eos, _force_xrdcp
    stdout = ""
    args = [FsPath(arg) for arg in args]
    target = args[-1].resolve()
    sources = args[:-1]
    # If we are copying a directory, we need to specify `recursive=True`
    if not recursive:
        for arg in sources:
            if arg.is_dir():
                raise IsADirectoryError(f"Cannot copy directory {arg}. Need to "
                                      + f"specify `recursive=True`.")
    if not target.is_dir():
        raise NotImplementedError
    for src in sources:
        stderr = ""    # Reset for every source
        if src.is_dir():
            rcrsv = True
            this_target = target / src.name
        else:
            rcrsv = False
        # If we are copying to EOS, we need a special treatment
        if isinstance(src, EosPath) or isinstance(target, EosPath):
            if not _skip_eos:
                # If either of the eos software is installed, we will use the full eos paths
                if _xrdcp_installed or _eos_installed:
                    path_src = src.eos_path_full if isinstance(src, EosPath) else src.as_posix()
                    path_target = target.eos_path_full if isinstance(target, EosPath) else target.as_posix()
                    if rcrsv:
                        r = ['-r']
                    else:
                        r = []
                        # We ensure that the target has a trailing '/'
                        if path_target[-1] != '/':
                            path_target = path_target + '/'
                # We first try to use xrdcp, and if that fails, we try eos
                if _xrdcp_installed and not _force_eos:
                    # Option --xattr is not supported on all machines
                    opts = ['--cksum', 'adler32', '--rm-bad-cksum'] # --silent
                    cmds = ['xrdcp', *r, *opts, path_src, path_target]
                        # # Multiple files are copied using a list of files
                        # _temp = FsPath(_tempdir.name, "list_of_files").resolve()
                        # with _temp.open('w') as fid:
                        #     for arg in path_args[:-1]:
                        #         fid.write(arg + '\n')
                        # cmds = ['xrdcp', *r, *opts, '--infiles', _temp.as_posix(), path_args[-1]]
                    cmd_mess = ' '.join(cmds)
                    failed = False
                    try:
                        cmd = run(cmds, stdout=PIPE, stderr=PIPE)
                        if cmd.returncode == 0:
                            stdout += cmd.stdout.decode('UTF-8').strip()
                            stdout += f"\nstderr: {cmd.stderr.decode('UTF-8').strip()}\n"
                            if not (target / src.name).exists():
                                failed = True
                                stderr += f"Failed {cmd_mess}. Target/src does not exist.\n"
                                stderr += cmd.stderr.decode('UTF-8').strip()
                                stderr += f"\nstdout: {cmd.stdout.decode('UTF-8').strip()}\n"
                        else:
                            failed = True
                            stderr += f"Failed {cmd_mess}.\n"
                            stderr += cmd.stderr.decode('UTF-8').strip()
                            stderr += f"\nstdout: {cmd.stdout.decode('UTF-8').strip()}\n"
                    except Exception as e:
                        stderr += f"Failed {cmd_mess}.\n"
                        stderr += str(e) + '\n'
                    else:
                        if not failed:
                            if stderr != "":
                                warnings.warn(f"Previous try failed:\n{stderr=}", RuntimeWarning)
                            continue
                    # finally:
                    #     # We clean up the temporary file
                    #     if len(args) > 2:
                    #         _temp.unlink()
                if _eos_installed and not _force_xrdcp:
                    opts = [] # --silent
                    cmds = ['eos', 'cp', *r, *opts, path_src, path_target]
                    cmd_mess = ' '.join(cmds)
                    failed = False
                    try:
                        if rcrsv:
                            # HACK because whatever, eos cp -r is not working
                            if isinstance(this_target, EosPath):
                                mgm = this_target.mgm
                            else:
                                mgm = src.mgm
                            path_src = src.as_posix()
                            path_target = this_target.as_posix()
                            if path_target[-1] != '/':
                                path_target = path_target + '/'
                            cmds = ['eos', 'cp', *r, *opts, path_src, path_target]
                            cmd_mess = ' '.join(cmds)
                            eos_env = {**os.environ, 'EOS_MGM_URL': mgm}
                            cmd = run(cmds, stdout=PIPE, stderr=PIPE, env=eos_env)
                        else:
                            cmd = run(cmds, stdout=PIPE, stderr=PIPE)
                        if cmd.returncode == 0:
                            stdout += cmd.stdout.decode('UTF-8').strip()
                            stdout += f"\nstderr: {cmd.stderr.decode('UTF-8').strip()}\n"
                            if not (target / src.name).exists():
                                failed = True
                                stderr += f"Failed {cmd_mess}. Target/src does not exist.\n"
                                stderr += cmd.stderr.decode('UTF-8').strip()
                                stderr += f"\nstdout: {cmd.stdout.decode('UTF-8').strip()}\n"
                        else:
                            failed = True
                            stderr += f"Failed {cmd_mess}.\n"
                            stderr += cmd.stderr.decode('UTF-8').strip()
                            stderr += f"\nstdout: {cmd.stdout.decode('UTF-8').strip()}\n"
                    except Exception as e:
                        stderr += f"Failed {cmd_mess}.\n"
                        stderr += str(e) + '\n'
                    else:
                        if not failed:
                            if stderr != "":
                                warnings.warn(f"Previous try failed:\n{stderr=}", RuntimeWarning)
                            continue
            if _force_xrdcp or _force_eos:
                raise OSError(stderr)
            # If we got here, then neither `xrdcp` nor `eos` were successful.
            # We can try to copy using a local mount, if it exists.
            _assert_eos_accessible(f"Cannot copy EOS paths.\n{stderr}")
        if rcrsv:
            try:
                copytree(src, this_target, symlinks=not follow_symlinks,
                         copy_function=copy2)
            except Exception as e:
                stderr += f"Failed copytree({src}, {this_target}, symlinks={not follow_symlinks}, "
                stderr += "copy_function=copy2).\n"
                stderr += str(e) + '\n'
                raise OSError(stderr)
        else:
            try:
                copy2(src, target, follow_symlinks=follow_symlinks)
            except Exception as e:
                stderr += f"Failed copy2({src}, {target}, follow_symlinks={follow_symlinks}).\n"
                stderr += str(e) + '\n'
                raise OSError(stderr)
    return stdout


# If follow_symlinks=False, same as cp -P (hence a link is copied instead of its contents)
def mv(*args, follow_symlinks=True, **kwargs):
    cp(*args, recursive=True, follow_symlinks=follow_symlinks, **kwargs)
    # If we got here, then the copy was successful
    for arg in args[:-1]:
        if arg.is_dir():
            arg.rmtree()
        else:
            arg.unlink()

