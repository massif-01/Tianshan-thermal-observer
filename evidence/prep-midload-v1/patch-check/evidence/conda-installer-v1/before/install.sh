#!/bin/sh
# Local installation only; no device access or service startup.
set -eu
bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${TTO_INSTALL_PYTHON:-}" ]; then
    installer_python=$TTO_INSTALL_PYTHON
elif command -v python3.10 >/dev/null 2>&1; then
    installer_python=python3.10
elif command -v python3 >/dev/null 2>&1; then
    installer_python=python3
else
    printf '%s\n' '未找到Python。Ubuntu 22.04可先执行：sudo apt install python3 python3-venv' >&2
    exit 1
fi
exec "$installer_python" "$bundle_dir/scripts/install_tto.py" "$@"
