# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from pathlib import Path
import os
import pytest

from xaux.fs import *
from xaux.fs.afs import _fs_installed

from test_fs import _test_instantiation, _afs_test_path, _eos_test_path, _test_user


@pytest.mark.skipif(afs_accessible, reason="AFS is accessible.")
def test_touch_and_symlinks_afs_no_access():
    file = (Path(_afs_test_path) / "example_file.txt").as_posix()
    link = (Path(_afs_test_path) / "example_link.txt").as_posix()
    broken_link = (Path(_afs_test_path) / "example_broken_link.txt").as_posix()
    # Create and test with FsPath
    path_file = FsPath(file)
    path_link = FsPath(link)
    path_broken_link = FsPath(broken_link)
    assert isinstance(path_file, AfsPath)
    assert isinstance(path_link, AfsPath)
    assert isinstance(path_broken_link, AfsPath)
    with pytest.raises(OSError, match="AFS is not installed on your system."):
        path_file.touch()
    with pytest.raises(OSError, match="AFS is not installed on your system."):
        path_link.symlink_to(path_file)
    with pytest.raises(OSError, match="AFS is not installed on your system."):
        path_broken_link.symlink_to(f"{file}_nonexistent")


@pytest.mark.skipif(not afs_accessible, reason="AFS is not accessible.")
def test_touch_and_symlinks_afs_access():
    file = (Path(_afs_test_path) / "example_file.txt").as_posix()
    link = (Path(_afs_test_path) / "example_link.txt").as_posix()
    broken_link = (Path(_afs_test_path) / "example_broken_link.txt").as_posix()
    # Create and test with FsPath
    path_file = FsPath(file)
    path_link = FsPath(link)
    path_broken_link = FsPath(broken_link)
    assert isinstance(path_file, AfsPath)
    assert isinstance(path_link, AfsPath)
    assert isinstance(path_broken_link, AfsPath)
    for path in [path_file, path_link, path_broken_link]:
        if path.lexists():
            path.unlink()
        assert not path.exists()
        assert not path.lexists()
    path_file.touch(exist_ok=False)
    path_link.symlink_to(path_file)
    path_broken_link.symlink_to(f"{file}_nonexistent")
    assert path_file.exists()
    assert path_link.exists()
    assert path_link.lexists()
    assert path_link.is_symlink()
    assert not path_link.is_broken_symlink()
    assert path_broken_link.lexists()
    assert not path_broken_link.exists()
    assert path_broken_link.is_symlink()
    assert path_broken_link.is_broken_symlink()
    # Double-check existence with pathlib API
    assert Path(file).exists()
    assert Path(link).exists()
    assert Path(link).is_symlink()
    assert not Path(broken_link).exists()
    assert Path(broken_link).is_symlink()
    # Delete with FsPath
    path_file.unlink()
    path_link.unlink()
    path_broken_link.unlink()


@pytest.mark.skipif(not isinstance(FsPath.cwd(), LocalPath), reason="This test should be ran from a local path.")
def test_instantiation_afs():
    AfsSystemPath    = AfsWindowsPath if os.name == 'nt' else AfsPosixPath
    AfsNonSystemPath = AfsPosixPath   if os.name == 'nt' else AfsWindowsPath
    file_abs = (Path(_afs_test_path) / "example_afs_file.txt").as_posix()
    if afs_accessible and Path(file_abs).exists():
        Path(file_abs).unlink()
    this_path = AfsSystemPath(file_abs)
    # Test non-existing file
    print(f"Testing AfsPath with {file_abs} (non-existent)...")
    _test_instantiation(file_abs, AfsPath, AfsSystemPath, AfsNonSystemPath, this_path)
    # Test invalid paths
    with pytest.raises(ValueError, match="The path is not on AFS."):
        AfsPath("example_local_file.txt")
    with pytest.raises(ValueError, match="The path is not on AFS."):
        AfsPath(_eos_test_path)


@pytest.mark.skipif(not afs_accessible, reason="AFS is not accessible.")
@pytest.mark.skipif(not isinstance(FsPath.cwd(), LocalPath), reason="This test should be ran from a local path.")
def test_instantiation_afs_access():
    AfsSystemPath    = AfsWindowsPath if os.name == 'nt' else AfsPosixPath
    AfsNonSystemPath = AfsPosixPath   if os.name == 'nt' else AfsWindowsPath
    LocalSystemPath    = LocalWindowsPath if os.name == 'nt' else LocalPosixPath
    LocalNonSystemPath = LocalPosixPath   if os.name == 'nt' else LocalWindowsPath
    _file_rel = "example_afs_file.txt"
    _link_rel = "example_afs_relative_link.txt"
    file_abs = (Path(_afs_test_path) / _file_rel).as_posix()
    rel_link = (Path(_afs_test_path) / _link_rel).as_posix() # on AFS, will point (relative) to _file_rel
    abs_link = "example_afs_absolute_link.txt"               # on local, will point (absolute) to file_abs
    fs_link = "afs_test"                                     # on local, will point to absolute AFS folder
    file_fs = (Path(fs_link) / _file_rel).as_posix()         # on local linked folder, equal to file_abs
    rel_link_fs = (Path(fs_link) / _link_rel).as_posix()     # on local linked folder, will point (relative) to _file_rel
    file_local = "example_file.txt"
    link_fs_to_local = (Path(fs_link) / "example_afs_link_to_fs.txt").as_posix() # on local linked folder, will point (absolute) to local file
    abs_link_fs = (Path(fs_link) / "example_afs_double_link.txt").as_posix()     # on local linked folder, will point (absolute) to abs_link

    # Clean start
    for f in [file_abs, rel_link, abs_link, file_fs, rel_link_fs, \
              file_local, link_fs_to_local, abs_link_fs, fs_link]:   # fs_link should go last..
        if FsPath(f).lexists():
            FsPath(f).unlink()
    this_path = AfsSystemPath(file_abs).resolve()

    # Test with existing file
    print(f"Testing AfsPath with {file_abs} (existent)...")
    path_file_abs = FsPath(file_abs)
    path_file_abs.touch()
    _test_instantiation(file_abs, AfsPath, AfsSystemPath, AfsNonSystemPath, this_path)
    assert path_file_abs.exists()
    assert path_file_abs.is_file()

    # Test with relative link
    print(f"Testing AfsPath with {rel_link} (relative link on AFS pointing to AFS file)...")
    path_rel_link = FsPath(rel_link)
    path_rel_link.symlink_to(FsPath(_file_rel))
    _test_instantiation(rel_link, AfsPath, AfsSystemPath, AfsNonSystemPath, this_path)
    assert isinstance(path_rel_link, AfsPath)
    assert path_rel_link.exists()
    assert path_rel_link.is_symlink()
    assert not path_rel_link.is_broken_symlink()
    resolved = path_rel_link.resolve()
    assert isinstance(resolved, AfsPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Test with absolute link
    print(f"Testing AfsPath with {abs_link} (absolute link on local fs pointing to AFS file)...")
    path_abs_link = FsPath(abs_link)
    path_abs_link.symlink_to(path_file_abs)
    _test_instantiation(abs_link, LocalPath, LocalSystemPath, LocalNonSystemPath, this_path)
    assert isinstance(path_abs_link, LocalPath)
    assert path_abs_link.exists()
    assert path_abs_link.is_symlink()
    assert not path_abs_link.is_broken_symlink()
    resolved = path_abs_link.resolve()
    assert isinstance(resolved, AfsPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Create local link to AFS folder
    print(f"Testing AfsPath with {fs_link} (local link to AFS folder)...")
    path_fs_link = FsPath(fs_link)
    path_fs_link.symlink_to(FsPath(_afs_test_path))
    assert isinstance(path_fs_link, LocalPath)
    assert path_fs_link.exists()
    assert path_fs_link.is_symlink()
    assert not path_fs_link.is_broken_symlink()
    resolved = path_fs_link.resolve()
    assert isinstance(resolved, AfsPath)
    assert resolved.exists()
    assert resolved.is_dir()

    # Test with file local linked AFS folder
    print(f"Testing AfsPath with {file_fs} (file on local linked AFS folder)...")
    path_file_fs = FsPath(file_fs)    # already exists
    assert isinstance(path_file_fs, AfsPath)
    assert path_file_fs.exists()
    assert path_file_fs.is_file()
    resolved = path_file_fs.resolve()
    assert isinstance(resolved, AfsPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Test with relative link on local linked AFS folder
    print(f"Testing AfsPath with {rel_link_fs} (relative link on local linked AFS folder)...")
    path_rel_link_fs = FsPath(rel_link_fs)   # already exists
    assert isinstance(path_rel_link_fs, AfsPath)
    assert path_rel_link_fs.exists()
    assert path_rel_link_fs.is_symlink()
    assert not path_rel_link_fs.is_broken_symlink()
    resolved = path_rel_link_fs.resolve()
    assert isinstance(resolved, AfsPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Test with absolute link (pointing to local file) on local linked AFS folder
    print(f"Testing AfsPath with {link_fs_to_local} (absolute link on local linked AFS folder pointing to local file)...")
    path_file_local = FsPath(file_local).resolve()
    path_file_local.touch()
    assert isinstance(path_file_local, LocalPath)
    assert path_file_local.exists()
    assert path_file_local.is_file()
    path_link_fs_to_local = FsPath(link_fs_to_local)
    path_link_fs_to_local.symlink_to(path_file_local)
    assert isinstance(path_link_fs_to_local, AfsPath)
    assert path_link_fs_to_local.exists()
    assert path_link_fs_to_local.is_symlink()
    assert not path_link_fs_to_local.is_broken_symlink()
    resolved = path_link_fs_to_local.resolve()
    assert isinstance(resolved, LocalPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == path_file_local.resolve()

    # Test with absolute link (pointing to local absolute link) on local linked AFS folder
    print(f"Testing AfsPath with {abs_link_fs} (absolute link on local linked AFS folder pointing to local absolute link)...")
    path_abs_link_fs = FsPath(abs_link_fs)
    path_abs_link_fs.symlink_to(FsPath.cwd() / abs_link)
    assert isinstance(path_abs_link_fs, AfsPath)
    assert path_abs_link_fs.exists()
    assert path_abs_link_fs.is_symlink()
    assert not path_abs_link_fs.is_broken_symlink()
    resolved = path_abs_link_fs.resolve()
    assert isinstance(resolved, AfsPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Clean-up
    for f in [path_file_abs, path_rel_link, path_abs_link, \
              path_file_local, path_link_fs_to_local, \
              path_abs_link_fs, path_fs_link]:   # fs_link should go last..
        # file_fs and rel_link_fs are already deleted as file_abs and rel_link
        f.unlink()


@pytest.mark.skipif(not _fs_installed, reason="The `fs` command is not installed.")
def test_afs_acl():
    path = FsPath(_afs_test_path)
    acl = path.acl
    print(acl)
    assert isinstance(acl, dict)
#     assert "sixtadm" in acl
#     assert ''.join(sorted(acl["sixtadm"].lower())) == "adiklrw"
    assert _test_user in acl
    assert ''.join(sorted(acl[_test_user].lower())) == "adiklrw"
    assert "testuser" not in acl
    path.acl = {"testuser": "rli"}
    acl = path.acl
    print(acl)
    assert "testuser" in acl
    assert ''.join(sorted(acl["testuser"].lower())) == "ilr"
    path.acl = {"testuser": None}
    acl = path.acl
    assert "testuser" not in acl

