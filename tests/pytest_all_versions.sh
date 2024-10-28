#!/bin/bash

# files="test_fs.py test_fs_api.py test_fs_afs.py test_fs_eos.py"
files=''

for i in 8 9 10 11 # 12 13
do
    source ~/miniforge3/bin/activate python3.$i
    python -c "import sys; print(f'Testing xaux FS in Python version {sys.version.split()[0]}')"
    pytest $files
    source ~/miniforge3/bin/activate
done
