# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import numpy as np
import xaux as xa


def test_timestamp():
    ts = xa.timestamp()
    ts_f = xa.timestamp(in_filename=True)
    ts_ms = xa.timestamp(ms=True)
    ts_ms = xa.timestamp(us=True)
    ts_ms_f = xa.timestamp(ms=True, in_filename=True)

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
    rans = [xa.ranID(length=l+1) for l in range(40)]
    print(rans)
    for i, ran in enumerate(rans):
        assert len(ran) == int(np.ceil((i+1)/4)*4)

    rans = [xa.ranID(length=20) for _ in range(1000)]
    for ran in rans:
        base64_safe = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        assert np.all([c in base64_safe for c in ran])

    rans = [xa.ranID(length=20, only_alphanumeric=True) for _ in range(1000)]
    for ran in rans:
        alnum = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        assert np.all([c in alnum for c in ran])

    rans = xa.ranID(length=20, size=1000)
    for ran in rans:
        base64_safe = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        assert np.all([c in base64_safe for c in ran])

    rans = xa.ranID(length=20, size=1000, only_alphanumeric=True)
    for ran in rans:
        alnum = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        assert np.all([c in alnum for c in ran])


def test_system_lock():
    pass
