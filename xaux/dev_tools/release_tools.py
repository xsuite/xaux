# copyright ############################### #
# This file is part of the Xaux package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import sys
from .gh import *
from .package_manager import get_latest_package_version


class VersionError(OSError):
    pass


def make_release_branch(package, bump=None, allow_major=False):
    if bump is None:
        bump, _ = _parse_argv(optional_force=False)

    # Check necessary setup and installs
    assert_git_repo()
    assert_git_repo_name(package)
    _assert_in_root_package_dir(package)
    assert_poetry_installed()

    # Check our working directory is clean
    git_assert_working_tree_clean()
    branch = git_current_branch()
    if branch != "main":
        raise GitError("This script needs to be ran on the main branch.")
    git_pull()   # Sync with the remote to be sure we don't delete an incomplete branch later
    git_push()
    print("Repository is clean.")

    expected_ver = poetry_get_expected_version(bump)
    _assert_not_major_version(expected_ver, 'make_release_branch.py', allow_major)

    branch = f"release/v{expected_ver}"
    expected_ver = f"{expected_ver}rc0"
    _confirm_version_bump(expected_ver)

    print("Creating release branch...")
    git_switch(branch, create=True)
    print("Poetry version bump...")
    new_ver = _do_bump(expected_ver)

    _adapt_version_files(package, new_ver)
    git_add(["pyproject.toml", f"{package}/general.py", "tests/test_version.py"])
    git_commit(f"Created release branch release/v{new_ver}.", no_verify=True)
    git_push(set_upstream=True)

    print("All done!")


def rename_release_branch(package, bump=None, allow_major=False):
    if bump is None:
        bump, _ = _parse_argv(optional_force=False)

    # Check necessary setup and installs
    assert_git_repo()
    assert_git_repo_name(package)
    _assert_in_root_package_dir(package)
    assert_poetry_installed()

    # Check our working directory is clean
    git_assert_working_tree_clean()
    branch = git_current_branch()
    current_ver = poetry_get_version()
    if branch != f"release/v{current_ver[:-3]}":
        raise GitError("This script needs to be ran from a release branch.")
    git_pull()   # Sync with the remote to be sure we don't delete an incomplete branch later
    git_push()
    _assert_no_open_prs(branch)
    print("Repository is clean.")

    expected_ver = poetry_get_expected_version(bump)
    _assert_not_major_version(expected_ver, 'rename_release_branch.py', allow_major)

    new_branch = f"release/v{expected_ver}"
    expected_ver = f"{expected_ver}rc0"
    _confirm_version_bump(expected_ver)

    print("Renaming release branch...")
    git_rename_current_branch(new_branch, set_upstream=True)
    print("Poetry version bump...")
    new_ver = _do_bump(expected_ver)

    _adapt_version_files(package, new_ver)
    git_add(["pyproject.toml", f"{package}/general.py", "tests/test_version.py"])
    git_commit(f"Renamed release branch {branch} into {new_branch}.", no_verify=True)
    git_push(set_upstream=True)

    print("All done!")


def make_release(package, bump=None, force=False, allow_major=False):
    if bump is None:
        bump, force = _parse_argv(optional_force=True)

    # Check necessary setup and installs
    assert_git_repo()
    assert_git_repo_name(package)
    _assert_in_root_package_dir(package)
    assert_poetry_installed()
    assert_gh_installed()

    # Check our working directory is clean
    print("Verifying repository status...")
    git_assert_working_tree_clean()
    branch = git_current_branch()
    if branch == "main":
        raise GitError("\nThis script cannot be ran on the main branch."
                        "Make a release branch and make the new release from there."
                        "Make sure that the release branch has an upstream version (i.e."
                        "push at least once before running this script), or this script"
                        "will fail.")
    expected_ver = poetry_get_expected_version(bump)
    if not force:
        if branch != f"release/v{expected_ver}":
            raise VersionError(f"\nYou are bumping to {expected_ver} but this branch is {branch}. "
                                    "If this is intentional, use --force.")
    git_pull()   # Sync with the remote to be sure we don't delete an incomplete branch later
    git_push()
    _assert_no_open_prs(branch)
    print("Repository is clean.")

    _assert_not_major_version(expected_ver, 'release.py', allow_major)
    _confirm_version_bump(expected_ver)
    print("Updating version in the release branch...")
    new_ver = _do_bump(expected_ver, bump)

    _adapt_version_files(package, new_ver)
    _set_dependencies(package)
    git_add(["pyproject.toml", f"{package}/general.py", "tests/test_version.py"])
    git_commit(f"Updated version number to v{new_ver}.", no_verify=True)
    git_push()

    print("Creating and merging pull request to main branch...")
    gh_pr_create('main', f"Release {new_ver}")
    git_switch('main')
    git_pull()
    prs = gh_pr_list(base='main', head=branch)
    if len(prs) != 1:
        raise GitError(f"Expected one PR from {branch} to main, found {len(prs)}:\n"
                    + "\n".join([f"PR#{pr} from {br}" for pr, br in prs.items()]))
    gh_pr_merge(list(prs.keys())[0], admin=True, delete_branch=True)
    git_pull()
    git_make_tag(f"v{new_ver}")

    print("Creating draft release and publishing to PyPi...")
    gh_release_create(f"v{new_ver}", f"{package.capitalize()} release {new_ver}", draft=True)
    poetry_publish(build=True)

    print("All done!")


def _parse_argv(optional_force=False):
    # Check the script arguments
    num_max_args = 3 if optional_force else 2
    if len(sys.argv) < 2 or len(sys.argv) > num_max_args:
        raise ValueError("Are you running CLI?\nThen this script needs exactly one argument: "
                       + "the new version number or a bump (which can be: patch, minor, major).\n"
                       + "If running in python, please provide the argument `bump=...`.")
    bump = sys.argv[1]
    force = False
    if optional_force and len(sys.argv) == num_max_args:
        force = True
        if sys.argv[1] == "--force":
            bump = sys.argv[2]
        elif sys.argv[2] != "--force":
            raise ValueError("Only '--force' is allowed as an option.")
    return bump, force


def _assert_in_root_package_dir(package):
    if package in [pp.name for pp in Path.cwd().parents]:
        raise VersionError("This script needs to be ran from the root package directory.")


def _assert_not_major_version(expected_ver, file, allow_major):
    # Check that we are not accidentally bumping a major version
    if not allow_major:
        major_ver = int(expected_ver.split('.')[0])
        if major_ver != 0:
            raise VersionError("Bumping a major version! If this is really what you want, "
                            + f"then adapt {file} manually to add `allow_major=True`.")


def _assert_no_open_prs(branch):
    # Check that there are no conflicting PRs open
    prs = gh_pr_list(base=branch)
    if prs:
        raise GitError(f"There are open PRs to the release branch:\n" \
                    + "\n".join([f"PR#{pr} from {br}" for pr, br in prs.items()]) \
                    + "\nThese would be automatically closed by this script, " \
                    + "as the target branch disappears. Please close them manually, " \
                    + "or change the target branch.")
    prs = gh_pr_list(base='main', head=branch)
    if prs:
        raise GitError(f"There are open PRs from the release branch to main:\n" \
                    + "\n".join([f"PR#{pr} from {br}" for pr, br in prs.items()]) \
                    + "\nThese would conflict with the versioning script. "
                    + "Please close them manually.")

def _set_dependencies(package):
    # Manually get the xsuite dependencies from the pyproject.toml file (not from PyPi as things might have changed)
    xsuite_pkgs = ['xaux', 'xobjects', 'xdeps', 'xtrack', 'xpart', 'xfields', 'xcoll', 'xdyna', 'xboinc']
    xsuite_pkgs.remove(package)
    latest_version = {}
    for pkg in xsuite_pkgs:
        latest_version[pkg] = get_latest_package_version(pkg)
    with Path("pyproject.toml").open("r") as fid:
        lines = fid.readlines()
    with Path("pyproject.toml").open("w") as fid:
        for line in lines:
            if any([line.startswith(f"{pkg} =") or line.startswith(f"{pkg}=") for pkg in xsuite_pkgs]):
                for pkg in xsuite_pkgs:
                    if line.startswith(f"{pkg} ") or line.startswith(f"{pkg}="):
                        fid.write(f'{pkg} = ">={latest_version[pkg]}"\n')
                        break
            else:
                fid.write(line)

def _confirm_version_bump(expected_ver):
    current_ver = poetry_get_version()
    print(f"Bumping from {current_ver} to {expected_ver}.")
    print("Type y to continue (or anything else to cancel):")
    answer = input()
    if answer not in ["y", "Y"]:
        print("Cancelled.")
        sys.exit(1)


def _do_bump(expected_ver, bump=None):
    if bump is None:
        bump=expected_ver
    poetry_bump_version(bump)
    new_ver = poetry_get_version()
    if new_ver != expected_ver:
        raise VersionError(f"Fatal error: `poetry --dry-run` expected {expected_ver}, but result is {new_ver}..."
                            "Need to recover manually!")
    return new_ver


def _adapt_version_files(package, new_ver):
    for file, pattern in zip([f"{package}/general.py", "tests/test_version.py"],
                            ["__version__ = ", "    assert __version__ == "]):
        file_adapted = False
        with Path(file).open("r") as fid:
            lines = fid.readlines()
        with Path(file).open("w") as fid:
            for line in lines:
                if line.startswith(pattern):
                    fid.write(f"{pattern}'{new_ver}'\n")
                    file_adapted = True
                else:
                    fid.write(line)
        if not file_adapted:
            raise VersionError(f"Fatal error: could not adapt {file}...")
