import json
from pathlib import Path
from xaux.test_helpers import init_file, change_file_protected
from multiprocessing import Process
import os
import time
import signal

def test_max_lock_time():
    fname = "test_max_lock_time.json"
    assert not Path(fname).exists()
    init_file(fname)

    procA = Process(target=change_file_protected, args=(fname, False, 1))
    procB = Process(target=change_file_protected, args=(fname, False, 1))

    procA.start()
    procB.start()

    procA.join()
    procB.join()

    with open(fname, "r+") as pf:
        Path(fname).unlink()
        data = json.load(pf)
        assert data["myint"] == 2

def test_max_lock_time_crashed():
    fname = "test_max_lock_time.json"
    assert not Path(fname).exists()
    init_file(fname)

    procA = Process(target=change_file_protected, args=(fname, False, 5))
    procB = Process(target=change_file_protected, args=(fname, False, 5))

    procA.start()
    procB.start()
    start = time.time()
    time.sleep(0.1)
    os.kill(procA.pid, signal.SIGKILL)
    procA.join()

    time.sleep(6.1)
    with open(fname, "r") as pf:
        data = json.load(pf)
        assert data["myint"] == 0

    assert Path(fname+'.lock').exists()
    procB.join()

    stop = time.time()
    elapsed_time = stop - start
    assert elapsed_time < 6.5

    with open(fname, "r+") as pf:
        Path(fname).unlink()
        data = json.load(pf)
        assert data["myint"] == 1
