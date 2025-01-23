# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import pytest
import json
import sys
from pathlib import Path
from xaux.jobmanager import JobManager, DAJob


def test_jobmanager_DA():
    work_directory = Path("/home/thpugnat/Public/Xsuite/xaux/tests/dirtest_jobmanager")
    if work_directory.exists():
        for file in work_directory.iterdir():
            if file.is_file():
                file.unlink()
            if file.is_dir():
                for f in file.iterdir():
                    f.unlink()
                file.rmdir()
        work_directory.rmdir()
    manager = JobManager(name='TestDA',job_class=DAJob, work_directory=work_directory)
    manager.save_metadata()
    manager.add(
        job1={"inputfiles":{"line": "line1.json"}, "particles": "part.1.parquet", "parameters":{"num_particles": 1000, "num_turns": 1000}, "outputfiles": {"part": "part.parquet"}},
        job2={"inputfiles":{"line": "line2.json"}, "particles": "part.2.parquet", "parameters":{"num_particles": 1000, "num_turns": 1000}, "outputfiles": {"part": "part.parquet"}},
        job3={"inputfiles":{"line": "line3.json"}, "particles": "part.3.parquet", "parameters":{"num_particles": 1000, "num_turns":  100}, "outputfiles": {"part": "part.parquet"}}
    )
    manager.submit()

test_jobmanager_DA()


if 'xcoll' in sys.modules:
    from xaux.jobmanager import LossMapPencilJob
    def test_jobmanager_LM():
        manager = JobManager(job_class=LossMapPencilJob)
        manager.add({
            'job0': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
            'job1': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
            'job2': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
        })

    
    test_jobmanager_LM()