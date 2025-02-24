# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2025.                 #
# ######################################### #

import sys
import json
import subprocess
import numpy as np
import pandas as pd
from pathlib import Path

from .template import JobTemplate


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
            # Load the job manager from its metadata file
            self.read_metadata(arg[0])
            self.read_job_list()
            return
        elif len(arg) == 2:
            # Set the job manager main parameters
            self._name = arg[0]
            self._work_directory  = Path(arg[0]).resolve()
        elif len(arg) != 0:
            raise ValueError("Invalid number of arguments!")
        # Set the job manager main parameters
        if "name" in kwargs:
            self._name = kwargs.pop("name")
        if "work_directory" in kwargs:
            self._work_directory  = Path(kwargs.pop("work_directory")).resolve()
        if not self._work_directory.exists():
            self._work_directory.mkdir(parents=True)
        # Check if the job manager is already created
        if (self._work_directory / (self._name + '.jobmanager.meta.json')).exists():
            self.read_metadata(self._work_directory / (self._name + '.jobmanager.meta.json'))
            self.read_job_list()
            if len(kwargs) == 0:
                return
        # Set default input directory
        self._input_directory = Path(kwargs.pop("input_directory")) if "input_directory" in kwargs else None
        if self._input_directory is not None:
            if not self._input_directory.exists():
                raise ValueError(f"Input directory {self._input_directory} does not exist!")
            self._input_directory = self._input_directory.resolve()
        # Set utput directory
        self._output_directory = Path(kwargs.pop("output_directory", self._work_directory / 'output'))
        if not self._output_directory.exists():
            self._output_directory.mkdir(parents=True)
        self._output_directory = self._output_directory.resolve()
        # Set the job class for the tracking
        if "job_class" in kwargs:
            self._job_class = kwargs.pop("job_class", None)
            if self._job_class is None:
                self._job_class_name = None
                self._job_class_script = ""
            else:
                self._job_class_name = self._job_class.__name__
                self._job_class_script = Path(sys.modules[self._job_class.__module__].__file__).absolute()
        else:
            if"job_class_name" in kwargs and "job_class_script" in kwargs:
                self._job_class_name   = kwargs.pop("job_class_name")
                self._job_class_script = kwargs.pop("job_class_script")
                # # Import the job class TODO: Does not work
                # from importlib import import_module
                # self._job_class = import_module(self._job_class_name, package=self._job_class_script)
            else:
                raise ValueError("Either specify the class for the tracking using job_class or both job_class_name and job_class_script!")
        self._step = kwargs.get("step", 1)
        self._main_python_env = kwargs.get("main_python_env", "/cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh")
        self.save_metadata()
        self.read_job_list()

    @property
    def step(self):
        if self._step > 0:
            return self._step
        else:
            raise ValueError("Invalid step value!")

    @step.setter
    def step(self, step):
        self._step = step

    @property
    def main_python_env(self):
        return self._main_python_env

    @main_python_env.setter
    def main_python_env(self, main_python_env):
        self._main_python_env = main_python_env

    @property
    def job_class(self):
        return self._job_class

    @job_class.setter
    def job_class(self, job_class):
        self._job_class = job_class
        self._job_class_name = self._job_class.__name__
        self._job_class_script = Path(sys.modules[self._job_class.__module__].__file__).absolute()

    @property
    def work_directory(self):
        return Path(self._work_directory)

    @work_directory.setter
    def work_directory(self, path: Path|str):
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True)
        self._work_directory = str(path.resolve())

    @property
    def input_directory(self):
        return Path(self._input_directory)

    @input_directory.setter
    def input_directory(self, path: Path|str|None):
        if path is None:
            self._input_directory = None
        else:
            path = Path(path).resolve()
            if not path.exists():
                raise ValueError(f"Input directory {path} does not exist!")
            self._input_directory = str(path)

    @property
    def output_directory(self):
        return Path(self._output_directory)

    @output_directory.setter
    def output_directory(self, path: Path|str):
        path = Path(path)
        if not Path(path).exists():
            Path(path).mkdir(parents=True)
        self._output_directory = str(Path(path).resolve())

    @property
    def metafile(self):
        return self.work_directory / (self._name + '.jobmanager.meta.json')

    @property
    def job_management_file(self):
        return self.work_directory / (self._name + '.jobmanager.jobs.json')

    @property
    def job_specific_input_directory(self):
        return self.work_directory / 'job_specific_input'

    def to_dict(self):
        return {'name': self._name, 'work_directory': str(self.work_directory),
                'input_directory': str(self.input_directory), 'output_directory': str(self.output_directory), 
                'job_class_name': str(self._job_class_name), 'job_class_script': str(self._job_class_script), 'step': self._step}

    def from_dict(self, metadata):
        for kk, vv in metadata.items():
            setattr(self, "_"+kk, vv)
        # Import the job class
        # TODO: Find how to import the class from the script
        # from importlib import import_module
        # self._job_class = import_module(self._job_class_script, package=self._job_class_name)

    def save_metadata(self):
        if not self.work_directory.exists():
            self.work_directory.mkdir(parents=True)
        with open(self.metafile, 'w') as fid:
            json.dump(self.to_dict(), fid, indent=True, sort_keys=False)

    def read_metadata(self, filename):
        with open(filename, 'r') as fid:
            metadata = json.load(fid)
        self.from_dict(metadata)

    def save_job_list(self):
        with open(self.job_management_file, 'w') as fid:
            json.dump(self._job_list, fid, indent=True, sort_keys=False)

    def read_job_list(self):
        if not self.job_management_file.exists():
            self._job_list = {}
        else:
            with open(self.job_management_file, 'r') as fid:
                self._job_list = json.load(fid)

    def add(self, *arg, **kwargs):
        self.read_job_list()
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
        if any([kk in kwargs for kk in ['inputfiles', 'parameters', 'outputfiles']]):
            kwargs = {f"job{len(self._job_list)}": kwargs}
            process_job_name = True
        # Check if jobs description is correct
        for kk,job_description in kwargs.items():
            lwrong_description = [kkjob for kkjob in job_description if kkjob not in ['inputfiles', 'parameters', 'outputfiles']]
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
        import xtrack as xt
        if not self.job_specific_input_directory.exists():
            self.job_specific_input_directory.mkdir(parents=True)
        # Fix input files format in order to have only strings and save the data in files if needed
        for kk,vv in job_description['inputfiles'].items():
            if isinstance(vv, (xt.Line, xt.Multiline)):
                # If it is a line object and save it into a file
                data   = vv.to_dict()
                suffix = '.json'
            elif isinstance(vv, xt.Particles):
                # If it is a particles object and save it into a file
                data   = vv.to_pandas()
                suffix = '.parquet'
            elif isinstance(vv, (pd.DataFrame, np.ndarray)):
                # If it is a pandas DataFrame and save it into a file
                data   = pd.DataFrame(vv)
                suffix = '.parquet'
            elif isinstance(vv, dict):
                suffix = '.json'
                # If it is a dictionary and save it into a file
                if isinstance(vv[list(vv.keys())[0]], (xt.Line, xt.Multiline, xt.Particles)):
                    # If the dictionary contains a line or particles object, transform those line into dict
                    data = {}
                    for kkk, in vv.keys():
                        data[kkk] = vv[kkk].to_dict()
                else:
                    data = vv
            elif isinstance(vv, (Path, str)):
                # If it is a Path or a str, check if it exist directly or in input_directory and resolve the path
                file = Path(vv)
                if file.exists():
                    job_description['inputfiles'][kk] = str(file.resolve())
                elif self.input_directory is not None and (self.input_directory / file).exists():
                    job_description['inputfiles'][kk] = str((self.input_directory / file).resolve())
                else:
                    raise ValueError(f"\"{kk}\": {file} could not be found directly nor in the selected input directory!")
                continue
            else:
                raise ValueError(f"Type variable not supported for \"{kk}\": {type(vv)}")
            # Save the data in job_specific_input_directory
            new_filename = (self.job_specific_input_directory / f"{self._name}.{job_name}.{kk}{suffix}").resolve()
            if suffix == '.json':
                import xobjects as xo
                with open(new_filename, 'wb') as pf:
                    json.dump(data, pf, cls=xo.JEncoder, indent=True, sort_keys=False)
            elif suffix == '.parquet':
                with open(new_filename, 'wb') as pf:
                    data.to_parquet(pf, index=True, engine="pyarrow")
            job_description['inputfiles'][kk] = str(new_filename)
        return [[job_name, job_description, False, False, False]] # job_name, job_description, submitted, finished, returned

    def submit(self, platform='htcondor', **kwargs):
        if platform == 'htcondor':
            self._submit_htcondor(**kwargs)
        elif platform == 'boinc':
            self._submit_boinc(**kwargs)
        else:
            raise ValueError("Invalid platform! Use either 'htcondor' or 'boinc'!")

    def _submit_htcondor(self, auto: bool=False, **kwargs):
        # Check kwargs
        if 'step' in kwargs:
            self.step = kwargs.pop('step')
            self.save_metadata()
        import xdeps as xd
        import xfields as xf
        if 'xcoll' in sys.modules:
            import xcoll as xc # type: ignore
        job_list = self._job_list.keys()
        # Check if the job list is valid
        assert any([job_name in self._job_list for job_name in job_list]), "Invalid job name!"
        # Check if the job is already submitted
        job_list = [job_name for job_name in job_list if not self._job_list[job_name][1]]
        if len(job_list) == 0:
            print("All jobs are already submitted!")
            return
        # Check if jobs have the same structure
        for job_name in job_list:
            for kk in self._job_list[job_name][0]:
                assert kk in self._job_list[job_list[0]][0], "Jobs have different structures!"
                if isinstance(self._job_list[job_name][0][kk], dict):
                    for jj in self._job_list[job_name][0][kk]:
                        assert jj in self._job_list[job_list[0]][0][kk], "Jobs have different structures!"
        # Classify job arguments between the ones with unique values and the ones with different values between jobs
        lunique_inputfiles  = {}; lmulti_inputfiles  = {}
        lunique_parameters  = {}; lmulti_parameters  = {}
        lunique_outputfiles = {}; lmulti_outputfiles = {}
        jn0 = job_list[0]
        if 'inputfiles' in self._job_list[jn0][0]:
            largs = self._job_list[jn0][0]['inputfiles']
            lunique_inputfiles = {kk:vv for kk,vv in largs.items() if not any([self._job_list[jn][0]['inputfiles'][kk] != largs[kk] for jn in job_list[1:]])}
            lmulti_inputfiles  = {kk:vv for kk,vv in largs.items() if kk not in lunique_inputfiles}
        if 'parameters' in self._job_list[jn0][0]:
            largs = self._job_list[jn0][0]['parameters']
            lunique_parameters = {kk:vv for kk,vv in largs.items() if not any([self._job_list[jn][0]['parameters'][kk] != largs[kk] for jn in job_list[1:]])}
            lmulti_parameters  = {kk:vv for kk,vv in largs.items() if kk not in lunique_parameters}
        if 'outputfiles' in self._job_list[jn0][0]:
            largs = self._job_list[jn0][0]['outputfiles']
            lunique_outputfiles = {kk:vv for kk,vv in largs.items() if not any([self._job_list[jn][0]['outputfiles'][kk] != largs[kk] for jn in job_list[1:]])}
            lmulti_outputfiles  = {kk:vv for kk,vv in largs.items() if kk not in lunique_outputfiles}
        # Creation of htcondor executable file
        executable_file = self.work_directory / f"{self._name}.htcondor.sh"
        with open(executable_file, 'w') as fid:
            fid.write(f"#!/bin/bash\n\n")
            # Add arguments to the job
            fid.write("job_name=${1};\n")
            fid.write("Step=${2};\n")
            for ii,kk in enumerate({**lmulti_inputfiles,**lmulti_parameters,**lmulti_outputfiles}):
                fid.write(kk+"=${"+str(ii+3)+"};\n")
            fid.write(f"\nset --;\n\n")
            fid.write(f"sleep 60;\n\n")
            # Load python environment
            fid.write(f"source {Path(self.main_python_env)};\n")
            fid.write(f"retVal=$?;\n")
            fid.write(f"if [ $retVal -ne 0 ];\n")
            fid.write(f"then\n")
            fid.write(f'    echo "Failed to source LCG_106"; # Catch source error to avoid endless loop\n')
            fid.write(f"    exit $retVal;\n")
            fid.write(f"fi\n\n")
            # Copy Xsuite classes locally
            import xobjects as xo
            import xdeps as xd
            import xtrack as xt
            import xpart as xp
            import xfields as xf
            for xclass in [xo, xd, xt, xp, xf]:
                fid.write(f"cp -r {str(Path(xclass.__file__).parent)} .;\n")  # Copy of main xobjects
            fid.write(f"cp -r {str(Path(sys.modules[JobTemplate.__module__].__file__).parent)} .;\n") # Copy of xaux
            if 'xcoll' in sys.modules:
                fid.write(f"cp -r {str(Path(xc.__file__).parent)} .;\n")      # Copy of xcoll if exists
            # Copy input files locally
            fid.write(f"\ncp {self._job_class_script} .;\n") # TODO: pass this to htcondor submission file
            # Check local copy of the job input files
            fid.write('\necho "uname -r:" `uname -r`;\n')
            fid.write('python --version;\n')
            fid.write('echo "which python:" `which python`;\n')
            fid.write('echo "ls:";\n')
            fid.write('ls;\n')
            fid.write('echo;\n')
            fid.write('echo $( date )"    Running job ${job_name}.";\n')
            fid.write('echo;\n')
            # List arguments for the python script
            job_args  = [f"{kk}='"+"${"+kk+"}'" for kk in lmulti_inputfiles]
            job_args += [f"{kk}='{Path(vv).name}'" for kk,vv in lunique_inputfiles.items()]
            job_args += [f"{kk}='"+"${"+kk+"}'" for kk in lmulti_parameters]
            job_args += [f"{kk}='{vv}'" for kk,vv in lunique_parameters.items()]
            job_args += [f"{kk}='"+"${"+kk+"}'" for kk in lmulti_outputfiles]
            job_args += [f"{kk}='"+str(vv)+"'" for kk,vv in lunique_outputfiles.items()]
            job_args = ", ".join(job_args)
            # Execute python script
            fid.write(f"\npython -c \"from {self._job_class_script.stem} import {self._job_class_name}; {self._job_class_name}.run({job_args})\";\n")
            # last steps
            fid.write('\necho;\n')
            fid.write('echo $( date )"    End job ${job_name}.";\n')
            fid.write('echo "ls:";\n')
            fid.write('ls;\n')
            # Copy the outputs into the output directory
            if len(lmulti_outputfiles) != 0 or len(lunique_outputfiles) != 0:
                # TODO: check if possible to do this automatically with htcondor
                out_args  = ["${"+kk+"}" for kk in lmulti_outputfiles]
                out_args += [str(vv) for vv in lunique_outputfiles.values()]
                out_args  = " ".join(out_args)
                if self.step > 0:
                    job_output_directory = self.output_directory / (self._name+'.htcondor.${job_name}.${Step}')
                else:
                    job_output_directory = self.output_directory / (self._name+'.htcondor.${job_name}.0')
                fid.write(f"\ncp {out_args} {job_output_directory}/;\n")
                #     fid.write(f"\ncp {out_args} {self.output_directory / (self._name+'.htcondor.${job_name}.${Step}')}/;\n")
                # else:
                #     fid.write(f"\ncp {out_args} {self.output_directory / (self._name+'.htcondor.${job_name}.0')}/;\n")
                fid.write('\necho "ls output_dir:";\n')
                fid.write(f'ls {job_output_directory};\n')
            fid.write('exit 0;\n')
        # Create output job directory and clean it if not empty
        for job_name in job_list:
            if self.step > 0 :
                for ss in range(self.step):
                    job_output_directory = self.output_directory / (self._name+f'.htcondor.{job_name}.{ss}')
                    if not job_output_directory.exists():
                        job_output_directory.mkdir(parents=True)
                    else:
                        list_inside_job_output_directory = list(job_output_directory.glob('*'))
                        if len(list_inside_job_output_directory) != 0:
                            raise FileExistsError(f"Output directory {job_output_directory} is not empty!")
                        #     for ff in list_inside_job_output_directory:
                        #         if ff.is_dir():
                        #             raise ValueError(f"Output directory {job_output_directory} is not empty!")
                        #         else:
                        #             ff.unlink()
            else:
                job_output_directory = self.output_directory / (self._name+f'.htcondor.{job_name}.0')
                if not job_output_directory.exists():
                    job_output_directory.mkdir(parents=True)
                else:
                    list_inside_job_output_directory = list(job_output_directory.glob('*'))
                    if len(list_inside_job_output_directory) != 0:
                        raise FileExistsError(f"Output directory {job_output_directory} is not empty!")
                    #     for ff in list_inside_job_output_directory:
                    #         if ff.is_dir():
                    #             raise ValueError(f"Output directory {job_output_directory} is not empty!")
                    #         else:
                    #             ff.unlink()

        # Create main htcondor submission file
        with open(self.work_directory / f"{self._name}.htcondor.sub", 'w') as fid:
            # Set general parameters
            fid.write(f"universe           = {kwargs.pop('universe','vanilla')}\n")
            fid.write(f"executable         = {self.work_directory / (self._name+'.htcondor.sh')}\n")
            fid.write(f"output_destination = {self.output_directory / (self._name+'.htcondor.$(job_name).$(Step)')}\n")
            fid.write(f"output             = {self.output_directory / (self._name+'.htcondor.$(job_name).$(Step)') / (self._name+'.htcondor.$(ClusterId).$(ProcId).$(job_name).$(Step).out')}\n")
            fid.write(f"error              = {self.output_directory / (self._name+'.htcondor.$(job_name).$(Step)') / (self._name+'.htcondor.$(ClusterId).$(ProcId).$(job_name).$(Step).err')}\n")
            fid.write(f"log                = {self.output_directory / (self._name+'.htcondor.$(job_name).$(Step)') / (self._name+'.htcondor.$(ClusterId).$(ProcId).$(job_name).$(Step).log')}\n")
            # Set general parameters
            fid.write(f"batch_name         = {self._name}\n")
            fid.write(f"on_exit_remove     = {kwargs.pop('on_exit_remove','(ExitBySignal == False) && (ExitCode == 0)')}\n")
            fid.write(f"requirements       = {kwargs.pop('requirements','Machine =!= LastRemoteHost')}\n")
            fid.write(f"max_retries        = {kwargs.pop('max_retries',3)}\n")
            fid.write(f"max_materialize    = {kwargs.pop('max_materialize',100)}\n")
            fid.write(f"notification       = {kwargs.pop('notification','error')}\n")
            # Allowed JobFlavors: espresso, microcentury, longlunch, workday, tomorrow, testmatch, nextweek
            fid.write(f"MY.JobFlavour      = \"{kwargs.pop('JobFlavor','tomorrow')}\"\n")
            fid.write(f"MY.AccountingGroup = \"{kwargs.pop('accounting_group','group_u_BE.ABP.normal')}\"\n")
            # Set additional parameters
            for kk,vv in kwargs.items():
                fid.write(f"{kk} = {vv}\n")
            # Set input files transfer
            fid.write(f"should_transfer_files = YES\n")
            linputs = ''
            linputs += ', '.join([vv for vv in lunique_inputfiles.values()])
            if len(lmulti_inputfiles) != 0:
                linputs += ', ' if (len(linputs) != 0) else ''
                linputs += '$('+'), $('.join([f"{kk}_full" for kk in lmulti_inputfiles])+')'
            fid.write(f"transfer_input_files    = {linputs}\n")
            # Set output files transfer
            loutputs = ''
            if 'outputfiles' in self._job_list[jn0][0]:
                # TODO: fix file transfer to output directory
                # loutputs += ', '.join([vv for vv in lunique_outputfiles.values()])
                # if len(lmulti_outputfiles) != 0:
                #     loutputs += '$('+'),$('.join([kk for kk in lmulti_outputfiles])+')'
                # fid.write(f"transfer_output_files   = {loutputs}\n")
                fid.write(f"when_to_transfer_output = ON_EXIT\n")
            # Create the list of arguments and the queue
            section_arguments = "arguments = $(job_name) $(Step)"
            section_queue_name = "job_name"
            section_queue_list = ""
            if len(lmulti_inputfiles) != 0:
                section_arguments  += ' $(' + ') $('.join([f'{kk}_name' for kk in lmulti_inputfiles]) + ')'
                section_queue_name += ', ' + ', '.join([f'{kk}_full, {kk}_name' for kk in lmulti_inputfiles])
            if len(lmulti_parameters) != 0:
                section_arguments  += ' $(' + ') $('.join([kk for kk in lmulti_parameters]) + ')'
                section_queue_name += ', ' + ', '.join([kk for kk in lmulti_parameters])
            if len(lmulti_outputfiles) != 0:
                section_arguments  += ' $(' + ') $('.join([kk for kk in lmulti_outputfiles]) + ')'
                section_queue_name += ', ' + ', '.join([kk for kk in lmulti_outputfiles])
            for job_name in job_list:
                section_queue_list +=f"    {job_name}"
                for kk in lmulti_inputfiles:
                    vv = Path(self._job_list[job_name][0]['inputfiles'][kk])
                    section_queue_list +=f"    {vv.resolve()}    {vv.name}"
                for kk in lmulti_parameters:
                    section_queue_list +=f"    {self._job_list[job_name][0]['parameters'][kk]}"
                for kk in lmulti_outputfiles:
                    section_queue_list +=f"    {self._job_list[job_name][0]['outputfiles'][kk]}"
                section_queue_list +=f"\n"
            fid.write(f"{section_arguments}\n")
            fid.write(f"queue {self.step} {section_queue_name} from (\n")
            fid.write(f"{section_queue_list})\n")
        # Submit the jobs to HTCONDOR
        if auto:
            print(f"Submit: `condor_submit {self.work_directory / (self._name+'.htcondor.sub')}`")
            subprocess.check_output(['condor_submit', str(self.work_directory / (self._name+'.htcondor.sub')) ])
            print(f"Submit done.")
        else:
            print(f"please run: `condor_submit {self.work_directory / (self._name+'.htcondor.sub')}`")
        # Update the job list
        for job_name in job_list:
            self._job_list[job_name][1] = True
        self.save_job_list()

    def _submit_boinc(self, **kwargs):
        raise NotImplementedError("BOINC submission not implemented yet!")
    
    def status(self, platform='htcondor', job_list=None, **kwargs):
        if platform == 'htcondor':
            self._status_htcondor(job_list, **kwargs)
        elif platform == 'boinc':
            self._status_boinc(job_list, **kwargs)
        else:
            raise ValueError("Invalid platform! Use either 'htcondor' or 'boinc'!")
        
    def _status_htcondor(self, **kwargs):
        self.read_job_list()
        job_list = self._job_list.keys()
        # Check if the job list is valid
        assert any([job_name in self._job_list for job_name in job_list]), "Invalid job name!"
        # Check if submission still running
        similation_status = subprocess.run(['condor_q'], stdout=subprocess.PIPE).stdout.decode('utf-8')
        still_running = (self._name in similation_status)
        if not still_running:
            similation_status_lines = similation_status.split('\n')[3:-6]
            similation_status_lines = [line.split() for line in similation_status_lines]
            header = similation_status_lines[0]
            similation_status_lines = [line for line in similation_status_lines[1:] if self._name in line][0]
            status_htcondor = {hh:ss for hh,ss in zip(header,similation_status_lines)}
            for kk,vv in status_htcondor.items():
                status_htcondor[kk] = '0' if (vv == "_") else vv
            done = status_htcondor.pop('DONE', '0')
            run  = status_htcondor.pop('RUN',  '0')
            idle = status_htcondor.pop('IDLE', '0')
            hold = status_htcondor.pop('HOLD', '0')
            total= status_htcondor.pop('TOTAL','0')
            print(f"{self._name} is still running (Done: {done} / Run: {run} / Idle: {idle} / Hold: {hold} / Total: {total})!")
        else:
            print(f"{self._name} is not running!")
        # Check the status of the jobs
        for job_name in job_list:
            # Check the status of the job
            job_description = self._job_list[job_name]
            if job_description[1]:
                if 'outputfiles' in job_description[0]:
                    if not job_description[2]:
                        all_outputfiles_present = True
                        for ff in job_description[0]['outputfiles']:
                            if self.step > 0:
                                for ss in range(self.step):
                                    # TODO: Add output directory check
                                    if not (self.output_directory / (self._name+f'.htcondor.{job_name}.{ss}') / ff).exists():
                                        all_outputfiles_present = False
                            else:
                                if not (self.output_directory / (self._name+f'.htcondor.{job_name}.0') / ff).exists():
                                    all_outputfiles_present = False
                        self._job_list[job_name] = all_outputfiles_present
                    print(f"   - Job {job_name} is {'not ' if not self._job_list[job_name][2] else ''}completed!")
                else:
                    all_outputfiles_present = True
                    if self.step > 0:
                        for ss in range(self.step):
                            ff = (self._name+'.htcondor.*.*.{job_name}.{ss}.out')
                            list_ff = list((self.output_directory / (self._name+f'.htcondor.{job_name}.{ss}')).glob(ff))
                            # TODO: Add output directory check
                            if len(list_ff) == 0:
                                all_outputfiles_present = False
                            elif len(list_ff) > 1:
                                raise ValueError(f"Multiple output files found for job {job_name}:\n{list_ff}")
                    else:
                        ff = (self._name+'.htcondor.*.*.{job_name}.0.out')
                        list_ff = list((self.output_directory / (self._name+f'.htcondor.{job_name}.0')).glob(ff))
                        # TODO: Add output directory check
                        if len(list_ff) == 0:
                            all_outputfiles_present = False
                        elif len(list_ff) > 1:
                            raise ValueError(f"Multiple output files found for job {job_name}:\n{list_ff}")
                    self._job_list[job_name] = all_outputfiles_present
                    print(f"   - Job {job_name} is {'not ' if not self._job_list[job_name][2] else ''}completed!")
            else:
                print(f"   - Job {job_name} is not submitted!")
        self.save_job_list()
        
    def _status_boinc(self, **kwargs):
        raise NotImplementedError("BOINC status not implemented yet!")
    
    def retrieve(self, platform='htcondor', job_list=None, **kwarg):
        if platform == 'htcondor':
            return self._retrieve_htcondor(job_list, **kwarg)
        elif platform == 'boinc':
            return self._retrieve_boinc(job_list, **kwarg)
        else:
            raise ValueError("Invalid platform! Use either 'htcondor' or 'boinc'!")
        
    def _retrieve_htcondor(self, job_list=None, **kwarg):
        self.read_job_list()
        if job_list is None:
            job_list = self._job_list.keys()
        # Check if the job list is valid
        assert any([job_name in self._job_list for job_name in job_list]), "Invalid job name!"
        # Check if submission still running
        similation_status = subprocess.run(['condor_q'], stdout=subprocess.PIPE).stdout.decode('utf-8')
        if self._name in similation_status:
            print(f"WARNING: {self._name} is still running! Wait for the end of the simulation before retrieving the results!")
        # Retrieve the results of the jobs
        if 'outputfiles' in self._job_list[list(self._job_list.keys())[0]][0]:
            results = {kk:self._job_list[kk][0]['outputfiles'] for kk in job_list if self._job_list[kk][1] and self._job_list[kk][2]}
            for job_name in results:
                for kk,ff in results[job_name].items():
                    if self.step > 0:
                        results[job_name][kk] = [None for _ in range(self.step)]
                        for ss in range(self.step):
                            results[job_name][kk][ss] = (self.output_directory / (self._name+f'.htcondor.{job_name}.{ss}') / ff)
                    else:
                        results[job_name][kk] = (self.output_directory / (self._name+f'.htcondor.{job_name}.0') / ff)
                self._job_list[job_name][3] = True
        else:
            results = {kk:[None for _ in range(self.step)] for kk in job_list if self._job_list[kk][1] and self._job_list[kk][2]}
            for job_name in results:
                if self.step > 0:
                    for ss in range(self.step):
                        ff = (self._name+'.htcondor.*.*.{job_name}.{ss}.out')
                        results[job_name][ss] = list((self.output_directory / (self._name+f'.htcondor.{job_name}.{ss}')).glob(ff))
                else:
                    ff = (self._name+'.htcondor.*.*.{job_name}.0.out')
                    results[job_name][0] = list((self.output_directory / (self._name+f'.htcondor.{job_name}.0')).glob(ff))
                self._job_list[job_name][3] = True
        # List missing results
        missing_results = [kk for kk in job_list if kk not in results]
        if len(missing_results) != 0:
            print(f"Missing results for the following jobs: {missing_results}")
        return results
    
    def _retrieve_boinc(self, job_list=None, **kwarg):
        raise NotImplementedError("BOINC retrieval not implemented yet!")

    def clean(self, platform='htcondor', job_list=None, **kwarg):
        if platform == 'htcondor':
            self._clean_htcondor(job_list, **kwarg)
        elif platform == 'boinc':
            self._clean_boinc(job_list, **kwarg)
        else:
            raise ValueError("Invalid platform! Use either 'htcondor' or 'boinc'!")

    def _clean_htcondor(self, job_list=None, **kwarg):
        self.read_job_list()
        if job_list is None:
            job_list = self._job_list.keys()
        # Check if the job list is valid
        assert any([job_name in self._job_list for job_name in job_list]), "Invalid job name!"
        # Remove unfinished jobs from the list
        job_list = [job_name for job_name in job_list if self._job_list[job_name][2]]
        # Remove jobs from main list and remove files
        for job_name in job_list:
            if self._job_list[job_name][3]:
                job_dirs = list(self.output_directory.glob(self._name+f'.htcondor.{job_name}.*'))
                # The user should remove the output files
                if not any([len(jds.glob('*'))>0 for jds in job_dirs]):
                    for jds in job_dirs:
                        jds.rmdir()
                    self._job_list.pop(job_name)
                else:
                    print(f"Job {job_name} still has output files saved. Please remove them for the cleaning to be performed! Check:\n"+ \
                          f"{self.output_directory / (self._name+f'.htcondor.{job_name}.*')}")
            else:
                print(f"Job {job_name} output files have not been retrived, so it cannot be cleaned!")
        if len(self._job_list) == 0:
            print("All jobs are already cleaned!")
        self.save_job_list()

    def _clean_boinc(self,  job_list=None, **kwarg):
        raise NotImplementedError("BOINC cleaning not implemented yet!")



# https://htcondor.readthedocs.io/en/latest/users-manual/submitting-a-job.html
# https://htcondor.readthedocs.io/en/latest/users-manual/file-transfer.html
# https://htcondor.readthedocs.io/en/latest/
# https://htcondor.readthedocs.io/en/latest/man-pages/condor_submit.html


# def main(job_class_name, job_class_script, **arg):
#         from importlib import import_module
#         import time
#         start_time = time.time()
#         import xdeps as xd
#         import xfields as xf
#         if 'xcoll' in sys.modules:
#             import xcoll as xc
#         job_class = import_module(job_class_script, package=job_class_name)
#         job_class.run(**arg)
#         print(f"Total calculation time {time.time()-start_time:.2f}s")

# if __name__ == '__main__':
#     print("Test:")
#     print(f"{DAJob.__name__=}")
#     print(f"{os.path.abspath(sys.modules[DAJob.__module__].__file__)=}")
#     print(f"{xt.Line.__name__=}")
#     print(f"{os.path.abspath(sys.modules[xt.Line.__module__].__file__)=}")
#     print(f"{str(Path(xt.__file__).parent)=}")
#     print("end")

#     # # Executable for the job class
#     # main(sys.argv[1], # job_class_name 
#     #      sys.argv[2], # job_class_script
#     #      **dict(arg.split('=') for arg in sys.argv[3:]) # job arguments
#     #      )