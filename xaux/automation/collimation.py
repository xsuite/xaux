# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import numpy as np
from pathlib import Path

if __name__ == "__main__":
    from xaux.automation.template import JobTemplate
else:
    from .template import JobTemplate


class LossMapPencilJob(JobTemplate):
    def validate_kwargs(self, **kwargs):
        if "colldb" not in kwargs:
            raise ValueError("No collimation database provided!")
        if "lmtype" not in kwargs:
            raise ValueError("No loss map type provided!")
        elif kwargs['lmtype'] not in ['B1H', 'B1V', 'B2H', 'B2V']:
            raise ValueError("Invalid loss map type!")
        lmtype = kwargs.pop('lmtype')
        self.beam = int(lmtype[1])
        self.plane = lmtype[2]
        if "num_particles" not in kwargs:
            raise ValueError("No number of particles provided!")

    def pre_build(self, **kwargs):
        import xcoll as xc
        self.colldb = xc.CollimatorDatabase.from_yaml(kwargs["colldb"], beam=self.beam)
        self.colldb.install_everest_collimators(line=self.line, verbose=True)
        print('\nAperture model check after introducing collimators:')
        df_with_coll = self.line.check_aperture()
        assert not np.any(df_with_coll.has_aperture_problem)

    def post_build(self, **kwargs):
        self.line.collimators.assign_optics()

    def generate_particles(self, **kwargs):
        tcp  = f"tcp.{'c' if self.plane=='H' else 'd'}6{'l' if f'{self.beam}'=='1' else 'r'}7.b{self.beam}"
        self.particles = self.line[tcp].generate_pencil(kwargs['num_particles'])

    def pre_track(self, **kwargs):
        self.line.scattering.enable()

    def post_track(self, **kwargs):
        import xcoll as xc
        self.line.scattering.disable()
        line_is_reversed = True if f'{self.beam}' == '2' else False
        self.ThisLM = xc.LossMap(self.line, line_is_reversed=line_is_reversed, part=self.particles)

    def generate_output(self, **kwargs):
        lossmap_file = kwargs.get("lossmap_file", None)
        if lossmap_file is None:
            lossmap_file = Path(f'lossmap_B{self.beam}{self.plane}.json')
        self.ThisLM.to_json(file=lossmap_file)
        summary_file = kwargs.get("summary_file", None)
        if summary_file is None:
            summary_file = Path(f'coll_summary_B{self.beam}{self.plane}.out')
        # Save a summary of the collimator losses to a text file
        self.ThisLM.save_summary(file=summary_file)
        print(self.ThisLM.summary)
