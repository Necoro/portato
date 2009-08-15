#!/bin/sh

python setup.py build_ext -i
# remove the "build" directory
python setup.py clean -a 
