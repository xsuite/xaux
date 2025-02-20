# copyright ############################### #
# This file is part of the Xaux Package.    #
# Copyright (c) CERN, 2024.                 #
# ######################################### #

import pytest
import json
import sys
from pathlib import Path
from xaux.jobmanager import JobManager, DAJob
import pandas as pd




def test_jobmanager_DA():
    # prepare the input files for the test
    default_path = Path(__file__).parent / 'JM_Test'
    input_directory = default_path / 'input'
    if not input_directory.exists():
        input_directory.mkdir(parents=True)
    for ii in range(1,4):
        with open(input_directory / f'line{ii}.json', 'w') as f:
            json.dump(f'test line{ii}.json', f)
    input_directory2= default_path / 'input2'
    if not (input_directory2 / 'test').exists():
        (input_directory2 / 'test').mkdir(parents=True)
    with open(input_directory2 / 'test' / f'extra.txt', 'w') as f:
        f.write('test extra.txt')
    # Clea the output directory
    output_directory = default_path / 'output'
    if output_directory.exists():
        for file in output_directory.iterdir():
            if file.is_file():
                file.unlink()
            if file.is_dir():
                for f in file.iterdir():
                    f.unlink()
                file.rmdir()
        output_directory.rmdir()
    assert not output_directory.exists()
    # Clean the work directory
    work_directory = default_path / 'dirtest_jobmanager'
    if work_directory.exists():
        for file in work_directory.iterdir():
            if file.is_file():
                file.unlink()
            if file.is_dir():
                for f in file.iterdir():
                    f.unlink()
                file.rmdir()
        work_directory.rmdir()
    assert not work_directory.exists()
    # Create the job manager
    manager = JobManager(name='TestDA', job_class=DAJob, work_directory=work_directory, 
                         output_directory=output_directory, input_directory=input_directory)
    assert manager.work_directory == work_directory
    assert work_directory.exists()
    assert manager._name == 'TestDA'
    assert manager.metafile == work_directory / 'TestDA.jobmanager.meta.json'
    assert manager.metafile.exists()
    assert manager.job_class == DAJob
    assert manager.input_directory == input_directory
    assert manager.output_directory == output_directory
    assert manager.output_directory.exists()
    assert len(manager._job_list) == 0
    # Add jobs
    assert not manager.job_management_file.exists()
    part = pd.DataFrame({'x': [1,2,3], 'y': [4,5,6]})
    manager.add(
        job1={"inputfiles":{"line": "line1.json", "extrafile": input_directory2/"test/extra.txt", "particles": part}, "parameters":{"num_particles": 1000, "num_turns": 1000}, "outputfiles": {"part": "part.parquet"}},
        job2={"inputfiles":{"line": "line2.json", "extrafile": input_directory2/"test/extra.txt", "particles": part}, "parameters":{"num_particles": 1000, "num_turns": 1000}, "outputfiles": {"part": "part.parquet"}},
        job3={"inputfiles":{"line": "line3.json", "extrafile": input_directory2/"test/extra.txt", "particles": part}, "parameters":{"num_particles": 1000, "num_turns":  100}, "outputfiles": {"part": "part.parquet"}}
    )
    assert manager.job_management_file.exists()
    assert len(manager._job_list) == 3
    for ii,(nn,job) in enumerate(manager._job_list.items(),1):
        assert nn == f'job{ii}', f'job{ii} != {nn}'
        for kk,vv in job[0]['inputfiles'].items():
            assert isinstance(vv,str), f'In \'inputfiles/{kk}\', {vv} is not a string'
            assert Path(vv).exists(),  f'In \'inputfiles/{kk}\', {vv} does not exist'
        for kk,vv in job[0]['outputfiles'].items():
            assert isinstance(vv,str), f'In \'outputfiles/{kk}\', {vv} is not a string'
            assert not Path(vv).exists(),  f'In \'outputfiles/{kk}\', {vv} already exist'
        assert job[1] == False, f'job{ii} is set as submitted while it shouldn\'t be'
        assert job[2] == False, f'job{ii} is set as finished while it shouldn\'t be'
        assert job[3] == False, f'job{ii} is set as its results have been retrived while it shouldn\'t be'
    manager.submit(auto=False)
    for ii,job in enumerate(manager._job_list.values(),1):
        assert job[1] == True,  f'job{ii} is set as not submitted while it should be'
        assert job[2] == False, f'job{ii} is set as finished while it shouldn\'t be'
        assert job[3] == False, f'job{ii} is set as its results have been retrived while it shouldn\'t be'

test_jobmanager_DA()


# if 'xcoll' in sys.modules:
#     from xaux.jobmanager import LossMapPencilJob
#     def test_jobmanager_LM():
#         manager = JobManager(job_class=LossMapPencilJob)
#         manager.add({
#             'job0': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
#             'job1': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
#             'job2': {'inputfiles':{'line': "line.json", 'colldb': "colldb.yaml"}, "parameters":{'num_particles': 50000,'lmtype': "B1H", 'num_turns': 200}},
#         })

    
#     test_jobmanager_LM()