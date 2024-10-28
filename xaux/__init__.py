# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import sys
if sys.version_info[1] >= 12:
    raise Exception("Must be using Python 3.8 - 3.11")

from .general import _pkg_root, __version__
from .protectfile import ProtectFile, ProtectFileError, get_hash
from .fs import FsPath, LocalPath, EosPath, AfsPath, afs_accessible, eos_accessible, is_egroup_member, cp, mv
