#!/bin/bash

files="test_fs.py test_afs.py test_eos.py test_fs_api.py"

# Activate the Mamba base environment
source /apps/miniforge3/etc/profile.d/conda.sh
source /apps/miniforge3/etc/profile.d/mamba.sh

mamba activate python3.8
python -c "import sys; print(f'Testing xaux FS in Python version {sys.version.split()[0]}')"
pytest $files
mamba deactivate

mamba activate python3.9
python -c "import sys; print(f'Testing xaux FS in Python version {sys.version.split()[0]}')"
pytest $files
mamba deactivate

mamba activate python3.10
python -c "import sys; print(f'Testing xaux FS in Python version {sys.version.split()[0]}')"
pytest $files
mamba deactivate

mamba activate python3.11
python -c "import sys; print(f'Testing xaux FS in Python version {sys.version.split()[0]}')"
pytest $files
mamba deactivate

mamba activate python3.12
python -c "import sys; print(f'Testing xaux FS in Python version {sys.version.split()[0]}')"
pytest $files
mamba deactivate
