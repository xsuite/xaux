import json
from pathlib import Path
from xaux.test_helpers import init_file, change_file_protected
from multiprocessing import Process

def test_max_lock_time():
    fname = "test_standard.json"
    assert not Path(fname).exists()
    init_file(fname)

    procA = Process(target=change_file_protected, args=(fname, False, 1))
    procB = Process(target=change_file_protected, args=(fname, False, 1))

    procA.start()
    procB.start()

    procA.join()
    procB.join()

    with open(fname, "r+") as pf:  # fails with this context
        Path(fname).unlink()
        data = json.load(pf)
        assert data["myint"] == 2
