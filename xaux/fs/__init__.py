# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from .fs import FsPath, LocalPath, LocalPosixPath, LocalWindowsPath
from .afs import AfsPath, AfsPosixPath, AfsWindowsPath, afs_accessible
from .eos import EosPath, EosPosixPath, EosWindowsPath
from .eos_methods import eos_accessible, is_egroup_member
from .fs_methods import *
from .io import cp, mv


EOS_CELL = 'cern.ch'
default_eos_instance = 'public'


# For testing
_skip_eos = False
_force_eos = False
_force_xrdcp = False
