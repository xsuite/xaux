# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from pathlib import Path
import os
import pytest
import numpy as np

from xaux.fs import *
from xaux.fs.afs import _fs_installed


def _test_user(test_user):
    if test_user['skip_afs']:
        pytest.skip("AFS test directory is not accessible.")
    return test_user['test_user']

def _afs_test_path(test_user, skip=True):
    if test_user['skip_afs'] and skip:
        pytest.skip("AFS test directory is not accessible.")
    return test_user['afs_path']

def _eos_test_path(test_user, skip=True):
    if test_user['skip_eos'] and skip:
        pytest.skip("EOS test directory is not accessible.")
    return test_user['eos_path']


@pytest.mark.skipif(not isinstance(FsPath.cwd(), LocalPath), reason="This test should be ran from a local path.")
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
        with pytest.raises(OSError, match=f"Cannot instantiate " +
                           f"'{NonSystemPathClass.__name__}' on your system"):
            new_path = NonSystemPathClass(path)


@pytest.mark.skipif(not isinstance(FsPath.cwd(), LocalPath), reason="This test should be ran from a local path.")
def test_instantiation_local():
    LocalSystemPath    = LocalWindowsPath if os.name == 'nt' else LocalPosixPath
    LocalNonSystemPath = LocalPosixPath   if os.name == 'nt' else LocalWindowsPath
    file = "example_local_file.txt"
    rel_link = "example_local_relative_link.txt"
    abs_link = "example_local_absolute_link.txt"
    for f in [file, rel_link, abs_link]:
        if FsPath(f).lexists():
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


@pytest.mark.skipif(not afs_accessible, reason="AFS is not accessible.")
@pytest.mark.skipif(not eos_accessible, reason="EOS is not accessible.")
@pytest.mark.skipif(not isinstance(FsPath.cwd(), LocalPath), reason="This test should be ran from a local path.")
def test_nested_fs(test_user):
    level1     = FsPath(_afs_test_path(test_user)) / "level1"
    level1_res = FsPath.cwd() / "level1"
    level1_res.mkdir(exist_ok=True)
    if level1.lexists():
        level1.unlink()
    level1.symlink_to(level1_res)
    level2     = level1_res / "level2"
    level2_res = FsPath(_eos_test_path(test_user)) / "level2_res"
    level2_res.mkdir(exist_ok=True)
    if level2.lexists():
        level2.unlink()
    level2.symlink_to(level2_res)
    level3     = level2_res / "level3"
    level3_res = FsPath(_afs_test_path(test_user)) / "level3_res"
    level3_res.mkdir(exist_ok=True)
    if level3.lexists():
        level3.unlink()
    level3.symlink_to(level3_res)
    level4     = level3_res / "level4"
    level4_res = FsPath(_eos_test_path(test_user)) / "level4_res"
    level4_res.mkdir(exist_ok=True)
    if level4.lexists():
        level4.unlink()
    level4.symlink_to(level4_res)
    level5     = level4_res / "level5"
    level5_res = FsPath.cwd() / "level5_res"
    level5_res.mkdir(exist_ok=True)
    if level5.lexists():
        level5.unlink()
    level5.symlink_to(level5_res)
    level6     = level5_res / "level6"
    level6_res = FsPath(_afs_test_path(test_user)) / "level6_res"
    level6_res.mkdir(exist_ok=True)
    if level6.lexists():
        level6.unlink()
    level6.symlink_to(level6_res)

    path = level1 / "level2" / "level3" / "level4" / "level5" / "level6"
    assert isinstance(path, LocalPath)
    parents = [f for f in path.parents]
    expected = [EosPath, AfsPath, EosPath, LocalPath, AfsPath,
                AfsPath, AfsPath, AfsPath, AfsPath, AfsPath,
                AfsPath, LocalPath, LocalPath]
    assert np.all([isinstance(f, exp) for f, exp in zip(parents, expected)])
    assert isinstance(path.resolve(), AfsPath)
    parents_res = [f.resolve() for f in path.parents]
    expected_res = [LocalPath, EosPath, AfsPath, EosPath, LocalPath,
                    AfsPath, AfsPath, AfsPath, AfsPath, AfsPath,
                    AfsPath, LocalPath, LocalPath]
    assert np.all([isinstance(f, exp) for f, exp in zip(parents_res, expected_res)])

    level1.unlink()
    level2.unlink()
    level3.unlink()
    level4.unlink()
    level5.unlink()
    level6.unlink()
    level1_res.rmdir()
    level2_res.rmdir()
    level3_res.rmdir()
    level4_res.rmdir()
    level5_res.rmdir()
    level6_res.rmdir()
