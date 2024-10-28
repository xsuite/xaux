# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os, sys
from ..fs import FsPath
import atexit
import base64
import datetime


def timestamp(ms=False, in_filename=True):
    ms = -3 if ms else -7
    if in_filename:
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:ms]
    else:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:ms]

def ranID():
    ran = base64.urlsafe_b64encode(os.urandom(8)).decode('utf-8')
    return ''.join(c if c.isalnum() else 'X' for c in ran)


def lock(lockfile):
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
