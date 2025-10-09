# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

from subprocess import run, TimeoutExpired
from math import ceil
from xaux import timestamp, ranID, get_hash, FsPath


def test_timestamp():
    ts = timestamp()
    ts_f = timestamp(in_filename=True)
    ts_ms = timestamp(ms=True)
    ts_us = timestamp(us=True)
    ts_ms_f = timestamp(ms=True, in_filename=True)

    if ts.startswith('21'):
        raise RuntimeError("You really should not be using this code anymore...")

    assert len(ts) == 19
    assert len(ts_f) == 19
    assert len(ts_ms) == 23
    assert len(ts_us) == 26
    assert len(ts_ms_f) == 23

    assert len(ts.split()) == 2
    assert len(ts.split()[0]) == 10
    assert len(ts.split()[1]) == 8
    assert len(ts.split()[0].split('-')) == 3
    assert len(ts.split()[0].split('-')[0]) == 4
    assert len(ts.split()[0].split('-')[1]) == 2
    assert len(ts.split()[0].split('-')[2]) == 2
    assert len(ts.split()[1].split(':')) == 3
    assert len(ts.split()[1].split(':')[0]) == 2
    assert len(ts.split()[1].split(':')[1]) == 2
    assert len(ts.split()[1].split(':')[2]) == 2
    assert len(ts_f.split('_')) == 2
    assert len(ts_f.split('_')[0]) == 10
    assert len(ts_f.split('_')[1]) == 8
    assert len(ts_f.split('_')[0].split('-')) == 3
    assert len(ts_f.split('_')[0].split('-')[0]) == 4
    assert len(ts_f.split('_')[0].split('-')[1]) == 2
    assert len(ts_f.split('_')[0].split('-')[2]) == 2
    assert len(ts_f.split('_')[1].split('-')) == 3
    assert len(ts_f.split('_')[1].split('-')[0]) == 2
    assert len(ts_f.split('_')[1].split('-')[1]) == 2
    assert len(ts_f.split('_')[1].split('-')[2]) == 2
    assert len(ts_ms.split()) == 2
    assert len(ts_ms.split()[0]) == 10
    assert len(ts_ms.split()[1]) == 12
    assert len(ts_ms.split()[0].split('-')) == 3
    assert len(ts_ms.split()[0].split('-')[0]) == 4
    assert len(ts_ms.split()[0].split('-')[1]) == 2
    assert len(ts_ms.split()[0].split('-')[2]) == 2
    assert len(ts_ms.split()[1].split(':')) == 3
    assert len(ts_ms.split()[1].split(':')[0]) == 2
    assert len(ts_ms.split()[1].split(':')[1]) == 2
    assert len(ts_ms.split()[1].split(':')[2]) == 6
    assert len(ts_ms.split()[1].split(':')[2].split('.')) == 2
    assert len(ts_ms.split()[1].split(':')[2].split('.')[0]) == 2
    assert len(ts_ms.split()[1].split(':')[2].split('.')[1]) == 3
    assert len(ts_us.split()) == 2
    assert len(ts_us.split()[0]) == 10
    assert len(ts_us.split()[1]) == 15
    assert len(ts_us.split()[0].split('-')) == 3
    assert len(ts_us.split()[0].split('-')[0]) == 4
    assert len(ts_us.split()[0].split('-')[1]) == 2
    assert len(ts_us.split()[0].split('-')[2]) == 2
    assert len(ts_us.split()[1].split(':')) == 3
    assert len(ts_us.split()[1].split(':')[0]) == 2
    assert len(ts_us.split()[1].split(':')[1]) == 2
    assert len(ts_us.split()[1].split(':')[2]) == 9
    assert len(ts_us.split()[1].split(':')[2].split('.')) == 2
    assert len(ts_us.split()[1].split(':')[2].split('.')[0]) == 2
    assert len(ts_us.split()[1].split(':')[2].split('.')[1]) == 6
    assert len(ts_ms_f.split('_')) == 2
    assert len(ts_ms_f.split('_')[0]) == 10
    assert len(ts_ms_f.split('_')[1]) == 12
    assert len(ts_ms_f.split('_')[0].split('-')) == 3
    assert len(ts_ms_f.split('_')[0].split('-')[0]) == 4
    assert len(ts_ms_f.split('_')[0].split('-')[1]) == 2
    assert len(ts_ms_f.split('_')[0].split('-')[2]) == 2
    assert len(ts_ms_f.split('_')[1].split('-')) == 3
    assert len(ts_ms_f.split('_')[1].split('-')[0]) == 2
    assert len(ts_ms_f.split('_')[1].split('-')[1]) == 2
    assert len(ts_ms_f.split('_')[1].split('-')[2]) == 6
    assert len(ts_ms_f.split('_')[1].split('-')[2].split('.')) == 2
    assert len(ts_ms_f.split('_')[1].split('-')[2].split('.')[0]) == 2
    assert len(ts_ms_f.split('_')[1].split('-')[2].split('.')[1]) == 3


def test_ranID():
    rans = [ranID(length=l+1) for l in range(40)]
    print(rans)
    for i, ran in enumerate(rans):
        assert len(ran) == int(ceil((i+1)/4)*4)

    rans = [ranID(length=20) for _ in range(1000)]
    for ran in rans:
        base64_safe = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        assert all([c in base64_safe for c in ran])

    rans = [ranID(length=20, only_alphanumeric=True) for _ in range(1000)]
    for ran in rans:
        alnum = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        assert all([c in alnum for c in ran])

    rans = ranID(length=20, size=1000)
    for ran in rans:
        base64_safe = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        assert all([c in base64_safe for c in ran])

    rans = ranID(length=20, size=1000, only_alphanumeric=True)
    for ran in rans:
        alnum = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        assert all([c in alnum for c in ran])


def test_system_lock():
    datafile = FsPath.cwd() / 'test_cronjob.txt'
    lockfile = FsPath.cwd() / 'test_cronjob.lock'
    if datafile.exists():
        datafile.unlink()
    if lockfile.exists():
        lockfile.unlink()

    # Normal run
    cmd1 = run(['python', 'cronjob_example.py'], capture_output=True, text=True)
    assert cmd1.returncode == 0
    assert "Cronjob running." in cmd1.stdout
    assert "Cronjob finished." in cmd1.stdout
    assert not lockfile.exists()
    assert not datafile.exists()

    # Run and kill halfway
    try:
        cmd2 = run(['python', 'cronjob_example.py'], timeout=2, capture_output=True, text=True)
    except TimeoutExpired:
        assert lockfile.exists()
        assert datafile.exists()
        datafile.unlink()

    # Run while lockfile exists
    cmd3 = run(['python', 'cronjob_example.py'], capture_output=True, text=True)
    assert cmd3.returncode == 1
    assert "Cronjob running." not in cmd3.stdout
    assert "Cronjob finished." not in cmd3.stdout
    assert "Previous test_cronjob.lock script still active!" in cmd3.stderr
    assert not datafile.exists()
    lockfile.unlink()


def test_hash():
    hs = get_hash('cronjob_example.py')
    assert hs == '3eeb344d1236d3d0e2400744c732aded84528a4491600b5533052ced14b03fc5249668' \
               + '3d2f5e71ac18f4ddf14673a4b53fb06c01c95f1a1d0ea11a485439a17b'
