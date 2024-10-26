# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #import json

from pathlib import Path
from multiprocessing import Process, Queue
import time
import pytest
import json

from xaux import ProtectFile
from _test_helpers import init_file, change_file_protected, propagate_child_errors, kill_process


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
    assert not Path(lock_file).exists()

    print(f"Total time for {n_concurrent} concurrent jobs: {time.time() - t0:.2f}s")

    Path(fname).unlink()


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
            assert Path(lock_file).exists()

    # After a bit more than a minute, the situation should not have changed
    time.sleep(90)
    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == 0
    assert Path(lock_file).exists()

    # So we manually remove the lockfile, and the situation should resolve itself
    Path(lock_file).unlink()
    for proc in procs:
        proc.join()

    propagate_child_errors(error_queue)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == n_concurrent - 1
    assert not Path(lock_file).exists()

    print(f"Total time for {n_concurrent} concurrent jobs: {time.time() - t0:.2f}s")

    Path(fname).unlink()


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
    assert not Path(lock_file).exists()

    print(f"Total time for {n_concurrent} concurrent jobs: {time.time() - t0:.2f}s")

    Path(fname).unlink()


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
            assert Path(lock_file).exists()

    # The situation should now resolve itself as there is a max_lock_time
    for proc in procs:
        proc.join()

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == n_concurrent - 1
    assert not Path(lock_file).exists()

    propagate_child_errors(error_queue)

    print(f"Total time for {n_concurrent} concurrent jobs: {time.time() - t0:.2f}s")

    Path(fname).unlink()
