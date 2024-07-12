# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import time
import json
import shutil
import os
import signal

from xaux import ProtectFile, FsPath


ProtectFile._debug = True


def rewrite(pf, with_copy=False):
    data = json.load(pf)
    time.sleep(0.2)
    data["myint"] += 1
    if not with_copy:
        pf.seek(0)  # revert point to beginning of file
        json.dump(data, pf, indent=4, sort_keys=True)
        pf.truncate()
    else:  # write to another file and copy back
        cfname = "_copy_" + pf.name
        with open(cfname, "w") as cf:
            json.dump(data, cf, indent=4, sort_keys=True)
        shutil.copyfile(cfname, pf.name)
        FsPath.unlink(FsPath(cfname))


def change_file_protected(fname, with_copy=False, max_lock_time=None, error_queue=None):
    try:
        with ProtectFile(fname, "r+", backup=False, wait=0.1, max_lock_time=max_lock_time) as pf:
            rewrite(pf, with_copy=with_copy)
    except Exception as e:
        if error_queue is None:
            raise e
        else:
            error_queue.put(e)
    return


def change_file_standard(fname, with_copy=False):
    with open(fname, "r+") as pf:  # fails with this context
        rewrite(pf)
    return


def init_file(fname):
    # Remove leftover lockfiles
    for f in FsPath.cwd().glob(f"{fname}.lock*"):
        f.unlink()
    # Initialise file
    with ProtectFile(fname, "w", backup=False, wait=1) as pf:
        json.dump({"myint": 0}, pf, indent=4)


def propagate_child_errors(error_queue):
    while not error_queue.empty():
        raise error_queue.get()


def kill_process(proc, error_queue=None):
    os.kill(proc.pid, signal.SIGKILL)
    proc.join()
    # Check if the process raised an error
    if error_queue is not None:
        propagate_child_errors(error_queue)
