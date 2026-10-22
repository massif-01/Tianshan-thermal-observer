#!/bin/sh
# Uses the factory-installed Conda; never installs/updates Conda or starts services.
set -eu
# Do not let Conda reconcile pip metadata in the preinstalled base.
export CONDA_PIP_INTEROP_ENABLED=false
bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${CONDA_EXE:-}" ] && [ -x "$CONDA_EXE" ]; then
    conda_executable=$CONDA_EXE
elif command -v conda >/dev/null 2>&1; then
    conda_base=$(conda info --base)
    conda_executable=$conda_base/bin/conda
else
    printf '%s\n' '未找到出厂Conda。请在已初始化Conda的终端运行，或用 CONDA_EXE=/path/to/conda sh install.sh 指定位置。' >&2
    exit 1
fi
conda_base=$("$conda_executable" info --base)
exec "$conda_base/bin/python" "$bundle_dir/scripts/install_tto.py" --conda-exe "$conda_executable" "$@"
