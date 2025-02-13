# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import os
import json
import time
import pytest
import signal
from multiprocessing import Pool, Process, Queue

from xaux import FsPath, ProtectFile


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



def test_deliberate_failure():
    fname = "standard_file.json"
    init_file(fname)

    workers = 4
    with Pool(processes=workers) as pool:
        pool.map(change_file_standard, [fname] * 4)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] != workers  # assert that result is wrong

    FsPath(fname).unlink()


@pytest.mark.parametrize("workers", [4, 100])
def test_protection(workers):
    fname = "protected_file.json"
    init_file(fname)

    with Pool(processes=workers) as pool:
        pool.map(change_file_protected, [(fname)] * workers)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == workers

    FsPath(fname).unlink()


# TODO: on some systems, multiprocessing can take considerable time to start up (then the test will fail)

def test_normal_wait():
    fname = "test_normal_wait.json"
    lock_file = f"{fname}.lock"
    sys_init_time, sys_dump_time, sys_exit_time = init_file(fname)
    print(f"ProtectFile takes ~{1e3*sys_init_time}ms, ~{1e3*sys_dump_time}ms, "
        + f"~{1e3*sys_exit_time}ms on this system")

    t0 = time.time()
    n_concurrent = 20

    error_queue = Queue()
    procs = [
        # args: name, max_lock_time, error_queue, wait, runtime, job_id
        Process(target=change_file_protected, args=(fname, None, error_queue, 2, 1.5, i))
        for i in range(n_concurrent)
    ]

    for proc in procs:
        proc.start()
        time.sleep(0.001)

    for proc in procs:
        proc.join()

    propagate_child_errors(error_queue)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == n_concurrent
    assert not FsPath(lock_file).exists()

    print(f"Total time for {n_concurrent} concurrent jobs: {time.time() - t0:.2f}s")

    FsPath(fname).unlink()


def test_normal_crashed():
    fname = "test_normal_wait.json"
    lock_file = f"{fname}.lock"
    sys_init_time, sys_dump_time, sys_exit_time = init_file(fname)
    print(f"ProtectFile takes ~{1e3*sys_init_time}ms, ~{1e3*sys_dump_time}ms, "
        + f"~{1e3*sys_exit_time}ms on this system")

    t0 = time.time()
    n_concurrent = 20

    error_queue = Queue()
    procs = [
        # args: name, max_lock_time, error_queue, wait, runtime, job_id
        Process(target=change_file_protected, args=(fname, None, error_queue, 2, 1.5, i))
        for i in range(n_concurrent)
    ]

    for i, proc in enumerate(procs):
        proc.start()
        time.sleep(0.001)
        if i == 0:
            # This timing is very sensitive to the system; on some systems the process is almost finished
            # after this time while on others it did not even start yet...
            time.sleep(1.25)
            kill_process(proc, error_queue)
            with open(fname, "r") as pf:
                data = json.load(pf)
                assert data["myint"] == 0
            assert FsPath(lock_file).exists()

    # After a bit more than a minute, the situation should not have changed
    time.sleep(90)
    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == 0
    assert FsPath(lock_file).exists()

    # So we manually remove the lockfile, and the situation should resolve itself
    FsPath(lock_file).unlink()
    for proc in procs:
        proc.join()

    propagate_child_errors(error_queue)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == n_concurrent - 1
    assert not FsPath(lock_file).exists()

    print(f"Total time for {n_concurrent} concurrent jobs: {time.time() - t0:.2f}s")

    FsPath(fname).unlink()


def test_max_lock_time_wait():
    fname = "test_max_lock_time_wait.json"
    lock_file = f"{fname}.lock"
    sys_init_time, sys_dump_time, sys_exit_time = init_file(fname)
    print(f"ProtectFile takes ~{1e3*sys_init_time}ms, ~{1e3*sys_dump_time}ms, "
        + f"~{1e3*sys_exit_time}ms on this system")

    t0 = time.time()
    n_concurrent = 20

    error_queue = Queue()
    procs = [
        # args: name, max_lock_time, error_queue, wait, runtime, job_id
        Process(target=change_file_protected, args=(fname, 90, error_queue, 2, 1.5, i))
        for i in range(n_concurrent)
    ]

    for proc in procs:
        proc.start()
        time.sleep(0.001)

    for proc in procs:
        proc.join()

    propagate_child_errors(error_queue)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == n_concurrent
    assert not FsPath(lock_file).exists()

    print(f"Total time for {n_concurrent} concurrent jobs: {time.time() - t0:.2f}s")

    FsPath(fname).unlink()


def test_max_lock_time_crashed():
    fname = "test_max_lock_time_wait.json"
    lock_file = f"{fname}.lock"
    sys_init_time, sys_dump_time, sys_exit_time = init_file(fname)
    print(f"ProtectFile takes ~{1e3*sys_init_time}ms, ~{1e3*sys_dump_time}ms, "
        + f"~{1e3*sys_exit_time}ms on this system")

    t0 = time.time()
    n_concurrent = 20

    error_queue = Queue()
    procs = [
        # args: name, max_lock_time, error_queue, wait, runtime, job_id
        Process(target=change_file_protected, args=(fname, 90, error_queue, 2, 1.5, i))
        for i in range(n_concurrent)
    ]

    for i, proc in enumerate(procs):
        proc.start()
        time.sleep(0.001)
        if i == 0:
            # This timing is very sensitive to the system; on some systems the process is almost finished
            # after this time while on others it did not even start yet...
            time.sleep(1.25)
            kill_process(proc, error_queue)
            with open(fname, "r") as pf:
                data = json.load(pf)
                assert data["myint"] == 0
            assert FsPath(lock_file).exists()

    # The situation should now resolve itself as there is a max_lock_time
    for proc in procs:
        proc.join()

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == n_concurrent - 1
    assert not FsPath(lock_file).exists()

    propagate_child_errors(error_queue)

    print(f"Total time for {n_concurrent} concurrent jobs: {time.time() - t0:.2f}s")

    FsPath(fname).unlink()
