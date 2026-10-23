#!/bin/sh
set -eu
export CONDA_PIP_INTEROP_ENABLED=false
install_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$install_dir"
exec /opt/anaconda3/bin/conda run --no-capture-output --prefix "$install_dir/conda-env" python -I "$install_dir/thermal_trials/run_midload.py" "$@"
