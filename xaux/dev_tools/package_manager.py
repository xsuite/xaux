# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import os
import sys
import json
import importlib
import urllib.request
from shutil import rmtree
from subprocess import run
from contextlib import contextmanager
from packaging.version import Version

from ..general import _pkg_root


_PACKAGE_PATH = _pkg_root / "lib" / "_xaux_pkg_vers"

xsuite_pkgs = ['xaux', 'xobjects', 'xdeps', 'xtrack', 'xpart', 'xfields', 'xcoll', 'xdyna', 'xboinc']


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
    original_sys_meta_path = sys.meta_path.copy()
    pkgs = _get_available_packages_in_path(package_path)
    for pkg in pkgs:
        _remove_import_from_sys(pkg)
    for finder_name in sys.meta_path:
        if package_name in str(finder_name):
            sys.meta_path.remove(finder_name)
    if wipe_cache:
        importlib.invalidate_caches()
        for finder_name in sys.meta_path:
            if 'editable' in str(finder_name):
                sys.meta_path.remove(finder_name)
    sys.path.insert(0, package_path.as_posix())
    try:
        module = importlib.import_module(package_name)
        yield module
    finally:
        sys.path = original_sys_path
        sys.modules = original_sys_modules
        sys.meta_path = original_sys_meta_path


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


def get_package_versions(package_name):
    """
    Get all available versions of a package from PyPI, sorted by newest last.
    """
    data = json.loads(urllib.request.urlopen(f"https://pypi.org/pypi/{package_name}/json").read())
    return sorted(list(data['releases'].keys()), key=Version)


def get_latest_package_version(package_name):
    """
    Get the latest version of a package from PyPI.
    """
    data = json.loads(urllib.request.urlopen(f"https://pypi.org/pypi/{package_name}/json").read())
    return data['info']['version']


def get_package_dependencies(package_name):
    """
    Get the dependencies of a package from PyPI.
    """
    data = json.loads(urllib.request.urlopen(f"https://pypi.org/pypi/{package_name}/json").read())
    return data['info']['requires_dist']


def get_package_version_dependencies(package_name, version, skip=[]):
    """
    Get the package versions of the dependencies for a specific version of `package_name`.
    TODO: This function is not working as intended when `numpy` is a dependency and already imported.
    """
    if not hasattr(skip, '__iter__') or isinstance(skip, str):
        skip = [skip]
    deps = {}
    with import_package_version(package_name, version, wipe_cache=True):
        package_path = _PACKAGE_PATH / package_name / version
        pkgs = _get_available_packages_in_path(package_path)
        pkgs = [pkg for pkg in pkgs if pkg not in skip]
        # for pkg in pkgs:
        #     _remove_import_from_sys(pkg)
        for pkg in pkgs:
            if pkg in ['numpy', 'numba', 'scipy']:
                # These are being difficult
                deps[pkg] = None
            else:
                # mod = _import_package_from_path(pkg, package_path)
                mod = importlib.import_module(pkg)
                assert mod.__file__.startswith(package_path.as_posix())
                deps[pkg] = mod.__version__ if hasattr(mod, '__version__') else None
    return deps


def _get_available_packages_in_path(path):
    return [pkg.name for pkg in path.glob('*') if (path / pkg).is_dir() \
            and not pkg.name.startswith('_') and not '.' in pkg.name \
            and not pkg.name.endswith('dist-info') and not pkg.name == 'bin']


def _remove_import_from_sys(package_name):
    for mod_name in list(sys.modules):
        if package_name == mod_name or mod_name.startswith(package_name + '.'):
            del sys.modules[mod_name]

def _import_package_from_path(package_name, package_path):
    original_sys_path = sys.path.copy()
    original_sys_meta_path = sys.meta_path.copy()
    for finder_name in sys.meta_path:
        if package_name in str(finder_name):
            sys.meta_path.remove(finder_name)
    sys.path.insert(0, package_path.as_posix())
    module = importlib.import_module(package_name)
    sys.path = original_sys_path
    sys.meta_path = original_sys_meta_path
    return module
