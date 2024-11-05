# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import json
import urllib
from packaging.version import Version


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

