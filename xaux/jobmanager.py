import json
import sys
import os
from pathlib import Path

import xtrack as xt
import xpart as xp
import xobjects as xo


class JobTemplate:
    # The class is a singleton
    def __new__(cls, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self, **kwargs):
        self._context = kwargs.get("_context", None)
        line = kwargs.get("line", None)
        if isinstance(line, (xt.Line,xt.MultiLine,xt.Environment)):
            self._line = line
        elif isinstance(line, (str, Path)):
            line = Path(line)
            if not line.exists():
                raise ValueError(f"Line file {line} does not exist!")
            self._line = xt.Line.from_json(line, _context=self._context)
        elif line is not None:
            raise ValueError(f"Invalid line type {type(line)}")
        particles = kwargs.get("particles", None)
        if isinstance(particles, xt.Particles):
            self._particles = particles
        elif isinstance(particles, (str, Path)):
            particles = Path(particles)
            if not particles.exists():
                raise ValueError(f"particles file {particles} does not exist!")
            with open(particles, 'r') as fid:
                self._particles= xp.Particles.from_dict(json.load(fid), _context=self._context)
        elif particles is not None:
            raise ValueError(f"Invalid particles type {type(particles)}")
        if hasattr(self, 'validate_kwargs'):
            self.validate_kwargs(**kwargs)

    @property
    def line(self):
        return self._line

    @property
    def particles(self):
        return self._particles

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
        num_turns = kwargs.get("num_turns", 1)
        ele_start = kwargs.get("ele_start", None)
        ele_stop = kwargs.get("ele_stop", None)
        self.line.track(self.particles, num_turns=num_turns, ele_start=ele_start, ele_stop=ele_stop)

    def generate_output(self, **kwargs):
        output_file = Path(kwargs.get("output_file"))
        if output_file.exists():
            raise ValueError(f"Output file {output_file} already exists!")
        if not output_file.parent.exists():
            output_file.parent.mkdir(parents=True)
        with open(output_file, 'w') as fid:
            json.dump(self.particles.to_dict(), fid, cls=xo.JEncoder)



# Job template for Dynamic Aperture analysis
# ==========================================================================================
DAJob = JobTemplate



# Job template for loss map calculation
# ==========================================================================================
if 'xcoll' in sys.modules:
    import xcoll as xc
    import numpy as np

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





# Job Manager
# ==========================================================================================
class JobManager:
    job_class = JobTemplate
    def __init__(self, *arg, **kwargs):
        if len(arg) == 1:
            self.read_metadata(arg[0])
            return
        elif len(arg) != 0:
            raise ValueError("Invalid number of arguments!")

        self._name = kwargs.get("name")
        self._input_directory = Path(kwargs.get("input_directory"))
        if not self._input_directory.exists():
            raise ValueError(f"Input directory {self._input_directory} does not exist!")

        self._output_directory = Path(kwargs.get("output_directory"))
        if not self._output_directory.exists():
            self._output_directory.mkdir(parents=True)

        self._job_class = kwargs.get("job_class", self.job_class, None)
        if self._job_class is None:
            self._job_class_name = None
            self._job_class_script = ""
        else:
            self._job_class_name = self._job_class.__name__
            self._job_class_script = os.path.abspath(sys.modules[self._job_class.__module__].__file__)

        if "job_class" not in kwargs and "job_class_name" in kwargs and "job_class_script" in kwargs:
            self._job_class_name = kwargs["job_class_name"]
            self._job_class_script = kwargs.get("job_class_script", "")
        else:
            raise ValueError("Either job_class or both job_class_name and job_class_script must be provided!")
        self.load_job_list()

    
    @property
    def job_class(self):
        return self._job_class


    @job_class.setter
    def job_class(self, job_class):
        self._job_class = job_class
        self._job_class_name = self._job_class.__name__
        self._job_class_script = os.path.abspath(sys.modules[self._job_class.__module__].__file__)


    @property
    def input_directory(self):
        return self._input_directory


    @input_directory.setter
    def input_directory(self, path):
        self._input_directory = Path(path).resolve()


    @property
    def output_directory(self):
        return self._output_directory


    @output_directory.setter
    def output_directory(self, path):
        self._output_directory = Path(path).resolve()


    # def set_lines(self, **kwargs):
    #     line_files = kwargs.get("line_files", None)


    @property
    def job_management_directory(self):
        return self.input_directory / 'job_management'


    @property
    def job_input_directory(self):
        return self.job_management_directory / 'job_specific_input'


    @property
    def metafile(self):
        return self.job_management_directory / self._name + '.meta.json'


    @property
    def job_management_file(self):
        return self.job_management_directory / self._name + '.jobs.json'
    

    def to_dict(self):
        return {'name': self._name,
                'input_directory': str(self.input_directory), 'output_directory': str(self.output_directory), 
                'job_class_name': self._job_class_name, 'job_class_script': self._job_class_script}


    def save_metadata(self):
        if not self.job_management_directory.exists():
            self.job_management_directory.mkdir(parents=True)
        with open(self.metafile, 'w') as fid:
            json.dump(self.to_dict(), fid)

    def read_metadata(self, filename):
        with open(filename, 'r') as fid:
            metadata = json.load(fid)
        for kk, vv in metadata.items():
            setattr(self, "_"+kk, vv)


    def load_job_list(self):
        if not self.job_management_file.exists():
            self._job_list = {}
        else:
            with open(self.job_management_file, 'r') as fid:
                self._job_list = json.load(fid)


    def save_job_list(self):
        with open(self.job_management_file, 'w') as fid:
            json.dump(self._job_list, fid)


    def add(self, *arg, **kwargs):
        self.load_job_list()
        process_job_name = False
        if len(arg) != 0:
            if len(arg) == 1 and isinstance(arg[0], dict) and len(kwargs) == 0:
                kwargs = arg[0]
            else:
                raise ValueError("Invalid arguments!")
        
        if any([kk in kwargs for kk in ['inputfiles', 'particles', 'parameters', 'outputfiles']]):
            kwargs = {f"job{len(self._job_list)}": kwargs}
            process_job_name = True

        for kk,job_description in kwargs.items():
            if any([kkjob not in ['inputfiles', 'particles', 'parameters', 'outputfiles'] for kkjob in job_description]):
                if process_job_name:
                    raise ValueError("Wrong job description!")
                else:
                    raise ValueError(f"Wrong description for job {kk}!")
                
        new_jobs_list = [self._job_creation(kk,job_description) for kk,job_description in kwargs.items()]
        new_jobs = {val[0]:val[1] for new_job_list in new_jobs_list for val in new_job_list}
        self._job_list = {**self._job_list,**new_jobs} 
        self.save_job_list()


    def _job_creation(self, job_name, job_description) -> list:
        if 'subdivision' in job_description['parameters']:
            subdivision = job_description['parameters'].pop('subdivision')

            if 'particles' in job_description:
                particles = job_description.pop('particles')
                if isinstance(particles,str):
                    particles = Path(particles)
                if isinstance(particles,Path):
                    import pandas as pd
                    with open(particles, 'rb') as pf:
                        particles = pd.read_parquet(pf, engine="pyarrow")

            raise NotImplementedError("Subdivision of particles not implemented yet!")
            
            

        else:
            if 'particles' in job_description and isinstance(job_description['particles'], xp.Particles):
                particules_filename = f"{self._name}.particles.{job_name}.parquet"
                self._make_particles_file(particules_filename, job_description['particles'])

                if 'inputfiles' in job_description:
                    job_description['inputfiles'] = {**job_description['inputfiles'], 'particles': str(self.job_input_directory /particules_filename)}
                else:
                    job_description['inputfiles'] = {'particles': str(self.job_input_directory /particules_filename)}

            return [[job_name, job_description]]
                

    def _make_particles_file(self, filename, particles):
        if not self.job_input_directory.exists():
            self.job_input_directory.mkdir(parents=True)
        with open(self.job_input_directory / filename, 'wb') as pf:
            particles.to_parquet(pf, index=True, engine="pyarrow")
        


arg = {
    'job0': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
    'job1': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
    'job2': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
}
            



if __name__ == '__main__':
    print("Test:")
    print(f"{DAJob.__name__=}")
    print(f"{os.path.abspath(sys.modules[DAJob.__module__].__file__)=}")
    print(f"{xt.Line.__name__=}")
    print(f"{os.path.abspath(sys.modules[xt.Line.__module__].__file__)=}")
    print("end")