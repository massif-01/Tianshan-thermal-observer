#!/bin/sh
set -eu
sudo rm -- /etc/systemd/system/tegrastats-api.service.d/zz-rmstatus-1.1.1.conf
sudo systemctl daemon-reload
sudo systemctl restart tegrastats-api
systemctl show tegrastats-api -p MainPID -p ExecStart -p ActiveState
/home/rm01/.venvs/tegrastats-api/bin/python -m pip show tegrastats-api
