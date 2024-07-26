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


def rewrite(pf, runtime=0.2):
    data = json.load(pf)
    time.sleep(runtime)
    data["myint"] += 1
    pf.seek(0)  # revert point to beginning of file
    json.dump(data, pf, indent=4, sort_keys=True)
    pf.truncate()


def change_file_protected(fname, max_lock_time=None, error_queue=None, wait=0.1, runtime=0.2):
    try:
        with ProtectFile(fname, "r+", wait=wait, max_lock_time=max_lock_time) as pf:
            rewrite(pf, runtime)
    except Exception as e:
        if error_queue is None:
            raise e
        else:
            error_queue.put(e)
    return


def change_file_standard(fname):
    with open(fname, "r+") as pf:  # fails with this context
        rewrite(pf)
    return


def init_file(fname):
    # Remove leftover lockfiles
    for f in FsPath.cwd().glob(f"{fname}.lock*"):
        f.unlink()
    # Initialise file
    with ProtectFile(fname, "w", wait=1) as pf:
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
