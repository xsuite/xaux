# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

from pathlib import Path
import os
import pytest

from xaux.fs import *
from xaux.fs.afs import _afs_mounted
from xaux.fs.eos_methods import _xrdcp_installed, _eoscmd_installed, _eos_mounted
import xaux.fs  # to set test flags

from test_fs import _afs_test_path, _eos_test_path

def test_fs_methods():
    all_stat_fields = [k for k in os.stat_result.__dict__ if k.startswith('st_')]
    test_stats = Path('test_fs_api.py').stat()
    stat_dict = {}
    for key in all_stat_fields:
        stat_dict[key] = getattr(test_stats, key)
    new_stats = make_stat_result(stat_dict)
    print(test_stats)
    print(new_stats)
    assert new_stats == test_stats

    assert size_expand('4k') == 4000
    assert size_expand('4k', binary=True) == 4096
    assert size_expand('4m') == 4000000
    assert size_expand('4m', binary=True) == 4194304
    assert size_expand('4g') == 4000000000
    assert size_expand('4g', binary=True) == 4294967296
    assert size_expand('4t') == 4000000000000
    assert size_expand('4t', binary=True) == 4398046511104


def test_fspath_methods():
    # Test truediv
    new_path = FsPath('/afs/cern.ch') / FsPath('tripco.txt')
    print(repr(new_path))
    assert isinstance(new_path, AfsPath)
    new_path = FsPath('/eos/public') / FsPath('tripco.txt')
    print(repr(new_path))
    assert isinstance(new_path, EosPath)
    if afs_accessible:
        path_afs_link = FsPath("~/afs_test").expanduser()
        if path_afs_link.lexists():
            path_afs_link.unlink()
        path_afs_link.symlink_to(FsPath(_afs_test_path))
        test = FsPath("~/afs_test/default_file.txt").expanduser()
        assert isinstance(test, AfsPath)
        test = FsPath.home() / "afs_test" / "default_file.txt"
        assert isinstance(test, AfsPath)
        path_afs_link.unlink()
    if eos_accessible:
        path_eos_link = FsPath("~/eos_test").expanduser()
        if path_eos_link.lexists():
            path_eos_link.unlink()
        path_eos_link.symlink_to(FsPath(_eos_test_path))
        test = FsPath("~/eos_test/default_file.txt").expanduser()
        assert isinstance(test, EosPath)
        test = FsPath.home() / "eos_test" / "default_file.txt"
        assert isinstance(test, EosPath)
        path_eos_link.unlink()


@pytest.mark.skipif(not afs_accessible, reason="AFS is not accessible.")
@pytest.mark.parametrize("afs_cmd", [0, 1], ids=["xrdcp", "mount"])
def test_file_io_afs(afs_cmd):
    xaux.fs._force_xrdcp = False
    xaux.fs._skip_afs_software = False
    xaux.fs._skip_eos_software = False
    if afs_cmd == 0:
        if not _xrdcp_installed:
            pytest.skip("The command `xrdcp` is not installed.")
        xaux.fs._force_xrdcp = True
    if afs_cmd == 1:
        if not _afs_mounted:
            pytest.skip("The AFS file system is not mounted.")
        xaux.fs._skip_afs_software = True

    # Make a link to AFS
    path_afs_link = FsPath("~/afs_test").expanduser()
    if path_afs_link.lexists():
        path_afs_link.unlink()
    path_afs_link.symlink_to(FsPath(_afs_test_path))

    # Copy one file
    local_file_1 = FsPath("default_file_1.txt")
    local_file_1.touch()
    assert local_file_1.exists()
    with pytest.raises(NotADirectoryError, match="is not a directory."):
        local_file_1.rmdir()
    target = FsPath("~/afs_test/default_file_1.txt").expanduser()
    assert isinstance(target, AfsPath)
    if target.exists():
        target.unlink()
    local_file_1.copy_to("~/afs_test/")
    assert target.exists()
    assert local_file_1.exists()
    target.unlink()
    assert not target.exists()

    # Move one file
    local_file_2 = FsPath("default_file_2.txt")
    local_file_2.touch()
    assert local_file_2.exists()
    target = FsPath("~/afs_test/default_file_2.txt").expanduser()
    assert isinstance(target, AfsPath)
    if target.exists():
        target.unlink()
    local_file_2.move_to("~/afs_test/")
    assert target.exists()
    assert not local_file_2.exists()
    target.unlink()
    assert not target.exists()

    # Copy several files
    local_file_2.touch()
    local_files = [local_file_1, local_file_2]
    for i in range(3, 8):
        file = FsPath(f"default_file_{i}.txt")
        file.touch()
        assert file.exists()
        local_files.append(file)
    for i in range(1, 8):
        target = FsPath(f"~/afs_test/default_file_{i}.txt").expanduser()
        if target.exists():
            target.unlink()
    print(cp(*local_files, "~/afs_test/"))
    for i in range(1, 8):
        target = FsPath(f"~/afs_test/default_file_{i}.txt").expanduser()
        assert target.exists()
        target.unlink()
        assert not target.exists()
    for file in local_files:
        assert file.exists()

    # Move several files
    print(mv(*local_files, "~/afs_test/"))
    for i in range(1, 8):
        target = FsPath(f"~/afs_test/default_file_{i}.txt").expanduser()
        assert target.exists()
        target.unlink()
        assert not target.exists()
    for file in local_files:
        assert not file.exists()

    # Make a directory
    dir_path = FsPath("~/afs_test/Blibo").expanduser()
    if dir_path.exists():
        dir_path.rmtree()
    dir_path.mkdir()
    assert dir_path.exists()
    assert dir_path.is_dir()
    assert not dir_path.is_file()
    assert not dir_path.is_symlink()
    assert not dir_path.is_broken_symlink()
    assert isinstance(dir_path, AfsPath)
    with pytest.raises(IsADirectoryError, match="is a directory."):
        dir_path.unlink()
    dir_path.rmdir()
    assert not dir_path.exists()

    # Make it again, and try copying/deleting a full directory
    dir_path.mkdir()
    assert dir_path.exists()
    assert dir_path.is_dir()
    for file in local_files:
        file.touch()
        assert file.exists()
    print(mv(*local_files, "~/afs_test/Blibo/"))
    for file in local_files:
        assert not file.exists()
    for i in range(1, 8):
        target = FsPath(f"~/afs_test/Blibo/default_file_{i}.txt").expanduser()
        assert target.exists()
    # Copy the directory to a new directory
    new_dir_path = FsPath("~/afs_test/BliboContainer").expanduser()
    if new_dir_path.exists():
        new_dir_path.rmtree()
    new_dir_path.mkdir()
    assert new_dir_path.exists()
    # First, fail to copy the directory because recursive is False
    stdout = dir_path.copy_to(new_dir_path, recursive=False)
    assert not FsPath("~/afs_test/BliboContainer/Blibo").exists()
    assert stdout.startswith("cp: -r not specified; omitting directory")
    # Now copy the directory
    dir_path.copy_to(new_dir_path)
    # Check the copy was successful
    assert FsPath("~/afs_test/BliboContainer/Blibo").exists()
    for i in range(1, 8):
        target = FsPath(f"~/afs_test/BliboContainer/Blibo/default_file_{i}.txt").expanduser()
        assert target.exists()
    # Check the originals are still present
    assert dir_path.exists()
    for i in range(1, 8):
        target = dir_path / f"default_file_{i}.txt"
        assert target.exists()
    # Remove the originals
    with pytest.raises((OSError, FileExistsError)) as exc_info:
        dir_path.rmdir()
    if exc_info.type is OSError:
        assert "Directory not empty" in str(exc_info.value)
    dir_path.rmtree()
    assert not dir_path.exists()
    # Move the new folder back
    last_dir_path = FsPath("~/afs_test/BliboContainer/Blibo").expanduser()
    last_dir_path.move_to(last_dir_path / '../..')
    assert not last_dir_path.exists()
    assert new_dir_path.exists()
    assert dir_path.exists()
    for i in range(1, 8):
        target = dir_path / f"default_file_{i}.txt"
        assert target.exists()
    # Remove all
    dir_path.rmtree()
    new_dir_path.rmtree()
    path_afs_link.unlink()
    xaux.fs._skip_afs_software = False
    xaux.fs._force_xrdcp = False


@pytest.mark.skipif(not eos_accessible, reason="EOS is not accessible.")
@pytest.mark.parametrize("eos_cmd", [0, 1, 2], ids=["xrdcp", "eos", "mount"])
def test_file_io_eos(eos_cmd):
    xaux.fs._force_xrdcp = False
    xaux.fs._force_eoscmd = False
    xaux.fs._skip_eos_software = False
    xaux.fs._skip_afs_software = False
    if eos_cmd == 0:
        if not _xrdcp_installed:
            pytest.skip("The command `xrdcp` is not installed.")
        xaux.fs._force_xrdcp = True
    if eos_cmd == 1:
        if not _eoscmd_installed:
            pytest.skip("The command `eos` is not installed.")
        xaux.fs._force_eoscmd = True
    if eos_cmd == 2:
        if not _eos_mounted:
            pytest.skip("The EOS file system is not mounted.")
        xaux.fs._skip_eos_software = True

    # Make a link to EOS
    path_eos_link = FsPath("~/eos_test").expanduser()
    if path_eos_link.lexists():
        path_eos_link.unlink()
    path_eos_link.symlink_to(FsPath(_eos_test_path))

    # Copy one file
    local_file_1 = FsPath("default_file_1.txt")
    local_file_1.touch()
    assert local_file_1.exists()
    with pytest.raises(NotADirectoryError, match="is not a directory."):
        local_file_1.rmdir()
    target = FsPath("~/eos_test/default_file_1.txt").expanduser()
    assert isinstance(target, EosPath)
    if target.exists():
        target.unlink()
    local_file_1.copy_to("~/eos_test/")
    assert target.exists()
    assert local_file_1.exists()
    target.unlink()
    assert not target.exists()

    # Move one file
    local_file_2 = FsPath("default_file_2.txt")
    local_file_2.touch()
    assert local_file_2.exists()
    target = FsPath("~/eos_test/default_file_2.txt").expanduser()
    assert isinstance(target, EosPath)
    if target.exists():
        target.unlink()
    local_file_2.move_to("~/eos_test/")
    assert target.exists()
    assert not local_file_2.exists()
    target.unlink()
    assert not target.exists()

    # Copy several files
    local_file_2.touch()
    local_files = [local_file_1, local_file_2]
    for i in range(3, 8):
        file = FsPath(f"default_file_{i}.txt")
        file.touch()
        assert file.exists()
        local_files.append(file)
    for i in range(1, 8):
        target = FsPath(f"~/eos_test/default_file_{i}.txt").expanduser()
        if target.exists():
            target.unlink()
    print(cp(*local_files, "~/eos_test/"))
    for i in range(1, 8):
        target = FsPath(f"~/eos_test/default_file_{i}.txt")
        assert target.exists()
        target.unlink()
        assert not target.exists()
    for file in local_files:
        assert file.exists()

    # Move several files
    print(mv(*local_files, "~/eos_test/"))
    for i in range(1, 8):
        target = FsPath(f"~/eos_test/default_file_{i}.txt").expanduser()
        assert target.exists()
        target.unlink()
        assert not target.exists()
    for file in local_files:
        assert not file.exists()

    # Make a directory
    dir_path = FsPath("~/eos_test/Blibo").expanduser()
    if dir_path.exists():
        dir_path.rmtree()
    dir_path.mkdir()
    assert dir_path.exists()
    assert dir_path.is_dir()
    assert not dir_path.is_file()
    assert not dir_path.is_symlink()
    assert not dir_path.is_broken_symlink()
    assert isinstance(dir_path, EosPath)
    with pytest.raises(IsADirectoryError, match="is a directory."):
        dir_path.unlink()
    dir_path.rmdir()
    assert not dir_path.exists()

    # Make it again, and try copying/deleting a full directory
    dir_path.mkdir()
    assert dir_path.exists()
    assert dir_path.is_dir()
    for file in local_files:
        file.touch()
        assert file.exists()
    print(mv(*local_files, "~/eos_test/Blibo/"))
    for file in local_files:
        assert not file.exists()
    for i in range(1, 8):
        target = FsPath(f"~/eos_test/Blibo/default_file_{i}.txt").expanduser()
        assert target.exists()
    # Copy the directory to a new directory
    new_dir_path = FsPath("~/eos_test/BliboContainer").expanduser()
    if new_dir_path.exists():
        new_dir_path.rmtree()
        assert not new_dir_path.exists()
    new_dir_path.mkdir()
    assert new_dir_path.exists()
    # First, fail to copy the directory because recursive is False
    stdout = dir_path.copy_to(new_dir_path, recursive=False)
    assert not FsPath("~/afs_test/BliboContainer/Blibo").exists()
    assert stdout.startswith("cp: -r not specified; omitting directory")
    # Now copy the directory
    dir_path.copy_to(new_dir_path)
    # Check the copy was successful
    assert FsPath("~/eos_test/BliboContainer/Blibo").exists()
    for i in range(1, 8):
        target = FsPath(f"~/eos_test/BliboContainer/Blibo/default_file_{i}.txt").expanduser()
        assert target.exists()
    # Check the originals are still present
    assert dir_path.exists()
    for i in range(1, 8):
        target = dir_path / f"default_file_{i}.txt"
        assert target.exists()
    # Remove the originals
    if eos_cmd != 0:   # TODO: remove when xrdfs implemented
        with pytest.raises((OSError, FileExistsError)) as exc_info:
            dir_path.rmdir()
        if exc_info.type is OSError:
            assert "Directory not empty" in str(exc_info.value)
    dir_path.rmtree()
    assert not dir_path.exists()
    # Move the new folder back
    last_dir_path = FsPath("~/eos_test/BliboContainer/Blibo").expanduser()
    last_dir_path.move_to(last_dir_path / '../..')
    assert not last_dir_path.exists()
    assert new_dir_path.exists()
    assert dir_path.exists()
    for i in range(1, 8):
        target = dir_path / f"default_file_{i}.txt"
        assert target.exists()
    # Remove all
    dir_path.rmtree()
    new_dir_path.rmtree()
    path_eos_link.unlink()
    xaux.fs._force_xrdcp = False
    xaux.fs._force_eoscmd = False
    xaux.fs._skip_eos_software = False


