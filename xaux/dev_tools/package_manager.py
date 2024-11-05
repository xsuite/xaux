# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
import sys
import importlib
from contextlib import contextmanager
from subprocess import run
from shutil import rmtree

from ..general import _pkg_root


_PACKAGE_PATH = _pkg_root / "lib" / "_xaux_pkg_vers"


@contextmanager
def import_package_version(package_name, version, wipe_cache=False):
    """
    Context manager to temporarily import a specific version of a package.
    """
    package_path = _PACKAGE_PATH / package_name / version
    if not package_path.exists():
        install_package_version(package_name, version)

    original_sys_path = sys.path.copy()
    original_sys_modules = sys.modules.copy()
    sys.path.insert(0, package_path)
    for mod_name in list(sys.modules):
        if mod_name == package_name or mod_name.startswith(package_name + '.'):
            del sys.modules[mod_name]
    print(list(sys.modules.keys()))
    print(sys.path)
    try:
        if wipe_cache:
            importlib.invalidate_caches()
        module = importlib.import_module(package_name)
        yield module
    finally:
        sys.path = original_sys_path
        sys.modules = original_sys_modules


def install_package_version(package_name, version, overwrite=False):
    """
    Installs a specific version of a package.
    """
    full_package_name = f"{package_name}=={version}"
    package_path = _PACKAGE_PATH / package_name / version
    if package_path.exists() and not overwrite:
        print(f"Package already installed in {package_path}. "
             + "Use `overwrite=True` if this is the intended goal.")
    else:
        if package_path.exists():
            rmtree(package_path)
        package_path.mkdir(parents=True)
        try:
            print(f"Installing package {full_package_name}")
            cmd = run([sys.executable, "-m", "pip", "install", full_package_name,
                    f"--target={package_path}"], capture_output=True)
            if cmd.returncode != 0:
                print(f"Installation failed for {full_package_name}:\n{cmd.stderr.decode()}")
        except Exception as e:
            print(f"An error occurred: {e}\nCommand output:{cmd.stderr.decode()}")
