#!/bin/bash

#files='test_fs*.py'
files=''

for i in 8 9 10 11 12 13 14
do
    source ~/miniforge3/bin/activate python3.$i
    python -c "import sys; print(f'Testing xaux in Python version {sys.version.split()[0]}')"
    pytest $files
    source ~/miniforge3/bin/activate
done
