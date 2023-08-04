#! /bin/bash

# source the venv

source ./venv/bin/activate
nohup python -u observer.py &
tail -f nohup.out
