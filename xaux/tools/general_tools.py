# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import os
import sys
import atexit
import base64
import hashlib
import pandas as pd
import numpy as np

from ..fs import FsPath


def timestamp(*, in_filename=False, ms=False, us=False):
    """Timestamp for easy use in logs and filenames.
    Args:
        ms (bool): If True, milliseconds are included.
            Default False.
        in_filename (bool): If True, colons are replaced
            with dashes to be used in filenames. Default False.
    Returns:
        str: Current timestamp in UTC.
    """
    if ms and us:
        raise ValueError("Only one of 'ms' or 'us' can be True!")
    idx = -3 if ms else -7
    idx = 26 if us else idx
    form = "%Y-%m-%d_%H-%M-%S.%f" if in_filename else "%Y-%m-%d %H:%M:%S.%f"
    return pd.Timestamp.now(tz='UTC').to_pydatetime().strftime(form)[:idx]


def ranID(*, length=12, size=1, only_alphanumeric=False):
    """Base64 encoded random ID.
    Args:
        length (int): Length of the ID string, rounded up to
            the closest multiple of 4. Default 12.
        size (int): Number of random IDs to generate.
            Default 1.
        only_alphanumeric (bool): If True, only alphanumeric
            characters are used. Default False.
    Returns:
        str: Random ID string.
    """
    if length < 1:
        raise ValueError("Length must be greater than 0!")
    if size < 1:
        raise ValueError("Size must be greater than 0!")
    if size > 1:
        return [ranID(length=length, only_alphanumeric=only_alphanumeric)
                for _ in range(size)]
    length = int(np.ceil(length/4))
    if only_alphanumeric:
        ran = ''
        for _ in range(length):
            while True:
                this_ran = ranID(length=4, only_alphanumeric=False)
                if this_ran.isalnum():
                    break
            ran += this_ran
        return ran
    else:
        random_bytes = os.urandom(3*length)
        return base64.urlsafe_b64encode(random_bytes).decode('utf-8')


def system_lock(lockfile):
    """Create a lockfile or quit the process if it already exists.
    This is useful for cronjobs that might overlap in time if they
    run for too long.
    Args:
        lockfile (str): Path to the lockfile.
    """
    lockfile = FsPath(lockfile)
    # Check if previous process still running
    if lockfile.exists():
        sys.exit(f"Previous {lockfile.name} script still active! Exiting...")
    else:
        # Otherwise register a lockfile
        lockfile.touch()
        def exit_handler():
            lockfile.unlink()
        atexit.register(exit_handler)


def get_hash(filename, *, size=128):
    """Get a fast hash of a file, in chunks of 'size' (in kb)"""
    h  = hashlib.blake2b()
    b  = bytearray(size*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()
