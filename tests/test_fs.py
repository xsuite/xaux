# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from pathlib import Path
import os
import pytest
import warnings

from xaux.fs import *
from xaux.fs.eos import EOS_CELL


_afs_test_path = "/afs/cern.ch/user/s/sixtadm/public/test_xboinc/"
_eos_test_path = "/eos/user/s/sixtadm/test_xboinc/"


def test_touch_and_symlinks_local():
    file = "example_file.txt"
    link = "example_link.txt"
    broken_link = "example_broken_link.txt"
    path_file = Path(file)
    path_link = Path(link)
    path_broken_link = Path(broken_link)
    for path in [path_file, path_link, path_broken_link]:
        if path.exists():
            path.unlink()
    # Assert correct file creation with standard pathlib API
    path_file.touch(exist_ok=False)
    path_link.symlink_to(path_file)
    path_broken_link.symlink_to(f"{file}_nonexistent")
    assert isinstance(path_file, Path)
    assert path_file.exists()
    assert isinstance(path_link, Path)
    assert path_link.exists()
    assert path_link.is_symlink()
    assert isinstance(path_broken_link, Path)
    assert not path_broken_link.exists()
    assert path_broken_link.is_symlink()
    # Test with LocalPath
    path_file = FsPath(file)
    path_link = FsPath(link)
    path_broken_link = FsPath(broken_link)
    assert isinstance(path_file, LocalPath)
    assert path_file.exists()
    assert isinstance(path_link, LocalPath)
    assert path_link.exists()
    assert path_link.lexists()
    assert path_link.is_symlink()
    assert not path_link.is_broken_symlink()
    assert isinstance(path_broken_link, LocalPath)
    assert path_broken_link.lexists()
    assert not path_broken_link.exists()
    assert path_broken_link.is_symlink()
    assert path_broken_link.is_broken_symlink()
    # Delete with pathlib API
    Path(file).unlink()
    Path(link).unlink()
    Path(broken_link).unlink()
    # Now create and test with FsPath
    path_file = FsPath(file)
    path_link = FsPath(link)
    path_broken_link = FsPath(broken_link)
    path_file.touch(exist_ok=False)
    path_link.symlink_to(path_file)
    path_broken_link.symlink_to(f"{file}_nonexistent")
    assert isinstance(path_file, LocalPath)
    assert path_file.exists()
    assert isinstance(path_link, LocalPath)
    assert path_link.exists()
    assert path_link.lexists()
    assert path_link.is_symlink()
    assert not path_link.is_broken_symlink()
    assert isinstance(path_broken_link, LocalPath)
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


def test_touch_and_symlinks_afs():
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
    if afs_accessible:
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
    else:
        with pytest.raises(EnvironmentError, match="AFS is not installed on your system."):
            path_file.touch()
        with pytest.raises(EnvironmentError, match="AFS is not installed on your system."):
            path_link.symlink_to(path_file)
        with pytest.raises(EnvironmentError, match="AFS is not installed on your system."):
            path_broken_link.symlink_to(f"{file}_nonexistent")


def test_touch_and_symlinks_eos():
    file = (Path(_eos_test_path) / "example_file.txt").as_posix()
    link = (Path(_eos_test_path) / "example_link.txt").as_posix()
    broken_link = (Path(_eos_test_path) / "example_broken_link.txt").as_posix()
    # Create and test with FsPath
    path_file = FsPath(file)
    path_link = FsPath(link)
    path_broken_link = FsPath(broken_link)
    assert isinstance(path_file, EosPath)
    assert isinstance(path_link, EosPath)
    assert isinstance(path_broken_link, EosPath)
    if eos_accessible:
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
    else:
        with pytest.raises(EnvironmentError, match="EOS is not installed on your system."):
            path_file.touch()
        with pytest.raises(EnvironmentError, match="EOS is not installed on your system."):
            path_link.symlink_to(path_file)
        with pytest.raises(EnvironmentError, match="EOS is not installed on your system."):
            path_broken_link.symlink_to(f"{file}_nonexistent")


def _test_instantiation(file, PathClass, SystemPathClass, NonSystemPathClass, this_path):
    for path in [file, (Path.cwd() / file).as_posix(), Path(file), Path(file).resolve()]:
        for cls in [FsPath, PathClass, SystemPathClass]:
            # Testing all initialisations
            new_path = cls(path)
            assert new_path.resolve() == this_path
            # Testing all mixed initialisations
            for cls2 in [FsPath, PathClass, SystemPathClass]:
                new_path = cls2(cls(path))
                assert new_path.resolve() == this_path
            # Verifying that the correct class is returned
            for inst in [Path, FsPath, PathClass, SystemPathClass]:
                assert isinstance(new_path, inst)
            assert not isinstance(new_path, NonSystemPathClass)
        with pytest.raises(RuntimeError, match=f"Cannot instantiate " +
                           f"'{NonSystemPathClass.__name__}' on your system"):
            new_path = NonSystemPathClass(path)


def test_instantiation_local():
    LocalSystemPath    = LocalWindowsPath if os.name == 'nt' else LocalPosixPath
    LocalNonSystemPath = LocalPosixPath   if os.name == 'nt' else LocalWindowsPath
    file = "example_local_file.txt"
    rel_link = "example_local_relative_link.txt"
    abs_link = "example_local_absolute_link.txt"
    for f in [file, rel_link, abs_link]:
        if FsPath(f).exists():
            FsPath(f).unlink()
    this_path = LocalSystemPath(file).resolve()
    # Test with non-existing file
    print(f"Testing LocalPath with {file} (non-existent)...")
    _test_instantiation(file, LocalPath, LocalSystemPath, LocalNonSystemPath, this_path)
    # Test with existing file
    FsPath(file).touch()
    print(f"Testing LocalPath with {file} (existent)...")
    _test_instantiation(file, LocalPath, LocalSystemPath, LocalNonSystemPath, this_path)
    # Test with relative link
    print(f"Testing LocalPath with {rel_link} (relative link)...")
    FsPath(rel_link).symlink_to(Path(file))
    _test_instantiation(rel_link, LocalPath, LocalSystemPath, LocalNonSystemPath, this_path)
    # Test with absolute link
    print(f"Testing LocalPath with {abs_link} (absolute link)...")
    FsPath(abs_link).symlink_to(Path(file).resolve())
    _test_instantiation(abs_link, LocalPath, LocalSystemPath, LocalNonSystemPath, this_path)
    # Clean-up
    for f in [file, rel_link, abs_link]:
        FsPath(f).unlink()


def test_instantiation_afs():
    AfsSystemPath    = AfsWindowsPath if os.name == 'nt' else AfsPosixPath
    AfsNonSystemPath = AfsPosixPath   if os.name == 'nt' else AfsWindowsPath
    _file_rel = "example_afs_file.txt"
    file_abs = (Path(_afs_test_path) / _file_rel).as_posix()
    rel_link = (Path(_afs_test_path) / "example_afs_relative_link.txt").as_posix()
    abs_link = "example_afs_absolute_link.txt"
    fs_link = "afs_test"
    file_fs = (Path(fs_link) / _file_rel).as_posix()
    for f in [file_abs, rel_link, abs_link, fs_link]:
        if afs_accessible and FsPath(f).lexists():
            FsPath(f).unlink()
    this_path = AfsSystemPath(file_abs).resolve()
    # Test invalid paths
    with pytest.raises(ValueError, match="The path is not on AFS."):
        AfsPath("example_local_file.txt").resolve()
    with pytest.raises(ValueError, match="The path is not on AFS."):
        AfsPath(_eos_test_path).resolve()
    # Test with non-existing file
    print(f"Testing AfsPath with {file_abs} (non-existent)...")
    _test_instantiation(file_abs, AfsPath, AfsSystemPath, AfsNonSystemPath, this_path)
    if not afs_accessible:
            warnings.warn("AFS is not accessible. Skipping the rest of the test.")
    else:
        # Test with existing file
        FsPath(file_abs).touch()
        print(f"Testing AfsPath with {file_abs} (existent)...")
        _test_instantiation(file_abs, AfsPath, AfsSystemPath, AfsNonSystemPath, this_path)
        # Test with relative link
        FsPath(rel_link).symlink_to(Path(_file_rel))
        print(f"Testing AfsPath with {rel_link} (relative link)...")
        _test_instantiation(rel_link, AfsPath, AfsSystemPath, AfsNonSystemPath, this_path)
        # Test with absolute link
        FsPath(abs_link).symlink_to(Path(file_abs).resolve())
        print(f"Testing AfsPath with {abs_link} (absolute link)...")
        _test_instantiation(abs_link, AfsPath, AfsSystemPath, AfsNonSystemPath, this_path)
        # Test with local link to AFS folder
        FsPath(fs_link).symlink_to(Path(_afs_test_path).resolve())
        print(f"Testing AfsPath with {file_fs} (using local link to AFS folder)...")
        _test_instantiation(file_fs, AfsPath, AfsSystemPath, AfsNonSystemPath, this_path)
        # Clean-up
        for f in [file_abs, rel_link, abs_link, fs_link]:
            FsPath(f).unlink()


def test_instantiation_eos():
    EosSystemPath    = EosWindowsPath if os.name == 'nt' else EosPosixPath
    EosNonSystemPath = EosPosixPath   if os.name == 'nt' else EosWindowsPath
    _file_rel = "example_eos_file.txt"
    file_abs = (Path(_eos_test_path) / _file_rel).as_posix()
    rel_link = (Path(_eos_test_path) / "example_eos_relative_link.txt").as_posix()
    abs_link = "example_eos_absolute_link.txt"
    fs_link = "eos_test"
    file_fs = (Path(fs_link) / _file_rel).as_posix()
    for f in [file_abs, rel_link, abs_link, fs_link]:
        if eos_accessible and FsPath(f).lexists():
            FsPath(f).unlink()
    this_path = EosSystemPath(file_abs).resolve()
    # Test invalid paths
    with pytest.raises(ValueError, match="The path is not on EOS."):
        EosPath("example_local_file.txt").resolve()
    with pytest.raises(ValueError, match="The path is not on EOS."):
        EosPath(_afs_test_path).resolve()
    # Test with non-existing file
    print(f"Testing EosPath with {file_abs} (non-existent)...")
    _test_instantiation(file_abs, EosPath, EosSystemPath, EosNonSystemPath, this_path)
    if not eos_accessible:
            warnings.warn("EOS is not accessible. Skipping the remainder of test_instantiation_eos.")
    else:
        # Test with existing file
        FsPath(file_abs).touch()
        print(f"Testing EosPath with {file_abs} (existent)...")
        _test_instantiation(file_abs, EosPath, EosSystemPath, EosNonSystemPath, this_path)
        # Test with relative link
        FsPath(rel_link).symlink_to(Path(_file_rel))
        print(f"Testing EosPath with {rel_link} (relative link)...")
        _test_instantiation(rel_link, EosPath, EosSystemPath, EosNonSystemPath, this_path)
        # Test with absolute link
        FsPath(abs_link).symlink_to(Path(file_abs).resolve())
        print(f"Testing EosPath with {abs_link} (absolute link)...")
        _test_instantiation(abs_link, EosPath, EosSystemPath, EosNonSystemPath, this_path)
        # Test with local link to EOS folder
        FsPath(fs_link).symlink_to(Path(_eos_test_path).resolve())
        print(f"Testing EosPath with {file_fs} (using local link to EOS folder)...")
        _test_instantiation(file_fs, EosPath, EosSystemPath, EosNonSystemPath, this_path)
        # Clean-up
        for f in [file_abs, rel_link, abs_link, fs_link]:
            FsPath(f).unlink()


def test_eos_components():
    if EOS_CELL != "cern.ch":
        warnings.warn("This EOS test is only valid for the CERN EOS instance.")
    else:
        _file_rel = "example_eos_file.txt"
        file_ref = (Path(_eos_test_path) / _file_rel).as_posix()
        this_path = EosPath(file_ref).resolve()
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
            with pytest.raises(ValueError, match="Invalid EOS path specification"):
                path = EosPath(file)
        with pytest.raises(ValueError, match="Unknown path specification"):
            path = FsPath(broken_mgm_files[-1])


def test_afs_acl():
    path = FsPath(_afs_test_path)
    acl = path.acl
    print(acl)
    assert isinstance(acl, dict)
    assert "sixtadm" in acl
    assert ''.join(sorted(acl["sixtadm"].lower())) == "adiklrw"
    assert "testuser" not in acl
    path.acl = {"testuser": "rli"}
    acl = path.acl
    print(acl)
    assert "testuser" in acl
    assert ''.join(sorted(acl["testuser"].lower())) == "ilr"
    path.acl = {"testuser": None}
    acl = path.acl
    assert "testuser" not in acl

