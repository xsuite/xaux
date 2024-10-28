# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
from math import prod
from subprocess import run, PIPE, CalledProcessError


_xrdcp_installed = False
if os.name != 'nt':
    try:
        cmd = run(["xrdcp", "--version"], stdout=PIPE, stderr=PIPE)
        _xrdcp_installed = cmd.returncode == 0
    except (CalledProcessError, FileNotFoundError):
        _xrdcp_installed = False


# The class os.stat_result can only be initialised with a Tuple,
# however, the contents of this Tuple can change between python versions.
# This is a rather contrived way of finding the Tuple indices that correspond
# to certain fields.
_stat_n_fields = os.stat_result.n_fields
_stat_idx = {k: [] for k in os.stat_result.__dict__ if k.startswith('st_')}
for i in range(os.stat_result.n_sequence_fields, _stat_n_fields):
    _stat_def = os.stat_result(tuple(range(i)))
    for k in _stat_def.__dir__():
        if k.startswith('st_'):
            val = getattr(_stat_def, k, None)
            if val is not None and val not in _stat_idx[k]:
                _stat_idx[k] += [val]
# Sanity check; if this fails, that certain indices are used for different fields
assert len(sum(_stat_idx.values(), [])) == len(set(sum(_stat_idx.values(), [])))

# Make a stat_result from the fields directly
def make_stat_result(stat_dict):
    stats = [None for _ in range(_stat_n_fields)]
    for key, val in stat_dict.items():
        if key in _stat_idx:
            for st in _stat_idx[key]:
                stats[st] = int(val)
    return os.stat_result(tuple(stats))


def size_expand(size, binary=False):
    size = str(size).lower()
    size = size.replace('b', '')
    if binary:
        size = size.replace('k','*1024')
        size = size.replace('m', '*1048576')
        size = size.replace('g', '*1073741824')
        size = size.replace('t', '*1099511627776')
    else:
        size = size.replace('k','*1000')
        size = size.replace('m', '*1000000')
        size = size.replace('g', '*1000000000')
        size = size.replace('t', '*1000000000000')
    return int(prod([int(i) for i in size.split('*')]))

