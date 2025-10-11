# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from .general import _pkg_root, __version__
from .fs import FsPath, LocalPath, EosPath, AfsPath, afs_accessible, eos_accessible, is_egroup_member, cp, mv
from .dev_tools import import_package_version  # Stub to get dev_tools in the namespace
from .tools import singleton, ClassProperty, ClassPropertyMeta, timestamp, ranID, system_lock, get_hash, \
                   ProtectFile, ProtectFileError

_tempdir_cache = None
def __getattr__(name):
    global _tempdir_cache
    if name == "tempdir":
        if not _tempdir_cache:
            from .fs.temp import _tempdir
            _tempdir_cache = _tempdir
        return FsPath(_tempdir_cache)
    raise AttributeError(f"module {__name__} has no attribute {name}")
