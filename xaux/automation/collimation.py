# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

from pathlib import Path

if __name__ == "__main__" or __name__ == "collimation":
    from xaux.automation.template import JobTemplate
else:
    from .template import JobTemplate
# try:
#     from .template import JobTemplate
# except ImportError:
#     from xaux.automation.template import JobTemplate


class LossMapPencilJob(JobTemplate):
    """Job to generate a loss map with a pencil beam.

    Parameters
    ----------
    line: Line | Path | str
        The Xsuite line to be tracked.
    colldb : CollimatorDatabase | Path | str
        Database with all collimators to be installed and their settings. If a
        path it should be in .yaml format.
    lmtype: {'B1H', 'B1V', 'B2H', 'B2V'}
        Loss map type, to specify the beam and plane for particle generation.
    num_particles: int
        Number of particles to generate.
    lossmap_file: Path | str | bool, optional
        Path to file to store the generated loss map result.
    summary_file: Path | str | bool, optional
        Path to file to store a summary of losses on collimators.
    """

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
        assert not any(df_with_coll.has_aperture_problem)

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
        if lossmap_file is None or lossmap_file is True:
            lossmap_file = Path(f'lossmap_B{self.beam}{self.plane}.json')
        if lossmap_file is not False:
            self.ThisLM.to_json(file=lossmap_file)
        summary_file = kwargs.get("summary_file", None)
        if summary_file is None or summary_file is True:
            summary_file = Path(f'coll_summary_B{self.beam}{self.plane}.out')
        if summary_file is not False:
            self.ThisLM.save_summary(file=summary_file)
        print(self.ThisLM.summary)
