# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import json
from pathlib import Path

# if __name__ == "__main__" or __name__ == "template":
#     from xaux.tools.singleton import singleton
# else:
#     from ..tools.singleton import singleton
# try:
#     from ..tools.singleton import singleton
# except ImportError:
#     from xaux.tools.singleton import singleton

# @singleton
class JobTemplate:
    def __init__(self, **kwargs):
        self._context = kwargs.get("_context", None)
        self.co_search_at = kwargs.get("co_search_at", None)
        self.line = kwargs.get("line", None)
        self.particles = kwargs.get("particles", None)
        if hasattr(self, 'validate_kwargs'):
            self.validate_kwargs(**kwargs)

    @property
    def line(self):
        return self._line

    @line.setter
    def line(self, line):
        import xtrack as xt
        if isinstance(line, (xt.Line,xt.Multiline,xt.Environment)):
            self._line = line
        elif isinstance(line, (str, Path)):
            line = Path(line)
            if not line.exists():
                raise ValueError(f"Line file {line} does not exist!")
            self._line = xt.Line.from_json(line, _context=self._context)
        elif line is not None:
            raise ValueError(f"Invalid line type {type(line)}")
        else:
            self._line = None

    @property
    def particles(self):
        return self._particles

    @particles.setter
    def particles(self, particles):
        import xtrack as xt
        if isinstance(particles, xt.Particles):
            self._particles = particles
        elif isinstance(particles, (str, Path)):
            particles = Path(particles) # TODO: verify context is consistent and adapt if needed
            if not particles.exists():
                raise ValueError(f"particles file {particles} does not exist!")
            if particles.suffix == '.json':
                # TODO: what if these are normalised particle coordinates?
                with open(particles, 'r') as fid:
                    self._particles= xt.Particles.from_dict(json.load(fid),
                                            _context=self._context)
            elif particles.suffix == '.parquet':
                # TODO: what if these are normalised particle coordinates?
                import pandas as pd
                with open(particles, 'rb') as fid:
                    self._particles = xt.Particles.from_pandas(
                        pd.read_parquet(fid, engine="pyarrow"), _context=self._context)
            else:
                raise ValueError(f"Unknown file extension {particles.suffix} for Particles!")
        elif particles is not None:
            raise ValueError(f"Invalid particles type {type(particles)}")
        else:
            self._particles = None

    @classmethod
    def run(cls, **kwargs):
        self = cls(**kwargs)
        if hasattr(self, 'generate_line'):
            self.generate_line(**kwargs)
        if hasattr(self, 'pre_build'):
            self.pre_build(**kwargs)
        self.line.build_tracker(_context=self._context)
        if hasattr(self, 'post_build'):
            self.post_build(**kwargs)
        if hasattr(self, 'generate_particles'):
            self.generate_particles(**kwargs)
        if hasattr(self, 'pre_track'):
            self.pre_track(**kwargs)
        self.track(**kwargs)
        if hasattr(self, 'post_track'):
            self.post_track(**kwargs)
        self.generate_output(**kwargs)

    def track(self, **kwargs):
        num_turns = int(kwargs.get("num_turns", 1))
        ele_start = kwargs.get("ele_start", None)
        ele_stop = kwargs.get("ele_stop", None)
        with_progress = bool(kwargs.get("with_progress", True))
        self.line.track(self.particles, num_turns=num_turns, ele_start=ele_start, ele_stop=ele_stop, with_progress=with_progress)

    def generate_output(self, **kwargs):
        output_file = Path(kwargs.get("output_file"))
        if output_file.exists():
            raise ValueError(f"Output file {output_file} already exists!")
        if not output_file.parent.exists():
            output_file.parent.mkdir(parents=True)
        if output_file.suffix == '.json':
            import xobjects as xo
            with open(output_file, 'w') as fid:
                json.dump(self.particles.to_dict(), fid, cls=xo.JEncoder)
        elif output_file.suffix == '.parquet':
            with open(output_file, 'wb') as pf:
                (self.particles.to_pandas()).to_parquet(pf, index=True, engine="pyarrow")
