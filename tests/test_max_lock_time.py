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


def test_max_lock_time():
    fname = "test_max_lock_time.json"
    init_file(fname)

    error_queue = Queue()
    procA = Process(target=change_file_protected, args=(fname, False, 1, error_queue))
    procB = Process(target=change_file_protected, args=(fname, False, 1, error_queue))

    procA.start() # Will take > 0.2s
    time.sleep(0.18)
    assert Path(f"{fname}.lock").exists()

    # B will try to access the file while A is still running, and will try
    # again ~0.1s later by which time A has finished (and the lock will have
    # disappeared).
    procB.start()

    # A finished, B did not retry yet
    time.sleep(0.05)
    assert not Path(f"{fname}.lock").exists()  # B did not retry yet
    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == 1              # A finished

    # Now B is running
    time.sleep(0.08)
    assert Path(f"{fname}.lock").exists()

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
    procA = Process(target=change_file_protected, args=(fname, False, 5, error_queue))
    procB = Process(target=change_file_protected, args=(fname, False, 5, error_queue))

    procA.start()
    procB.start()
    start = time.time()

    # We kill process A after 0.1s such that we have a hanging lockfile
    time.sleep(0.1)
    kill_process(procA, error_queue)
    assert Path(f"{fname}.lock").exists()

    # After 6s (5s * 1.2) the lockfile is allowed to be force-freed.
    # First we check that just before that, B was not able to alter the file:
    time.sleep(6.1) # 6s max_lock_time + 0.2s rewrite time - 0.1s already waited
    with open(fname, "r") as pf:
        data = json.load(pf)
        assert data["myint"] == 0
    procB.join()

    # Process B was able to complete its work directly after the max_lock_time
    stop = time.time()
    elapsed_time = stop - start
    assert elapsed_time < 6.5

    propagate_child_errors(error_queue)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == 1

    Path(fname).unlink()


def test_max_lock_time_nested():
    fname = "test_max_lock_time_nested.json"
    init_file(fname)
    n_concurrent = 20

    error_queue = Queue()
    procs = [
        Process(target=change_file_protected, args=(fname, False, 30, error_queue))
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


def test_max_lock_time_nested_crashes():
    fname = "test_max_lock_time_nested_crashes.json"
    init_file(fname)
    ProtectFile._testing_nested = True
    _run_nested_lockfiles(fname, 6)
    ProtectFile._testing_nested = False
    Path(fname).unlink()


def test_max_lock_time_nested_crashes_overflow():
    fname = "test_max_lock_time_nested_crashes_overflow.json"
    init_file(fname)
    ProtectFile._testing_nested = True
    with pytest.raises(RuntimeError, match="Too many lockfiles!"):
        _run_nested_lockfiles(fname, 7)
    ProtectFile._testing_nested = False
    Path(fname).unlink()


def _run_nested_lockfiles(fname, n_concurrent):
    error_queue = Queue()
    procs = [
        Process(target=change_file_protected, args=(fname, False, 2, error_queue))
        for _ in range(n_concurrent)
    ]

    # Start the first process and kill it before finishing
    procs[0].start()
    time.sleep(0.05)
    kill_process(procs[0], error_queue)

    # Check there is a leftover lockfile
    nested_path = f"{fname}.lock"
    assert Path(nested_path).exists()

    print("First process started and killed")

    # We start and kill all next processes consecutively, except the last.
    # This should generate nested lockfiles
    for i, proc in enumerate(procs[1:-1]):
        proc.start()
        print(f"Process {i + 2} started")

        # Give it time to pass the wait and try to read the lock
        time.sleep(0.15*(i + 1))  # Cascaded waiting time for each nested lock

        # Now kill it
        kill_process(proc, error_queue)

        # Check there is a leftover nested lockfile
        nested_path = f"{nested_path}.lock"
        assert Path(nested_path).exists()

        # Wait ~0.3s for the deepest lock to be allowed to be freed
        time.sleep(0.4)

    # Start the final process
    procs[-1].start()
    procs[-1].join()

    propagate_child_errors(error_queue)

    # Verify result
    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == 1      # Only the last job succeeded

