# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from multiprocessing import Pool
import pytest
import json
from xaux import FsPath

from _test_helpers import init_file, change_file_protected, change_file_standard


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

