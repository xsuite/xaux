import json
import sys
import os
from pathlib import Path

import xobjects as xo
import xtrack as xt
import xpart as xp


class JobTemplate:
    # The class is a singleton
    def __new__(cls, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self, **kwargs):
        self._context = kwargs.get("_context", None)
        self.loading_line(**kwargs)
        particles = kwargs.get("particles", None)
        if isinstance(particles, xt.Particles):
            self._particles = particles
        elif isinstance(particles, (str, Path)):
            particles = Path(particles)
            if not particles.exists():
                raise ValueError(f"particles file {particles} does not exist!")
            if particles.suffix == '.json':
                with open(particles, 'r') as fid:
                    self._particles= xp.Particles.from_dict(json.load(fid), _context=self._context)
            elif particles.suffix == '.parquet':
                import pandas as pd
                with open(particles, 'rb') as fid:
                    self._particles = xp.Particles.from_pandas(pd.read_parquet(fid, engine="pyarrow"), _context=self._context)
            else:
                raise ValueError(f"Invalid particles file extension {particles.suffix}!")
        elif particles is not None:
            raise ValueError(f"Invalid particles type {type(particles)}")
        if hasattr(self, 'validate_kwargs'):
            self.validate_kwargs(**kwargs)

    def loading_line(self,**kwargs):
        line = kwargs.get("line", None)
        if isinstance(line, (str, Path)):
            line = Path(line)
            if not line.exists():
                raise ValueError(f"Line file {line} does not exist!")
            self._line = xt.Line.from_json(line, _context=self._context)
        elif isinstance(line, (xt.Line,xt.Multiline,xt.Environment)):
            self._line = line
        elif line is not None:
            raise ValueError(f"Invalid line type {type(line)}")

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
        if output_file.suffix == '.json':
            with open(output_file, 'w') as fid:
                json.dump(self.particles.to_dict(), fid, cls=xo.JEncoder)
        elif output_file.suffix == '.parquet':
            with open(output_file, 'wb') as pf:
                self.particles.to_parquet(pf, index=True, engine="pyarrow")



# Job template for Dynamic Aperture analysis
# ==========================================================================================
class DAJob(JobTemplate):
    def loading_line(self, **kwargs):
        if 'seed' in kwargs:
            seed = kwargs.get("seed")
            line = kwargs.get("line", None)
            if isinstance(line, (str, Path)):
                line = Path(line)
                if not line.exists():
                    raise ValueError(f"Line file {line} does not exist!")
                with open(line, 'r') as fid:
                    line = json.load(fid)
                self._line = xt.Line.from_dict(line[seed])
            elif isinstance(line, dict):
                if isinstance(line[seed], dict):
                    self._line = xt.Line.from_dict(line[seed])
                elif isinstance(line[seed], (xt.Line, xt.Multiline, xt.Environment)):
                    self._line = line[seed]
                else:
                    raise ValueError(f"Invalid seed line type {type(line['seed'])} for seed {seed}!")
            elif line is not None:
                raise ValueError(f"Invalid line type {type(line)}")
        else :
            super().loading_line(**kwargs)



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
        """
        This Class manages a list of jobs for tacking to be executed in parallel and their submission to HTCONDOR and BOINC.
        It can be loaded from its metadata file or created from scratch using the following parameters.

        Parameters
        ----------
        name : str
            Name of the job manager.
        work_directory : str or Path
            Directory where the job manager will store files necessary for the management.
        input_directory : str or Path
            Directory where the input files are stored.
        output_directory : str or Path
            Directory where the output files will be stored.
        job_class (optional) : class
            Class use to run the simulations. Default is JobTemplate.
        job_class_name (optional) : str
            Name of the class used to run the simulations.
        job_class_script (optional) : str or Path
            Path to the script where the class for the tracking is defined (if different from the current script).
        """
        if len(arg) == 1:
            self.read_metadata(arg[0])
            self.load_job_list()
            return
        elif len(arg) != 0:
            raise ValueError("Invalid number of arguments!")
        self._name = kwargs.get("name")
        self._work_directory  = Path(kwargs.get("work_directory"))
        if not self._work_directory.exists():
            self._work_directory.mkdir(parents=True)
        self._input_directory = Path(kwargs.get("input_directory")) if "input_directory" in kwargs else None
        if self._input_directory is not None and not self._input_directory.exists():
            raise ValueError(f"Input directory {self._input_directory} does not exist!")
        self._output_directory = Path(kwargs.get("output_directory",)) if "output_directory" in kwargs else None
        if self._output_directory is not None and not self._output_directory.exists():
            self._output_directory.mkdir(parents=True)
        self._job_class = kwargs.get("job_class", None)
        if self._job_class is None:
            self._job_class_name = None
            self._job_class_script = ""
        else:
            self._job_class_name = self._job_class.__name__
            self._job_class_script = os.path.abspath(sys.modules[self._job_class.__module__].__file__)
        if "job_class" not in kwargs:
            if"job_class_name" in kwargs and "job_class_script" in kwargs:
                self._job_class_name = kwargs["job_class_name"]
                self._job_class_script = kwargs.get("job_class_script")
                # # Import the job class TODO: Does not work
                # from importlib import import_module
                # self._job_class = import_module(self._job_class_name, package=self._job_class_script)
            else:
                raise ValueError("Either specify the class for the tracking using job_class or both job_class_name and job_class_script!")
        self._step = kwargs.get("step", 0)
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
    def work_directory(self):
        return self._work_directory

    @work_directory.setter
    def work_directory(self, path):
        self._work_directory = Path(path).resolve()

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

    @property
    def metafile(self):
        return self.work_directory / (self._name + '.meta.json')

    @property
    def job_management_file(self):
        return self.work_directory / (self._name + '.jobs.json')

    @property
    def job_input_directory(self):
        return self.work_directory / 'job_specific_input'

    @property
    def job_management_directory(self):
        return self.work_directory / 'job_management_directory'

    def to_dict(self):
        return {'name': self._name, 'work_directory': str(self.work_directory),
                'input_directory': str(self.input_directory), 'output_directory': str(self.output_directory), 
                'job_class_name': self._job_class_name, 'job_class_script': self._job_class_script, 'step': self._step}
    
    def from_dict(self, metadata):
        for kk, vv in metadata.items():
            setattr(self, "_"+kk, vv)
        # Import the job class
        from importlib import import_module
        self._job_class = import_module(self._job_class_script, package=self._job_class_name)

    def save_metadata(self):
        if not self.job_management_directory.exists():
            self.job_management_directory.mkdir(parents=True)
        with open(self.metafile, 'w') as fid:
            json.dump(self.to_dict(), fid, indent=True)

    def read_metadata(self, filename):
        with open(filename, 'r') as fid:
            metadata = json.load(fid)
        self.from_dict(metadata)

    def save_job_list(self):
        with open(self.job_management_file, 'w') as fid:
            json.dump(self._job_list, fid, indent=True)

    def load_job_list(self):
        if not self.job_management_file.exists():
            self._job_list = {}
        else:
            with open(self.job_management_file, 'r') as fid:
                self._job_list = json.load(fid)

    def add(self, *arg, **kwargs):
        self.load_job_list()
        process_job_name = False # True if job description is provided directly as a dictionary in kwargs or as a list of dictionaries in arg
        # If job description is provided as a list of dictionaries in arg
        if len(arg) != 0:
            ii0=len(self._job_list)+len(kwargs)
            for ii,job_description in enumerate(arg):
                if isinstance(job_description, dict):
                    kwargs[f"job{ii+ii0}"] = job_description
                else:
                    raise ValueError(f"Invalid description for job {ii}!")
        # If job description is provided directly as a dictionary in kwargs
        if any([kk in kwargs for kk in ['inputfiles', 'particles', 'parameters', 'outputfiles']]):
            kwargs = {f"job{len(self._job_list)}": kwargs}
            process_job_name = True
        # Check if jobs description is correct
        for kk,job_description in kwargs.items():
            lwrong_description = [kkjob for kkjob in job_description if kkjob not in ['inputfiles', 'particles', 'parameters', 'outputfiles']]
            # if any([kkjob not in ['inputfiles', 'particles', 'parameters', 'outputfiles'] for kkjob in job_description]):
            if len(lwrong_description) != 0:
                if process_job_name:
                    raise ValueError(f"Wrong job description: {lwrong_description}!")
                else:
                    raise ValueError(f"Wrong description for job named \"{kk}\": {lwrong_description}!")
        # Create the new jobs
        new_jobs_list = [self._job_creation(kk,job_description) for kk,job_description in kwargs.items()]
        # Add the new jobs to the job list
        new_jobs = {val[0]:val[1:] for new_job_list in new_jobs_list for val in new_job_list}
        self._job_list = {**self._job_list,**new_jobs} 
        self.save_job_list()

    def _job_creation(self, job_name, job_description) -> list:
        # Check if the line is a xobjects object and save it into a file
        if 'line' in job_description['inputfiles'] and isinstance(job_description['inputfiles']['line'], (xt.Line, xt.Multiline)):
            line = job_description['inputfiles']['line'].to_dict()
            filename = f"{self._name}.line.{job_name}.json"
            if not self.job_input_directory.exists():
                self.job_input_directory.mkdir(parents=True)
            with open(self.job_input_directory / filename, 'wb') as pf:
                json.dump(line, pf, cls=xo.JEncoder, indent=True)
            job_description['inputfiles']['line'] = str(self.job_input_directory / filename)
        # if 'nbsubdivision' in job_description['parameters']:
        #     nbsubdivision = job_description['parameters'].get('nbsubdivision')
        #     if 'particles' in job_description and 'nbparticles' in job_description['parameters']:
        #         raise ValueError("Both 'particles' and 'nbparticles' cannot be used together!")
        #     if 'particles' in job_description:
        #         particles = job_description.pop('particles')
        #         if isinstance(job_description['particles'], xp.Particles):
        #             particles = job_description['particles'].to_pandas()
        #         elif isinstance(job_description['particles'], pd.DataFrame):
        #             particles = job_description['particles']
        #         if isinstance(job_description['particles'],Path) or isinstance(job_description['particles'],str):
        #             import pandas as pd
        #             with open(job_description['particles'], 'rb') as pf:
        #                 particles = pd.read_parquet(pf, engine="pyarrow")
        #         if 'particle_id' not in particles.columns:
        #             particles['particle_id'] = particles.index
        #         nbparticles_per_subdivision = len(particles) // nbsubdivision
        #         new_list_jobs = [None for ii in range(nbsubdivision)]
        #         for ii in range(nbsubdivision):
        #             job_name_sub = f"{job_name}_sub{ii}"
        #             particles_sub = particles.iloc[ii*nbparticles_per_subdivision:(ii+1)*nbparticles_per_subdivision]
        #             particles_filename = f"{self._name}.particles.{job_name_sub}.parquet"
        #             self._make_particles_file(particles_filename, particles_sub)
        #             new_list_jobs[ii] = [job_name_sub, job_name, job_description.copy(), False, False]
        #             new_list_jobs[ii]['particles'] = str(self.job_input_directory / particles_filename)
        #     elif 'nbparticles' in job_description['parameters']:
        #         nbparticles = job_description['parameters'].get('nbparticles')
        #         nbparticles_per_subdivision = nbparticles // nbsubdivision
        #         new_list_jobs = [None for ii in range(nbsubdivision)]
        #         for ii in range(nbsubdivision):
        #             job_name_sub = f"{job_name}_sub{ii}"
        #             new_list_jobs[ii] = [job_name_sub, job_name, job_description.copy(), False, False]
        #             if nbparticles_per_subdivision*(ii+1) > nbparticles:
        #                 new_list_jobs[ii][0]['parameters']['nbparticles'] = nbparticles - nbparticles_per_subdivision*ii
        #             else:
        #                 new_list_jobs[ii][0]['parameters']['nbparticles'] = nbparticles_per_subdivision
        #     else:
        #         new_list_jobs = [None for ii in range(nbsubdivision)]
        #         for ii in range(nbsubdivision):
        #             job_name_sub = f"{job_name}_sub{ii}"
        #             new_list_jobs[ii] = [job_name_sub, job_name, job_description.copy(), False, False]
        #             if nbparticles_per_subdivision*(ii+1) > nbparticles:
        #                 new_list_jobs[ii][0]['parameters']['nbparticles'] = nbparticles - nbparticles_per_subdivision*ii
        #             else:
        #                 new_list_jobs[ii][0]['parameters']['nbparticles'] = nbparticles_per_subdivision
        #     return new_list_jobs
        # else:
        # Check if the particles are a xobjects object or a pandas DataFrame and save it into a file
        if 'particles' in job_description:
            import pandas as pd
            if isinstance(job_description['particles'], xp.Particles):
                particles = job_description['particles'].to_pandas()
                particles_filename = f"{self._name}-{job_name}.particles.parquet"
                job_description['particles'] = str(self._make_particles_file(particles_filename, particles))
            elif isinstance(job_description['particles'], pd.DataFrame):
                particles = job_description['particles']
                particles_filename = f"{self._name}-{job_name}.particles.parquet"
                job_description['particles'] = str(self._make_particles_file(particles_filename, particles))
        return [[job_name, job_description, False, False]]

    def _make_particles_file(self, filename, particles):
        if not self.job_input_directory.exists():
            self.job_input_directory.mkdir(parents=True)
        with open(self.job_input_directory / filename, 'wb') as pf:
            particles.to_parquet(pf, index=True, engine="pyarrow")
        return self.job_input_directory / filename

    def submit(self, platform='htcondor', **kwargs):
        if platform == 'htcondor':
            self._submit_htcondor(**kwargs)
        elif platform == 'boinc':
            self._submit_boinc(**kwargs)
        else:
            raise ValueError("Invalid platform! Use either 'htcondor' or 'boinc'!")

    def _submit_htcondor(self, job_list=None, **kwargs):
        import xdeps as xd
        import xfields as xf
        if 'xcoll' in sys.modules:
            import xcoll as xc
        if job_list is None:
            job_list = self._job_list.keys()
        # Check if the job list is valid
        assert any([job_name in self._job_list for job_name in job_list]), "Invalid job name!"
        # Check if the job is already submitted
        job_list = [job_name for job_name in job_list if not self._job_list[job_name][2]]
        if len(job_list) == 0:
            print("All jobs are already submitted!")
            return
        if not self.job_management_directory.exists():
            self.job_management_directory.mkdir(parents=True)
        # Check if jobs have the same structure
        for job_name in job_list:
            for kk in self._job_list[job_name][0]:
                assert kk in self._job_list[job_list[0]][0], "Jobs have different structures!"
                if isinstance(self._job_list[job_name][0][kk], dict):
                    for jj in self._job_list[job_name][0][kk]:
                        assert jj in self._job_list[job_list[0]][0][kk], "Jobs have different structures!"
        # Classify job arguments
        larguments  = {}
        luniqueargs = {}
        lmuliargs   = {}
        jn0 = job_list[0]
        if 'inputfiles' in self._job_list[jn0][0]:
            largs = self._job_list[jn0][0]['inputfiles']
            larguments = {**larguments,**largs}
            luniquetmp = {kk:vv for kk,vv in largs.items() if not any([self._job_list[jn][0]['inputfiles'][kk] != largs[kk] for jn in job_list])}
            lmulitmp   = {kk:vv for kk,vv in largs.items() if kk not in luniquetmp}
            luniqueargs= {**luniqueargs,**luniquetmp}
            lmuliargs  = {**lmuliargs,**lmulitmp}
        if 'particles' in self._job_list[jn0][0]:
            largs = {'particles':self._job_list[jn0][0]['particles']}
            larguments = {**larguments,**largs}
            if 'Step' in self._job_list[jn0][0]['parameters']:
                lmuliargs   = {**lmuliargs,  'particles':self._job_list[jn0][0]['particles']}
            else:
                luniqueargs = {**luniqueargs,'particles':self._job_list[jn0][0]['particles']}
        if 'parameters' in self._job_list[jn0][0]:
            largs = self._job_list[jn0][0]['parameters']
            larguments = {**larguments,**largs}
            luniquetmp = {kk:vv for kk,vv in largs.items() if not any([self._job_list[jn][0]['parameters'][kk] != largs[kk] for jn in job_list])}
            lmulitmp   = {kk:vv for kk,vv in largs.items() if kk not in luniquetmp}
            luniqueargs= {**luniqueargs,**luniquetmp}
            lmuliargs  = {**lmuliargs,**lmulitmp}
        if 'outputfiles' in self._job_list[jn0][0]:
            largs = self._job_list[jn0][0]['outputfiles']
            larguments = {**larguments,**largs}
            luniquetmp = {kk:vv for kk,vv in largs.items() if not any([self._job_list[jn][0]['outputfiles'][kk] != largs[kk] for jn in job_list])}
            lmulitmp   = {kk:vv for kk,vv in largs.items() if kk not in luniquetmp}
            luniqueargs= {**luniqueargs,**luniquetmp}
            lmuliargs  = {**lmuliargs,**lmulitmp}
        # Creation of htcondor executable file
        executable_file = self.work_directory / f"{self._name}.htcondor.sh"
        with open(executable_file, 'w') as fid:
            fid.write(f"#!/bin/bash\n\n")
            # Add arguments to the job
            for ii,kk in enumerate(lmuliargs):
                fid.write(kk+"=${"+str(ii+1)+"}\n")
            fid.write(f"\nset --\n\n")
            fid.write(f"sleep 60\n\n")
            # Load python environment
            fid.write(f"source /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh\n")
            fid.write(f"retVal=$?\n")
            fid.write(f"if [ $retVal -ne 0 ]\n")
            fid.write(f"then\n")
            fid.write(f'    echo "Failed to source LCG_106" # Catch source error to avoid endless loop\n')
            fid.write(f"    exit $retVal\n")
            fid.write(f"fi\n\n")
            # Copy Xsuite classes locally
            for xclass in [xo, xd, xt, xp, xf]:
                fid.write(f"cp -r {str(Path(xclass.__file__).parent)} .\n")  # Copy of main xobjects
            fid.write(f"cp -r {str(Path(sys.modules[JobTemplate.__module__].__file__).parent)} .\n") # Copy of xaux
            if 'xcoll' in sys.modules:
                fid.write(f"cp -r {str(Path(xc.__file__).parent)} .\n")      # Copy of xcoll if exists
            # Check local copy of the job input files
            fid.write('\necho "uname -r:" `uname -r\n')
            fid.write('python --version\n')
            fid.write('echo "which python:" `which python`\n')
            fid.write('echo "ls:"\n')
            fid.write('ls\n')
            fid.write('echo\n')
            fid.write('echo $( date )"    Running lossmap study ${studyname} job ${jobid}."\n')
            fid.write('echo\n')
            # # Create python argument for input files
            # linputfile_key  = job_description['inputfiles'].keys()
            # linputfile_path = job_description['inputfiles'].values()
            # linputfile_name = [Path(vv).name for vv in linputfile_path]
            # job_args = ' '.join([f"{kk}={nn}" for kk,nn in zip(linputfile_key,linputfile_name)])
            # if 'particles' in job_description:
            #     # Add particles to python argument
            #     job_args += f" particles={Path(job_description['particles']).name}"
            # if 'parameters' in job_description:
            #     # Add parameters to python argument
            #     job_args += ' '+' '.join([f"{kk}={vv}" for kk,vv in job_description['parameters'].items()])
            # if 'outputfiles' in job_description:
            #     # Add output files to python argument
            #     job_args += ' '+' '.join([f"{kk}={str(Path(vv).name)}" for kk,vv in job_description['outputfiles'].items()])
            # List arguments for the python script
            print(f"{larguments=}")
            print(f"{luniqueargs=}")
            print(f"{lmuliargs=}")
            job_args = ' '.join([f"'{kk}='"+"${"+kk+"}" if kk in lmuliargs else f"'{kk}={vv}'" for kk,vv in larguments.items()])
            # Execute python script
            fid.write(f"\npython xaux/jobmanager.py {self._job_class_name} {self._job_class_script} {job_args}\n")


        # Create main htcondor submission file
        with open(self.work_directory / f"{self._name}.htcondor.sub", 'w') as fid:
            fid.write(f"executable = {self.work_directory}/$(jobname).htcondor.sh\n")
            fid.write(f"output = $(jobname).htcondor.out\n")
            fid.write(f"error = $(jobname).htcondor.err\n")
            fid.write(f"log = $(jobname).htcondor.log\n")
            fid.write(f"should_transfer_files = YES\n")
            linputs = ''
            if len(luniqueargs)!=0:
                linputs += ','.join([vv for kk,vv in luniqueargs.items() if kk in self._job_list[jn0][0]['inputfiles']])
            if len(lmuliargs)!=0:
                linputs += '$('+'),$('.join([kk for kk in lmuliargs if kk in self._job_list[jn0][0]['inputfiles']])+')'
            fid.write(f"transfer_input_files = {linputs}\n")
            loutputs = ''
            if 'outputfiles' in self._job_list[jn0][0]:
                if len(luniqueargs)!=0:
                    for kk,vv in luniqueargs.items():
                        if kk in self._job_list[jn0][0]['outputfiles']:
                            vv = Path(vv)
                            vv = vv.parent / (vv.stem+'.$(job_name).'+vv.suffix)
                            loutputs += f"{vv},"
                if len(lmuliargs)!=0:
                    loutputs += '$('+'),$('.join([kk for kk in lmuliargs if kk in self._job_list[jn0][0]['outputfiles']])+')'
                fid.write(f"transfer_output_files = {loutputs}\n")
                fid.write(f"when_to_transfer_output = ON_EXIT\n")

            if len(lmuliargs)!=0:
                fid.write(f"arguments = $(job_name) $({') $('.join([kk for kk in lmuliargs])})\n")
                fid.write(f"queue job_name, {', '.join(lmuliargs)} from (\n")
                for job_name in job_list:
                    fid.write(f"    {job_name}")
                    if 'inputfiles' in self._job_list[job_name][0]:
                        for kk in [kk for kk in lmuliargs if kk in self._job_list[job_name][0]['inputfiles']]:
                            fid.write(f" {self._job_list[job_name][0]['inputfiles'][kk]}")
                    if 'particles' in self._job_list[job_name][0]:
                        fid.write(f" {self._job_list[job_name][0]['particles']}")
                    if 'parameters' in self._job_list[job_name][0]:
                        for kk in [kk for kk in lmuliargs if kk in self._job_list[job_name][0]['parameters']]:
                            fid.write(f" {self._job_list[job_name][0]['parameters'][kk]}")
                    if 'outputfiles' in self._job_list[job_name][0]:
                        for kk in [kk for kk in self._job_list[job_name][0]['outputfiles']]:
                            if kk in lmuliargs:
                                fid.write(f" {self._job_list[job_name][0]['outputfiles'][kk]}")
                            else:
                                vv = Path(self._job_list[job_name][0]['outputfiles'][kk])
                                vv = vv.parent / (vv.stem+'.$(job_name).'+vv.suffix)
                                fid.write(f" {vv}")
                    fid.write(f"\n")
                fid.write(f")\n")
            else:
                fid.write(f"queue\n")
        raise NotImplementedError("HTCONDOR submission not implemented yet!")

    def _submit_boinc(self, **kwargs):
        raise NotImplementedError("BOINC submission not implemented yet!")
        


arg = {
    'job0': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
    'job1': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
    'job2': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
}




def main(job_class_name, job_class_script, **arg):
        from importlib import import_module
        import time
        start_time = time.time()
        import xdeps as xd
        import xfields as xf
        if 'xcoll' in sys.modules:
            import xcoll as xc
        job_class = import_module(job_class_script, package=job_class_name)
        job_class.run(**arg)
        print(f"Total calculation time {time.time()-start_time:.2f}s")



if __name__ == '__main__':
    print("Test:")
    print(f"{DAJob.__name__=}")
    print(f"{os.path.abspath(sys.modules[DAJob.__module__].__file__)=}")
    print(f"{xt.Line.__name__=}")
    print(f"{os.path.abspath(sys.modules[xt.Line.__module__].__file__)=}")
    print(f"{str(Path(xt.__file__).parent)=}")
    print("end")

    # # Executable for the job class
    # main(sys.argv[1], # job_class_name 
    #      sys.argv[2], # job_class_script
    #      **dict(arg.split('=') for arg in sys.argv[3:]) # job arguments
    #      )