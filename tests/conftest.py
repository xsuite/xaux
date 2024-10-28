import pytest
from pathlib import Path
import getpass
import warnings

from xaux.fs import afs_accessible, eos_accessible


def pytest_addoption(parser):
    parser.addoption(
        "--user", action="store", default="sixtadm", help="Specify the user that has access to EOS and AFS."
    )


@pytest.fixture(scope="session")
def test_user(request):
    test_user = request.config.getoption("--user")
    afs_path  = f"/afs/cern.ch/user/{test_user[0]}/{test_user}/public/test_xboinc/"
    eos_path  = f"/eos/user/{test_user[0]}/{test_user}/test_xboinc/"
    skip_afs = True
    if afs_accessible:
        afs_paths_tried = [afs_path]
        if Path(afs_path).is_dir():
            skip_afs = False
        else:
            test_user = getpass.getuser()
            afs_path  = f"/afs/cern.ch/user/{test_user[0]}/{test_user}/public/test_xboinc/"
            if Path(afs_path).is_dir():
                skip_afs = False
            else:
                afs_paths_tried.append(afs_path)
                warnings.warn("AFS test directory not accessible.\nPlease ensure the directory exists and verify "
                            + "your access rights (is your ticket still alive?).\nAlternatively, specify the test "
                            + "user account with the option `--user username`\nI Tried the following paths:\n    "
                            + "\n    ".join(afs_paths_tried) + "\nThe relevant AfsPath tests will be skipped.")
    skip_eos = True
    if eos_accessible:
        eos_paths_tried = [eos_path]
        if Path(eos_path).is_dir():
            skip_eos = False
        else:
            # Do not overwrite test_user (as it will be used by the AFS ACL test)
            eos_path  = f"/eos/user/{getpass.getuser()[0]}/{getpass.getuser()}/test_xboinc/"
            if Path(eos_path).is_dir():
                skip_eos = False
            else:
                eos_paths_tried.append(eos_path)
                warnings.warn("EOS test directory not accessible.\nPlease ensure the directory exists and verify "
                            + "your access rights (is your ticket still alive?).\nAlternatively, specify the test "
                            + "user account with the option `--user username`\nI Tried the following paths:\n    "
                            + "\n    ".join(eos_paths_tried) + "\nThe relevant EosPath tests will be skipped.")
    return {"test_user": test_user, "afs_path":  afs_path, "skip_afs": skip_afs, "eos_path":  eos_path, "skip_eos": skip_eos}
