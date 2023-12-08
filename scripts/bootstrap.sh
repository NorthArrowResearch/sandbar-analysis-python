#! /bin/bash
set -eu

# remove the .venv directory if it exists
if [ -d ".venv" ]; then
  rm -rf .venv
fi

# On OSX you must have run `brew install gdal` so that the header files are findable 
python3 --version
python3 -m venv .venv
# Make sure pip is at a good version
.venv/bin/python3 -m pip install --upgrade pip

# This is the only way I've found to overcome the following error:
# https://gis.stackexchange.com/questions/153199/import-error-no-module-named-gdal-array
# ensure numpy is installed prior to installing gdal
.venv/bin/pip3 install numpy
# ensure setuptools and wheel are installed to do the build in your current environment
.venv/bin/pip3 install -U setuptools wheel
# install gdal
.venv/bin/pip3 install --no-build-isolation --no-cache-dir --force-reinstall gdal 

# Now install everything else
.venv/bin/pip3 --timeout=120 install -r requirements.txt
