# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from .fs import FsPath, LocalPath, LocalPosixPath, LocalWindowsPath
from .eos import EosPath, EosPosixPath, EosWindowsPath, eos_accessible
from .afs import AfsPath, AfsPosixPath, AfsWindowsPath, afs_accessible
