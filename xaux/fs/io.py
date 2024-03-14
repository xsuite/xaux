# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import numpy as np
from shutil import copy2, copytree
from subprocess import run, PIPE

from .fs import FsPath
from .eos import EosPath, _assert_eos_accessible, _xrdcp_installed, _eos_installed
from .temp import _tempdir


# If follow_symlinks=False, same as cp -P (hence a link is copied instead of its contents)
def cp(*args, recursive=False, follow_symlinks=True, force_xrdcp=False, force_eos=False, **kwargs):
    if len(args) < 2:
        return
    stderr = ""
    args = [FsPath(arg) for arg in args]
    if not recursive:
        for arg in args[:-1]:
            if arg.is_dir():
                raise ValueError(f"Cannot copy directory {arg}. Need to "
                               + f"specify `recursive=True`.")
    if np.any([isinstance(arg, EosPath) for arg in args]):
        if _xrdcp_installed or _eos_installed:
            path_args = [arg.eos_path_full if isinstance(arg, EosPath)
                         else arg.as_posix() for arg in args]
            if args[-1].is_dir() and path_args[-1][-1] != '/':
                path_args[-1] = path_args[-1] + '/'
            r = ['-r'] if recursive else []
        if _xrdcp_installed and not force_eos:
            opts = ['--cksum', 'adler32', '--xattr', '--rm-bad-cksum', \
                    '--parallel', '8', '--silent']
            if len(args) == 2:
                cmds = ['xrdcp', *r, *opts, *path_args]
            else:
                _temp = FsPath(_tempdir.name,"list_of_files").resolve()
                with _temp.open('w') as fid:
                    for arg in path_args[:-1]:
                        fid.write(arg + '\n')
                cmds = ['xrdcp', *r, *opts, '--infiles', _temp.as_posix(), path_args[-1]]
            cmd = run(cmds, stdout=PIPE, stderr=PIPE, check=True)
            if cmd.returncode == 0:
                return cmd.stdout.decode('UTF-8').strip().split('\n')
            else:
                cmd_mess = ' '.join(cmds)
                stderr  += f"Failed {cmd_mess}.\n"
                stderr  += cmd.stderr.decode('UTF-8').strip().split('\n')
        if _eos_installed and not force_xrdcp:
            opts = ['--streams', '8', '--silent']
            cmds = ['eos', 'cp', *r, *opts, *path_args]
            cmd = run(cmds, stdout=PIPE, stderr=PIPE, check=True)
            if cmd.returncode == 0:
                return cmd.stdout.decode('UTF-8').strip().split('\n')
            else:
                cmd_mess = ' '.join(cmds)
                stderr  += f"Failed {cmd_mess}.\n"
                stderr  += cmd.stderr.decode('UTF-8').strip().split('\n')
        _assert_eos_accessible("Cannot copy EOS paths.")
    if not force_xrdcp and not force_eos:
        if not recursive:
            for arg in args[:-1]:
                try:
                    copy2(arg, args[-1], follow_symlinks=follow_symlinks)
                except Exception as e:
                    stderr += f"Failed {cmd_mess}.\n"
                    stderr += str(e)
                    break
        else:
            for arg in args[:-1]:
                try:
                    copytree(arg, args[-1], symlinks=not follow_symlinks,
                                    copy_function=copy2)
                except Exception as e:
                    stderr += f"Failed {cmd_mess}.\n"
                    stderr += str(e)
                    break
    raise RuntimeError(stderr)


# If follow_symlinks=False, same as cp -P (hence a link is copied instead of its contents)
def mv(*args, recursive=False, follow_symlinks=True, force_xrdcp=False, force_eos=False, **kwargs):
    cp(*args, recursive=recursive, follow_symlinks=follow_symlinks, force_xrdcp=force_xrdcp,
       force_eos=force_eos, **kwargs)
    # If we got here, then the copy was successful
    for arg in args[:-1]:
        if arg.is_dir():
            arg.rmtree()
        else:
            arg.unlink()

