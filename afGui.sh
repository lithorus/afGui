#!/bin/bash

DIR=`pwd`

cd /opt/projects/cgru
source ./setup.sh
export QT_PREFERRED_BINDING=PySide
cd $DIR
python afGui.py
