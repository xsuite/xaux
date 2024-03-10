# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import os
from pathlib import Path, PurePosixPath, PureWindowsPath


def _non_strict_resolve(path, _as_posix=False):
    # This function is resolving without strict=True as this 
    # might lead to infinite loops in case of broken links.
    if not isinstance(path, Path):
        path = Path(path)
    cls = path.__class__
    path = path.expanduser().as_posix()
    path = os.path.realpath(path, strict=False)
    if _as_posix:
        return path
    else:
        return cls(path)


_eos_path = Path('/eos')

def _on_eos(*args):
    if isinstance(args[0], str):
        if args[0].startswith('/eos/'):
            return True
        elif args[0].startswith('root://eos'):
            return True
        elif args[0] == '/' and len(args) > 1 \
        and (args[1] == 'eos' or args[1] == 'eos/'):
            return True
    parents = _non_strict_resolve(Path(*args)).parents
    return len(parents) > 1 and parents[-2] == _eos_path


# Factory
class FsPath(Path):
    def __new__(cls, *args):
        if _on_eos(*args):
            return EosPath.__new__(EosPath, *args, _eos_checked=True)
        else:
            return Path.__new__(Path, *args)


class EosPath(Path):
    """Path subclass for EOS paths.

    Instantiating an FsPath should call this class.
    """
    __slots__ = ('MGM', 'eos_instance', 'eos_path', 'eos_path_full')

    def __new__(cls, *args, _eos_checked=False):
        if cls is EosPath:
            cls = EosWindowsPath if os.name == 'nt' else EosPosixPath
        if isinstance(args[0], str) \
        and args[0].startswith('root://eos'):
            if len(args) > 0:
                raise ValueError("When specifying the instance `root://eos...` "
                               + "in the path, the latter has to be given as "
                               + "one complete string.")
            parts = args[0].split('/')
            MGM = '/'.join(parts[:3])
            eos_instance = self.MGM.split('/')[2].split('.')[0].replace('eos', '')
            self = cls._from_parts(['/'.join(parts[3:])])
            self.MGM = MGM
            self.eos_instance = eos_instance
            assert self.MGM == f'root://eos{self.eos_instance}.cern.ch' # to verify rest of MGM
        else:
            self = cls._from_parts(args)
            self.eos_instance = _non_strict_resolve(self, _as_posix=True
                                                    ).split('/')[2].split('-')[0]
        if not self._flavour.is_supported:
            raise RuntimeError(f"cannot instantiate {cls.__name__} "
                              + "on your system.")
        if not _eos_checked and not _on_eos(self):
            raise ValueError("The path is not on EOS.")
        if self.eos_instance == 'home':
            self.eos_instance = 'user'
        self.MGM = f'root://eos{self.eos_instance}.cern.ch'
        parts = _non_strict_resolve(self, _as_posix=True).split('/')
        instance_parts = parts[2].split('-')
        if len(instance_parts) > 1:
            if len(instance_parts) > 2:
                raise ValueError(f"EOS instance {parts[2]} has more than one dash.")
            else:
                parts = ['', 'eos', self.eos_instance, instance_parts[1], *parts[3:]]
        else:
            parts = ['', 'eos', self.eos_instance, *parts[3:]]
        self.eos_path = '/'.join(parts)
        self.eos_path_full = f'{self.MGM}/{self.eos_path}'
        return self

    def resolve(self):
        return EosPath(self.eos_path)


class EosPosixPath(EosPath, PurePosixPath):
    """EosPath subclass for EOS paths on non-Windows systems.

    On a POSIX system, instantiating an FsPath or an EosPath
    should return this object.
    """
    __slots__ = ()

    if os.name == 'nt':
        def __new__(cls, *args, **kwargs):
            raise RuntimeError(
                f"cannot instantiate {cls.__name__!r} on your system")


class EosWindowsPath(EosPath, PureWindowsPath):
    """EosPath subclass for EOS paths on Windows systems.

    This is currently not supported.
    """
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "Windows currently not supported by EosPath.")

    if os.name != 'nt':
        def __new__(cls, *args, **kwargs):
            raise RuntimeError(
                f"cannot instantiate {cls.__name__!r} on your system")

