#!/bin/bash

DIR=`pwd`

cd /opt/projects/cgru
source ./setup.sh
cd $DIR
python3.6 afGui.py
