#!/bin/bash

PROJECT_DIR=/home/pi/iotabot

python -m venv ${PROJECT_DIR}/venv
source ${PROJECT_DIR}/venv/bin/activate
pip install --upgrade pip
pip install -r ${PROJECT_DIR}/requirements.txt
python ${PROJECT_DIR}/launcher.py
