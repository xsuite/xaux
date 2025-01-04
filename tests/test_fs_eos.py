# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from pathlib import Path
import os
import pytest

from xaux.fs import *
from xaux.fs.eos_methods import EOS_CELL

from test_fs import _test_instantiation, _afs_test_path, _eos_test_path


@pytest.mark.skipif(eos_accessible, reason="EOS is accessible.")
def test_touch_and_symlinks_eos_no_access(test_user):
    eos_path = _eos_test_path(test_user, skip=False)
    file = (Path(eos_path) / "example_file.txt").as_posix()
    link = (Path(eos_path) / "example_link.txt").as_posix()
    broken_link = (Path(eos_path) / "example_broken_link.txt").as_posix()
    # Create and test with FsPath
    path_file = FsPath(file)
    path_link = FsPath(link)
    path_broken_link = FsPath(broken_link)
    assert isinstance(path_file, EosPath)
    assert isinstance(path_link, EosPath)
    assert isinstance(path_broken_link, EosPath)
    with pytest.raises(OSError, match="EOS is not installed on your system."):
        path_file.touch()
    with pytest.raises(OSError, match="EOS is not installed on your system."):
        path_link.symlink_to(path_file)
    with pytest.raises(OSError, match="EOS is not installed on your system."):
        path_broken_link.symlink_to(f"{file}_nonexistent")


@pytest.mark.skipif(not eos_accessible, reason="EOS is not accessible.")
def test_touch_and_symlinks_eos_access(test_user):
    file = (Path(_eos_test_path(test_user)) / "example_file.txt").as_posix()
    link = (Path(_eos_test_path(test_user)) / "example_link.txt").as_posix()
    broken_link = (Path(_eos_test_path(test_user)) / "example_broken_link.txt").as_posix()
    # Create and test with FsPath
    path_file = FsPath(file)
    path_link = FsPath(link)
    path_broken_link = FsPath(broken_link)
    assert isinstance(path_file, EosPath)
    assert isinstance(path_link, EosPath)
    assert isinstance(path_broken_link, EosPath)
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
    # Delete
    path_file.unlink()
    path_link.unlink()
    path_broken_link.unlink()



@pytest.mark.skipif(not isinstance(FsPath.cwd(), LocalPath), reason="This test should be ran from a local path.")
def test_instantiation_eos(test_user):
    EosSystemPath    = EosWindowsPath if os.name == 'nt' else EosPosixPath
    EosNonSystemPath = EosPosixPath   if os.name == 'nt' else EosWindowsPath
    file_abs = (Path(_eos_test_path(test_user, skip=False)) / "example_eos_file.txt").as_posix()
    if eos_accessible and Path(file_abs).exists():
        Path(file_abs).unlink()
    this_path = EosSystemPath(file_abs)
    # Test non-existing file
    print(f"Testing EosPath with {file_abs} (non-existent)...")
    _test_instantiation(file_abs, EosPath, EosSystemPath, EosNonSystemPath, this_path)
    # Test invalid paths
    with pytest.raises(ValueError, match="The path is not on EOS."):
        EosPath("example_local_file.txt")
    with pytest.raises(ValueError, match="The path is not on EOS."):
        EosPath(_afs_test_path(test_user, skip=False))


@pytest.mark.skipif(not eos_accessible, reason="EOS is not accessible.")
@pytest.mark.skipif(not isinstance(FsPath.cwd(), LocalPath), reason="This test should be ran from a local path.")
def test_instantiation_eos_access(test_user):
    EosSystemPath    = EosWindowsPath if os.name == 'nt' else EosPosixPath
    EosNonSystemPath = EosPosixPath   if os.name == 'nt' else EosWindowsPath
    _file_rel = "example_eos_file.txt"
    _link_rel = "example_eos_relative_link.txt"
    file_abs = (Path(_eos_test_path(test_user)) / _file_rel).as_posix()
    rel_link = (Path(_eos_test_path(test_user)) / _link_rel).as_posix() # on EOS, will point (relative) to _file_rel
    abs_link = "example_eos_absolute_link.txt"        # on local, will point (absolute) to file_abs
    fs_link = "eos_test"                              # on local, will point to absolute EOS folder
    file_fs = (Path(fs_link) / _file_rel).as_posix()  # on local linked folder, equal to file_abs
    rel_link_fs = (Path(fs_link) / _link_rel).as_posix()   # on local linked folder, will point (relative) to _file_rel
    file_local = "example_file.txt"
    link_fs_to_local = (Path(fs_link) / "example_eos_link_to_fs.txt").as_posix() # on local linked folder, will point (absolute) to local file
    abs_link_fs = (Path(fs_link) / "example_eos_double_link.txt").as_posix()     # on local linked folder, will point (absolute) to abs_link

    # Clean start
    for f in [file_abs, rel_link, abs_link, file_fs, rel_link_fs, \
              file_local, link_fs_to_local, abs_link_fs, fs_link]:   # fs_link should go last..
        if FsPath(f).lexists():
            FsPath(f).unlink()
    this_path = EosSystemPath(file_abs).resolve()

    # Test with existing file
    print(f"Testing EosPath with {file_abs} (existent)...")
    path_file_abs = FsPath(file_abs)
    path_file_abs.touch()
    _test_instantiation(file_abs, EosPath, EosSystemPath, EosNonSystemPath, this_path)
    assert path_file_abs.exists()
    assert path_file_abs.is_file()

    # Test with relative link
    print(f"Testing EosPath with {rel_link} (relative link on EOS pointing to EOS file)...")
    path_rel_link = FsPath(rel_link)
    path_rel_link.symlink_to(FsPath(_file_rel))
    _test_instantiation(rel_link, EosPath, EosSystemPath, EosNonSystemPath, this_path)
    assert isinstance(path_rel_link, EosPath)
    assert path_rel_link.exists()
    assert path_rel_link.is_symlink()
    assert not path_rel_link.is_broken_symlink()
    resolved = path_rel_link.resolve()
    assert isinstance(resolved, EosPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Test with absolute link
    print(f"Testing EosPath with {abs_link} (absolute link on local fs pointing to EOS file)...")
    path_abs_link = FsPath(abs_link)
    path_abs_link.symlink_to(path_file_abs)
    assert isinstance(path_abs_link, LocalPath)
    assert path_abs_link.exists()
    assert path_abs_link.is_symlink()
    assert not path_abs_link.is_broken_symlink()
    resolved = path_abs_link.resolve()
    assert isinstance(resolved, EosPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Create local link to EOS folder
    print(f"Testing EosPath with {fs_link} (local link to EOS folder)...")
    path_fs_link = FsPath(fs_link)
    path_fs_link.symlink_to(FsPath(_eos_test_path(test_user)))
    assert isinstance(path_fs_link, LocalPath)
    assert path_fs_link.exists()
    assert path_fs_link.is_symlink()
    assert not path_fs_link.is_broken_symlink()
    resolved = path_fs_link.resolve()
    assert isinstance(resolved, EosPath)
    assert resolved.exists()
    assert resolved.is_dir()

    # Test with file local linked EOS folder
    print(f"Testing EosPath with {file_fs} (file on local linked EOS folder)...")
    path_file_fs = FsPath(file_fs)    # already exists
    assert isinstance(path_file_fs, EosPath)
    assert path_file_fs.exists()
    assert path_file_fs.is_file()
    resolved = path_file_fs.resolve()
    assert isinstance(resolved, EosPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Test with relative link on local linked EOS folder
    print(f"Testing EosPath with {rel_link_fs} (relative link on local linked EOS folder)...")
    path_rel_link_fs = FsPath(rel_link_fs)   # already exists
    assert isinstance(path_rel_link_fs, EosPath)
    assert path_rel_link_fs.exists()
    assert path_rel_link_fs.is_symlink()
    assert not path_rel_link_fs.is_broken_symlink()
    resolved = path_rel_link_fs.resolve()
    assert isinstance(resolved, EosPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Test with absolute link (pointing to local file) on local linked EOS folder
    print(f"Testing EosPath with {link_fs_to_local} (absolute link on local linked EOS folder pointing to local file)...")
    path_file_local = FsPath(file_local).resolve()
    path_file_local.touch()
    assert isinstance(path_file_local, LocalPath)
    assert path_file_local.exists()
    assert path_file_local.is_file()
    path_link_fs_to_local = FsPath(link_fs_to_local)
    path_link_fs_to_local.symlink_to(path_file_local)
    assert isinstance(path_link_fs_to_local, EosPath)
    assert path_link_fs_to_local.exists()
    assert path_link_fs_to_local.is_symlink()
    assert not path_link_fs_to_local.is_broken_symlink()
    resolved = path_link_fs_to_local.resolve()
    assert isinstance(resolved, LocalPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == path_file_local.resolve()

    # Test with absolute link (pointing to local absolute link) on local linked EOS folder
    print(f"Testing EosPath with {abs_link_fs} (absolute link on local linked EOS folder pointing to local absolute link)...")
    path_abs_link_fs = FsPath(abs_link_fs)
    path_abs_link_fs.symlink_to(FsPath.cwd() / abs_link)
    assert isinstance(path_abs_link_fs, EosPath)
    assert path_abs_link_fs.exists()
    assert path_abs_link_fs.is_symlink()
    assert not path_abs_link_fs.is_broken_symlink()
    resolved = path_abs_link_fs.resolve()
    assert isinstance(resolved, EosPath)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved == this_path

    # Clean-up
    for f in [path_file_abs, path_rel_link, path_abs_link, \
              path_file_local, path_link_fs_to_local, \
              path_abs_link_fs, path_fs_link]:   # fs_link should go last..
        # file_fs and rel_link_fs are already deleted as file_abs and rel_link
        f.unlink()


@pytest.mark.skipif(EOS_CELL != "cern.ch", reason="This test is only valid for the CERN EOS instance.")
def test_eos_components(test_user):
    _file_rel = "example_eos_file_components.txt"
    file_ref = (Path(_eos_test_path(test_user, skip=False)) / _file_rel).as_posix()
    this_path = EosPath(file_ref)
    assert isinstance(this_path, EosPath)
    files = [file_ref]
    files.append(file_ref.replace("/user/", "/home/"))
    files.append(file_ref.replace("/user/", "/user-"))
    files.append(file_ref.replace("/user/", "/home-"))
    for file in files[:4]:
        files.append(f"root://eosuser.cern.ch/{file}")
        files.append(f"root://eoshome.cern.ch/{file}")
    for file in files:
        print(f"Testing EosPath components with {file}...")
        path = FsPath(file)
        if eos_accessible:
            assert path.resolve() == this_path
        assert isinstance(path, EosPath)
        assert path.eos_instance == "user"
        assert path.mgm == f"root://eosuser.cern.ch"
        assert path.eos_path == file_ref
        assert path.eos_path_full == f"{path.mgm}/{file_ref}"
    broken_mgm_files = [f"root://eoshome.cern.ch{file_ref}"]
    broken_mgm_files.append(f"root:/eoshome.cern.ch/{file_ref}")
    broken_mgm_files.append(f"root://afshome.cern.ch/{file_ref}")
    for file in broken_mgm_files:
        with pytest.raises(ValueError, match="Invalid EosPath specification"):
            path = EosPath(file)
    with pytest.raises(ValueError, match="Unknown EosPath specification"):
        path = FsPath(broken_mgm_files[-1])

