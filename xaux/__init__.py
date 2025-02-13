# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from .general import _pkg_root, __version__
from .fs import FsPath, LocalPath, EosPath, AfsPath, afs_accessible, eos_accessible, is_egroup_member, cp, mv
from .dev_tools import import_package_version  # Stub to get dev_tools in the namespace
from .tools import singleton, ClassProperty, ClassPropertyMeta, timestamp, ranID, system_lock, get_hash, \
                   ProtectFile, ProtectFileError
