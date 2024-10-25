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
ProtectFile._testing = True
from _test_helpers import init_file, change_file_protected, propagate_child_errors, kill_process


def test_max_lock_time():
    fname = "test_max_lock_time.json"
    lock_file = f"{fname}.lock"
    init_file(fname)

    error_queue = Queue()
    procA = Process(target=change_file_protected, args=(fname, 1.5, error_queue, 0.45, 0.3))
    procB = Process(target=change_file_protected, args=(fname, 1.5, error_queue, 0.45, 0.3))

    procA.start() # Lock takes 0.1s - 0.2s to create (due to flush) and job takes 0.3s to complete
    time.sleep(0.38)
    assert Path(lock_file).exists()

    # B will try to access the file while A is still running, and will try
    # again ~0.3s later by which time A has finished (and the lock will have
    # disappeared).
    procB.start()

    # A finished, B did not retry yet
    time.sleep(0.37)
    assert not Path(lock_file).exists()  # B did not retry yet
    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == 1              # A finished

    # Now B is running
    time.sleep(0.40)
    assert Path(lock_file).exists()

    procA.join()
    procB.join()

    propagate_child_errors(error_queue)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == 2              # B finished

    Path(fname).unlink()


def test_max_lock_time_crashed():
    fname = "test_max_lock_time_crashed.json"
    init_file(fname)

    error_queue = Queue()
    procA = Process(target=change_file_protected, args=(fname, 5, error_queue))
    procB = Process(target=change_file_protected, args=(fname, 5, error_queue))

    procA.start()
    procB.start()
    start = time.time()

    # We kill process A after 0.1s such that we have a hanging lockfile
    time.sleep(0.1)
    kill_process(procA, error_queue)
    assert Path(f"{fname}.lock").exists()

    # After 5s the lockfile is allowed to be force-freed.
    # First we check that just before that (4.6s), B was not able to alter the file:
    time.sleep(4)
    with open(fname, "r") as pf:
        data = json.load(pf)
        assert data["myint"] == 0

    # The job B should take 0.3-0.4s to complete (5.4s after the start of job A)
    time.sleep(1.3)
    procB.join()

    # Process B was able to complete its work directly after the max_lock_time
    stop = time.time()
    elapsed_time = stop - start
    assert elapsed_time < 5.7

    propagate_child_errors(error_queue)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == 1

    Path(fname).unlink()


def test_max_lock_time_multiple():
    fname = "test_max_lock_time_multiple.json"
    init_file(fname)
    n_concurrent = 20

    error_queue = Queue()
    procs = [
        Process(target=change_file_protected, args=(fname, 30, error_queue))
        for _ in range(n_concurrent)
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

    Path(fname).unlink()


def test_max_lock_time_multiple_crashed():
    fname = "test_max_lock_time_multiple_crashed.json"
    init_file(fname)
    n_concurrent = 20

    error_queue = Queue()
    procs = [
        Process(target=change_file_protected, args=(fname, 5, error_queue))
        for _ in range(n_concurrent)
    ]

    # We start the first process and kill it such that we have a hanging lockfile
    procs[0].start()
    time.sleep(0.02)
    kill_process(procs[0], error_queue)
    assert Path(f"{fname}.lock").exists()
    with open(fname, "r") as pf:
        data = json.load(pf)
        assert data["myint"] == 0

    # Start all other processes
    for proc in procs[1:]:
        proc.start()
        time.sleep(0.001)

    # After 5s the lockfile is allowed to be force-freed.
    # First we check that before that (4.25s), none of them was able to alter the file yet:
    time.sleep(4.2)
    with open(fname, "r") as pf:
        data = json.load(pf)
        assert data["myint"] == 0

    # We let them all finish
    for proc in procs:
        proc.join()

    propagate_child_errors(error_queue)

    # And we confirm all jobs were able to complete succesfully (except the first)
    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == n_concurrent - 1

    Path(fname).unlink()
