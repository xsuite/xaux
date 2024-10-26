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
ProtectFile._testing = True


def rewrite(pf, runtime=0.2):
    data = json.load(pf)
    time.sleep(runtime)
    data["myint"] += 1
    pf.seek(0)  # revert point to beginning of file
    json.dump(data, pf, indent=4, sort_keys=True)
    pf.truncate()


def change_file_protected(fname, max_lock_time=None, error_queue=None, wait=0.1, runtime=0.2, job_id=None):
    try:
        if job_id:
            t0 = time.time()
            print(f"Job {job_id} started  (stamp {t0})", flush=True)
        with ProtectFile(fname, "r+", wait=wait, max_lock_time=max_lock_time) as pf:
            if job_id:
                t1 = time.time()
                print(f"Job {job_id} in protectfile (init duration: {int(1e3*(t1 - t0))}ms)", flush=True)
            rewrite(pf, runtime)
            if job_id:
                t2 = time.time()
                print(f"Job {job_id} finished process in protectfile (process duration: {int(1e3*(t2 - t1))}ms)", flush=True)
        if job_id:
            t3 = time.time()
            print(f"Job {job_id} done (total duration: {int(1e3*(t3-t0))}ms, exit duration {int(1e3*(t3-t2))}ms, stamp {t2})", flush=True)
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
    t_prev = time.time()
    with ProtectFile(fname, "w", wait=0.1) as pf:
        init_time = time.time() - t_prev
        json.dump({"myint": 0}, pf, indent=4)
        dump_time = time.time() - t_prev - init_time
    exit_time = time.time() - t_prev - init_time - dump_time

    return init_time, dump_time, exit_time  # These are the times taken by the ProtectFile process


def propagate_child_errors(error_queue):
    while not error_queue.empty():
        raise error_queue.get()


def kill_process(proc, error_queue=None):
    os.kill(proc.pid, signal.SIGKILL)
    proc.join()
    # Check if the process raised an error
    if error_queue is not None:
        propagate_child_errors(error_queue)
