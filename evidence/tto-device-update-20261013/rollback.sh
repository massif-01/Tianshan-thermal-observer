#!/bin/sh
set -eu
/home/rm01/TTO/conda-env/bin/python -I -m pip install --no-index --no-deps --force-reinstall /home/rm01/tto-update-0.2.2-20261013/backup/tianshan_thermal_observer-0.1.2-py3-none-any.whl
cp -p /home/rm01/tto-update-0.2.2-20261013/backup/tto /home/rm01/TTO/tto
cp -p /home/rm01/tto-update-0.2.2-20261013/backup/.tto-install.json /home/rm01/TTO/.tto-install.json
cp -p /home/rm01/tto-update-0.2.2-20261013/backup/installation.json /home/rm01/TTO/installation.json
/home/rm01/TTO/tto --version
