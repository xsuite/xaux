# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
from shutil import copy2, copytree
from subprocess import run, PIPE
import warnings

from .fs import FsPath
from .afs import AfsPath, _afs_mounted
from .eos import EosPath
from .eos_methods import _eos_mounted, _xrdcp_installed, _eoscmd_installed, _eos_version, _eos_version_int


# TODO:
#   - xrdcp: increase efficiency by using a list of files
#   - xrdcp: check if recursive still needs to be done manually
#   - xrdcp: can we parallelize?
#   - xrdcp and eos: implement follow_symlinks
#   - test if symlinks behave correctly
#   - EOS is very very slow


# We want to mimic the bash commands as much as possible
# cp file1 file2            file2 does not exist:         copies file1 into new file2
# cp file1 file2            file2 does exist:             copies file1 into file2 (overwrites file2)
# cp file1 file2 file3                                    error  "cp: target 'file3' is not a directory"
# cp file1 link1            link points to other file:    copies file1 into link1 (overwrites the contents of the linked file without renaming it)
# cp file1 link1            link points to file1:         error "cp: 'file1' and 'link1' are the same file"
# cp file1 file2 link1                                    error  "cp: target 'file3' is not a directory"
# cp file1 dir1                                           copies file1 into dir1 (potentially overwrites)
# cp file1 file2 ... dir1                                 copies files into dir1 (potentially overwrites)
# cp file1 file2 ... link1  link points to dir1:          copies files into dir1 (potentially overwrites)
# cp dir1 file1                                           error  "cp: -r not specified; omitting directory 'dir1'"
# cp -r dir1 file1                                        error  "cp: cannot overwrite non-directory 'file1' with directory 'dir1'"
# cp -r dir1 dir2           dir2 does not exist:          copies dir1 into new dir2
# cp -r dir1 dir2           dir2 does exist:              copies dir1 inside dir2
# links are treated as the file/dir they point to, unless -P is specified, in which case (only for links as source argument) they are treated as separate files


# If follow_symlinks=False, same as cp -P (hence a link is copied instead of its contents)
def cp(*args, recursive=False, follow_symlinks=True, **kwargs):
    # print("COPY"); import time; t_start = time.time(); t_prev = t_start
    if len(args) < 2:
        return
    this_stdout = ""
    this_stderr = ""
    args = [FsPath(arg).expanduser() for arg in args]
    target = args[-1].resolve()
    sources = args[:-1]
    # t_new = time.time(); print(f"{target=}, {sources=}  ({int(1e3*(t_new-t_prev))}ms)"); t_prev = t_new

    # Renaming is only allowed if there is a single source
    if len(sources) > 1:
        if not target.is_dir():
            raise OSError(f"cp: target '{target}' is not a directory")

    # Omitting directories if -r is not specified
    if not recursive:
        new_sources = []
        for src in sources:
            if src.is_dir():
                this_stdout += f"cp: -r not specified; omitting directory '{src}'"
            else:
                new_sources.append(src)
        sources = new_sources

    # Match target for each source and verify the syntax
    # t_new = time.time(); print(f"Before loop ({int(1e3*(t_new-t_prev))}ms)"); t_prev = t_new
    sources_targets = _loop_sources_and_verify(sources, target)
    # t_new = time.time(); print(f"After loop ({int(1e3*(t_new-t_prev))}ms)"); t_prev = t_new
    # print(f"{sources_targets=}")

    # Files on EOS or AFS need a special treatment
    if isinstance(target, EosPath):
        eos_sources_targets = sources_targets
        afs_sources_targets = []
        sources_targets = []
    elif isinstance(target, AfsPath):
        eos_sources_targets = [f for f in sources_targets if isinstance(f[0], EosPath)]
        afs_sources_targets = [f for f in sources_targets if not isinstance(f[0], EosPath)]
        sources_targets = []
    else:
        eos_sources_targets = [f for f in sources_targets if isinstance(f[0], EosPath)]
        afs_sources_targets = [f for f in sources_targets if isinstance(f[0], AfsPath)]
        sources_targets     = [f for f in sources_targets if not isinstance(f[0], EosPath)
                                                         and not isinstance(f[0], AfsPath)]

    # t_new = time.time(); print(f"Setup done ({int(1e3*(t_new-t_prev))}ms)"); t_prev = t_new
    # Do the copy
    stdout, stderr = _cp_regular(sources_targets, follow_symlinks)
    this_stdout += stdout
    this_stderr += stderr
    # t_new = time.time(); print(f"Regular done ({int(1e3*(t_new-t_prev))}ms)"); t_prev = t_new
    stdout, stderr = _cp_afs(afs_sources_targets, follow_symlinks)
    this_stdout += stdout
    this_stderr += stderr
    # t_new = time.time(); print(f"AFS done ({int(1e3*(t_new-t_prev))}ms)"); t_prev = t_new
    stdout, stderr = _cp_eos(eos_sources_targets, follow_symlinks)
    this_stdout += stdout
    this_stderr += stderr
    # t_new = time.time(); print(f"EOS done ({int(1e3*(t_new-t_prev))}ms)"); t_prev = t_new

    # Raise an exception if some files could not be copied
    if this_stderr:
       raise OSError(this_stderr)
    # print(f"COPY DONE  ({int(1e3*(time.time() - t_start))}ms)")
    # print()
    # print()

    return this_stdout


# If follow_symlinks=False, same as cp -P (hence a link is copied instead of its contents)
def mv(*args, follow_symlinks=True, **kwargs):
    # print("MOVE"); import time; t_start = time.time()
    stdout = cp(*args, recursive=True, follow_symlinks=follow_symlinks, **kwargs)
    # If we got here, then the copy was successful
    for arg in args[:-1]:
        if arg.is_dir():
            arg.rmtree()
        else:
            arg.unlink()
    # print(f"MOVE DONE  ({int(1e3*(time.time() - t_start))}ms)")
    # print()
    # print()
    return stdout


# ===================
# Low-level functions
# ===================

def _loop_sources_and_verify(sources, target):
    src_target_recursive = []
    for src in sources:
        if src.is_dir():
            if target.exists():
                if not target.is_dir():
                    raise OSError(f"cp: cannot overwrite non-directory '{target}' with directory '{src}'\n")
                this_target = target / src.name
            elif target.parent.exists():
                # This includes a potential renaming
                this_target = target
            else:
                raise OSError(f"cp: cannot create directory '{target}': No such file or directory\n")
            if src in this_target.parents:
                raise OSError(f"cp: cannot copy a directory, '{src}', into itself, '{target}'\n")
            src_target_recursive.append([src, this_target, True])

        else:
            if target.exists():
                if target.is_dir():
                    this_target = target / src.name
                else:
                    # We are overwriting the target
                    this_target = target
            elif target.parent.exists():
                # This includes a potential renaming
                this_target = target
            else:
                raise OSError(f"cp: cannot create regular file '{target}': No such file or directory")
            if this_target == src:
                raise OSError(f"cp: '{src}' and '{this_target}' are the same file\n")
            src_target_recursive.append([src, this_target, False])

    return src_target_recursive


def _cp_regular(sources_targets, follow_symlinks):
    stdout = ""
    stderr = ""
    for src, target, recursive in sources_targets:
        if recursive:
            cmd_mess  = f"copytree({src}, {target}, symlinks={not follow_symlinks}, "
            cmd_mess += "copy_function=copy2)"
            try:
                this_stdout = copytree(src.as_posix(), target.as_posix(), symlinks=not follow_symlinks, copy_function=copy2)
                if this_stdout is not None:
                    stdout += this_stdout
                # Verify the files exist
                if not target.exists():
                    stderr += f"Failed {cmd_mess}:\n"
                    stderr += f"   Target {target} does not exist.\n"
            except Exception as e:
                stderr += f"Failed {cmd_mess}:\n"
                stderr += f"   {str(e)}\n"

        else:
            cmd_mess = f"copy2({src}, {target}, follow_symlinks={follow_symlinks})"
            try:
                this_stdout = copy2(src.as_posix(), target.as_posix(), follow_symlinks=follow_symlinks)
                if this_stdout is not None:
                    stdout += this_stdout
                # Verify the files exist
                if not target.exists():
                    stderr += f"Failed {cmd_mess}:\n"
                    stderr += f"   Target {target} does not exist.\n"
            except Exception as e:
                stderr += f"Failed {cmd_mess}:\n"
                stderr += f"   {str(e)}\n"

    return stdout, stderr  # An empty error message means success


def _cp_afs(sources_targets, follow_symlinks):
    from xaux.fs import _skip_afs_software, _force_xrdcp
    this_stdout = ""
    this_stderr = ""
    if _skip_afs_software:
        assert not _force_xrdcp

    # We first try to use xrdcp
    if sources_targets and _xrdcp_installed and not _skip_afs_software:
        sources_targets, stdout, stderr = _cp_xrdcp(sources_targets)
        this_stdout += stdout
        this_stderr += stderr

    # If xrdcp failed, we try to use the AFS mout
    regular_stderr = ""
    if sources_targets:
        if _force_xrdcp:
            this_stderr += "Skipping AFS mount.\n"
            this_stderr += "Failed to copy files to AFS.\n"
            return this_stdout, this_stderr
        if not _afs_mounted:
            this_stderr += "No AFS mount available.\n"
            this_stderr += "Failed to copy files to AFS.\n"
            return this_stdout, this_stderr
        regular_stdout, regular_stderr = _cp_regular(sources_targets, follow_symlinks)
        this_stdout += regular_stdout

    if not regular_stderr:
        # All files are copied successfully
        if this_stderr:
            # Just raise a warning that some earlier steps failed
            warnings.warn(this_stderr, RuntimeWarning)
        return this_stdout, ""  # An empty error message means success
    else:
        return this_stdout, this_stderr + regular_stderr


def _cp_eos(sources_targets, follow_symlinks):
    from xaux.fs import _skip_eos_software, _force_eoscmd, _force_xrdcp
    this_stdout = ""
    this_stderr = ""
    if _skip_eos_software:
        assert not _force_eoscmd
        assert not _force_xrdcp

    # We first try to use xrdcp
    if sources_targets and _xrdcp_installed and not _force_eoscmd and not _skip_eos_software:
        sources_targets, stdout, stderr = _cp_xrdcp(sources_targets)
        this_stdout += stdout
        this_stderr += stderr

    # If xrdcp failed, we try to use eos
    if sources_targets and _eoscmd_installed and not _force_xrdcp and not _skip_eos_software:
        sources_targets, stdout, stderr = _cp_eoscmd(sources_targets)
        this_stdout += stdout
        this_stderr += stderr

    # If eos also failed, we try using the EOS mount
    regular_stderr = ""
    if sources_targets:
        if _force_xrdcp or _force_eoscmd:
            this_stderr += "Skipping EOS mount.\n"
            this_stderr += "Failed to copy files to EOS.\n"
            return this_stdout, this_stderr
        if not _eos_mounted:
            this_stderr += "No EOS mount available.\n"
            this_stderr += "Failed to copy files to EOS.\n"
            return this_stdout, this_stderr
        regular_stdout, regular_stderr = _cp_regular(sources_targets, follow_symlinks)
        this_stdout += regular_stdout

    if not regular_stderr:
        # All files are copied successfully
        if this_stderr:
            # Just raise a warning that some earlier steps failed
            warnings.warn(this_stderr, RuntimeWarning)
        return this_stdout, ""  # An empty error message means success
    else:
        return this_stdout, this_stderr + regular_stderr


def _cp_xrdcp(sources_targets):
    from xaux.fs import _xrdcp_use_ipv4
    stderr = ""
    stdout = ""
    # Option --xattr is not supported on all machines
    # f'--sources {min(len(path_src), 15)}' f'--streams {min(len(path_src), 15)}' f'--parallel {min(len(path_src), 15)}'
    opts = ['--cksum', 'adler32', '--force', '--nopbar', '--rm-bad-cksum']
    if _xrdcp_use_ipv4:
        env = {'env': {**os.environ, 'XRD_NETWORKSTACK': 'IPv4'}}
    else:
        env = {}

    # TODO: increase efficiency by using a list of files
    # path_src = [src.eos_path_full if isinstance(src, EosPath) else src.as_posix() for src in sources]
    # infiles = path_src
    # if len(path_src) > 1:
    #     # Multiple files are copied using a list of files
    #     _temp = FsPath(f"list_of_files_{ranID()}").resolve()
    #     with _temp.open('w') as fid:
    #         for arg in path_src[:-1]:
    #             fid.write(arg + '\n')
    #     infiles = ['--infiles', _temp.as_posix()]

    cmd_data = []
    for src, target, recursive in sources_targets:
        if recursive:
            if not isinstance(target, EosPath) and not isinstance(target, AfsPath):
                # Not an XRootD path so -r works
                path_src = src.eos_path_full if isinstance(src, EosPath) else src.as_posix()
                path_target = target.eos_path_full if isinstance(target, EosPath) else target.as_posix()
                cmd_data.append(['xrdcp', '-r', *opts, path_src, path_target, src, target, True])
            else:
                # Manually walk through the directory
                for new_src in src.rglob('*'):
                    if new_src.is_dir():
                        # xrdcp automatically creates parent directories
                        continue
                    path_src = new_src.eos_path_full if isinstance(new_src, EosPath) else new_src.as_posix()
                    new_target = target / new_src.relative_to(src)
                    path_target = new_target.eos_path_full if isinstance(new_target, EosPath) else new_target.as_posix()
                    cmd_data.append(['xrdcp', *opts, path_src, path_target, new_src, new_target, False])

        else:
            path_src = src.eos_path_full if isinstance(src, EosPath) else src.as_posix()
            path_target = target.eos_path_full if isinstance(target, EosPath) else target.as_posix()
            cmd_data.append(['xrdcp', *opts, path_src, path_target, src, target, False])

    for this_cmd_data in cmd_data:
        src = this_cmd_data[-3]
        target = this_cmd_data[-2]
        this_cmd = this_cmd_data[:-3]
        cmd_mess = ' '.join(this_cmd)
        try:
            this_stderr = ""
            cmd = run(this_cmd, stdout=PIPE, stderr=PIPE, **env)
            if cmd.returncode == 0:
                # Verify the files exist
                if not target.exists():
                    this_stderr += f"Failed {cmd_mess}:\n"
                    this_stderr += f"   Target {target} does not exist.\n"
            else:
                this_stderr += f"Failed {cmd_mess}:\n"
                this_stderr += f"   {cmd.stderr.decode('UTF-8').strip()}\n"
            this_stdout = cmd.stdout.decode('UTF-8').strip()
            stderr += this_stderr
            if this_stdout:
                stdout += f"{this_stdout}\n"
                if this_stderr:
                    stderr += f"   stdout: {this_stdout}\n"
        except Exception as e:
            stderr += f"Failed {cmd_mess}:\n"
            stderr += f"   {str(e)}\n"
        # else:
        #     # Clean up the temporary file
        #     if infiles[0] == '--infiles':
        #         _temp.unlink()

    sources_targets = [f[-3:] for f in cmd_data if not f[-2].exists()]

    return sources_targets, stdout, stderr


def _cp_eoscmd(sources_targets):
    stderr = ""
    stdout = ""
    cmd_data = []
    for src, target, recursive in sources_targets:
        if recursive:
            if _eos_version_int >= 9000000: # 5002021 DOES NOT WORK
                # -r works
                path_src = src.eos_path if isinstance(src, EosPath) else src.as_posix()
                if src.is_dir() and path_src[-1] != '/':
                    path_src = path_src + '/'
                path_target = target.eos_path if isinstance(target, EosPath) else target.as_posix()
                if target.is_dir() and path_target[-1] != '/':
                    path_target = path_target + '/'
                cmd_data.append(['eos', 'cp', '-r', path_src, path_target, src, target, True])
            else:
                # Manually walk through the directory
                for new_src in src.rglob('*'):
                    if new_src.is_dir():
                        new_src.mkdir(parents=True, exist_ok=True)
                        continue
                    path_src = new_src.eos_path if isinstance(new_src, EosPath) else new_src.as_posix()
                    if new_src.is_dir() and path_src[-1] != '/':
                        path_src = path_src + '/'
                    new_target = target / new_src.relative_to(src)
                    path_target = new_target.eos_path if isinstance(new_target, EosPath) else new_target.as_posix()
                    if new_target.is_dir() and path_target[-1] != '/':
                        path_target = path_target + '/'
                    cmd_data.append(['eos', 'cp', path_src, path_target, new_src, new_target, False])

        else:
            path_src = src.eos_path if isinstance(src, EosPath) else src.as_posix()
            if src.is_dir() and path_src[-1] != '/':
                path_src = path_src + '/'
            path_target = target.eos_path if isinstance(target, EosPath) else target.as_posix()
            if target.is_dir() and path_target[-1] != '/':
                path_target = path_target + '/'
            cmd_data.append(['eos', 'cp', path_src, path_target, src, target, False])

    for this_cmd_data in cmd_data:
        src = this_cmd_data[-3]
        target = this_cmd_data[-2]
        this_cmd = this_cmd_data[:-3]
        cmd_mess = ' '.join(this_cmd)
        if isinstance(target, EosPath):
            mgm = target.mgm
        else:
            mgm = src.mgm
        eos_env = {**os.environ, 'EOS_MGM_URL': mgm}
        try:
            this_stderr = ""
            cmd = run(this_cmd, stdout=PIPE, stderr=PIPE, env=eos_env)
            if cmd.returncode == 0:
                # Verify the files exist
                if not target.exists():
                    this_stderr += f"Failed {cmd_mess}:\n"
                    this_stderr += f"   Target {target} does not exist.\n"
            else:
                this_stderr += f"Failed {cmd_mess}:\n"
                this_stderr += f"   {cmd.stderr.decode('UTF-8').strip()}\n"
            this_stdout = cmd.stdout.decode('UTF-8').strip()
            stderr += this_stderr
            if this_stdout:
                stdout += f"{this_stdout}\n"
                if this_stderr:
                    stderr += f"   stdout: {this_stdout}\n"
        except Exception as e:
            stderr += f"Failed {cmd_mess}:\n"
            stderr += f"   {str(e)}\n"

    sources_targets = [f[-3:] for f in cmd_data if not f[-2].exists()]

    return sources_targets, stdout, stderr
