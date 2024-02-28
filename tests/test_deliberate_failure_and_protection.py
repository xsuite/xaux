from multiprocessing import Pool
import pytest
from xaux import ProtectFile
import json
from pathlib import Path
import time
import shutil


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
        Path.unlink(Path(cfname))


def change_file_protected(fname, with_copy=False):
    with ProtectFile(fname, "r+", backup=False, wait=0.06) as pf:
        rewrite(pf, with_copy=with_copy)
    return


def change_file_standard(fname, with_copy=False):
    with open(fname, "r+") as pf:  # fails with this context
        rewrite(pf)
    return


def init_file(fname):
    with ProtectFile(fname, "w", backup=False, wait=1) as pf:
        json.dump({"myint": 0}, pf, indent=4)


def test_deliberate_failure():
    fname = "test_standard.json"
    assert not Path(fname).exists()
    init_file(fname)
    workers = 4
    with Pool(processes=workers) as pool:
        pool.map(change_file_standard, [fname] * 4)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] != workers  # assert that result is wrong
    Path.unlink(Path(fname))


@pytest.mark.parametrize("with_copy", [False, True])
def test_protection(with_copy):
    fname = "test_protection.json"
    assert not Path(fname).exists()
    init_file(fname)
    workers = 4
    with Pool(processes=workers) as pool:
        pool.map(change_file_protected, [(fname)] * 4)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == workers
    Path.unlink(Path(fname))
