import json
from pathlib import Path
from _test_helpers import init_file, change_file_protected
from multiprocessing import Process
import os
import time
import signal


fname = "test_max_lock_time.json"


def test_max_lock_time():
    init_file(fname)

    procA = Process(target=change_file_protected, args=(fname, False, 1))
    procB = Process(target=change_file_protected, args=(fname, False, 1))

    procA.start() # Will take > 0.2s
    time.sleep(0.18)
    assert Path(fname+'.lock').exists()

    # B will try to access the file while A is still running, and will try
    # again 0.1s later by which time A has finished (and the lock will have
    # disappeared).
    procB.start()

    procA.join()
    procB.join()

    with open(fname, "r+") as pf:
        Path(fname).unlink()
        data = json.load(pf)
        assert data["myint"] == 2


def test_max_lock_time_crashed():
    init_file(fname)

    procA = Process(target=change_file_protected, args=(fname, False, 5))
    procB = Process(target=change_file_protected, args=(fname, False, 5))

    procA.start()
    procB.start()
    start = time.time()

    # We kill process A after 0.1s such that we have a hanging lockfile
    time.sleep(0.1)
    os.kill(procA.pid, signal.SIGKILL)
    procA.join()
    assert Path(fname+'.lock').exists()

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

    with open(fname, "r+") as pf:
        Path(fname).unlink()
        data = json.load(pf)
        assert data["myint"] == 1
