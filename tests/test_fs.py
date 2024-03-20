# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from pathlib import Path
import os
import pytest

from xaux.fs import *
from xaux.fs.eos import EOS_CELL
from xaux.fs.afs import _fs_installed


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

