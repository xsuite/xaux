# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from .fs import FsPath, LocalPath, LocalPosixPath, LocalWindowsPath
from .afs import AfsPath, AfsPosixPath, AfsWindowsPath, afs_accessible
from .eos import EosPath, EosPosixPath, EosWindowsPath
from .eos_methods import eos_accessible, is_egroup_member
from .fs_methods import make_stat_result, size_expand
from .io import cp, mv

_xrdcp_use_ipv4 = True

# For testing
_skip_afs_software = False
_skip_eos_software = False
_force_xrdcp = False
_force_eoscmd = False
