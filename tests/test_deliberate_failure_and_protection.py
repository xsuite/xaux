# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from multiprocessing import Pool
import pytest
import json
from pathlib import Path

from _test_helpers import init_file, change_file_protected, change_file_standard


def test_deliberate_failure():
    fname = "test_standard.json"
    init_file(fname)

    workers = 4
    with Pool(processes=workers) as pool:
        pool.map(change_file_standard, [fname] * 4)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] != workers  # assert that result is wrong

    Path(fname).unlink()


@pytest.mark.parametrize("workers", [4, 100])
@pytest.mark.parametrize("with_copy", [False, True])
def test_protection(workers, with_copy):
    fname = "test_protection.json"
    init_file(fname)

    with Pool(processes=workers) as pool:
        pool.map(change_file_protected, [(fname)] * workers)

    with open(fname, "r+") as pf:
        data = json.load(pf)
        assert data["myint"] == workers

    Path(fname).unlink()

