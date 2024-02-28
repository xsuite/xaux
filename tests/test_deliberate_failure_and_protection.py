from multiprocessing import Pool
import pytest
import json
from pathlib import Path
from xaux.test_helpers import init_file, change_file_protected, change_file_standard

def test_deliberate_failure():
    fname = "test_standard.json"
    assert not Path(fname).exists()
    init_file(fname)
    workers = 4
    with Pool(processes=workers) as pool:
        pool.map(change_file_standard, [fname] * 4)

    with open(fname, "r+") as pf:
        Path.unlink(Path(fname))
        data = json.load(pf)
        assert data["myint"] != workers  # assert that result is wrong


@pytest.mark.parametrize("with_copy", [False, True])
def test_protection(with_copy):
    fname = "test_protection.json"
    assert not Path(fname).exists()
    init_file(fname)
    workers = 4
    with Pool(processes=workers) as pool:
        pool.map(change_file_protected, [(fname)] * 4)

    with open(fname, "r+") as pf:
        Path.unlink(Path(fname))
        data = json.load(pf)
        assert data["myint"] == workers
