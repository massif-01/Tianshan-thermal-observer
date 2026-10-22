#!/bin/bash

# Create conda package for Tegrastats API
# Usage: ./create_conda_package.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="tegrastats-api"
PACKAGE_VERSION="1.0.0"
CONDA_BUILD_DIR="$SCRIPT_DIR/conda-build"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=== Tegrastats API Conda包构建 ==="

# Check if conda-build is installed
if ! command -v conda-build >/dev/null 2>&1; then
    log_info "安装conda-build..."
    conda install conda-build -y
fi

# Create conda build directory
log_info "创建conda构建目录..."
rm -rf "$CONDA_BUILD_DIR"
mkdir -p "$CONDA_BUILD_DIR"

# Create meta.yaml
log_info "创建meta.yaml配置文件..."
cat > "$CONDA_BUILD_DIR/meta.yaml" << EOF
{% set name = "tegrastats-api" %}
{% set version = "1.0.0" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  path: ..

build:
  number: 0
  script: python -m pip install . -vv
  entry_points:
    - tegrastats-api = tegrastats_api.cli:main
    - tegrastats-server = tegrastats_api.cli:main
  noarch: python

requirements:
  host:
    - python >=3.7
    - pip
    - setuptools
    - wheel
  run:
    - python >=3.7
    - flask >=2.3.0
    - flask-socketio >=5.3.0
    - flask-cors >=4.0.0
    - python-socketio >=5.9.0
    - eventlet >=0.33.0
    - psutil >=5.9.0
    - requests >=2.31.0
    - websocket-client >=1.6.0
    - click >=8.0.0

test:
  imports:
    - tegrastats_api
    - tegrastats_api.server
    - tegrastats_api.parser
    - tegrastats_api.config
    - tegrastats_api.cli
  commands:
    - tegrastats-api --help
    - tegrastats-api config

about:
  home: https://github.com/your-username/tegrastats-api
  license: MIT
  license_file: LICENSE
  summary: HTTP API and WebSocket server for NVIDIA Jetson tegrastats monitoring
  description: |
    Tegrastats API provides a Flask-based HTTP API and WebSocket server for accessing
    tegrastats data from NVIDIA Jetson devices. Designed for integration with
    embedded devices like ESP32S3.
  doc_url: https://github.com/your-username/tegrastats-api
  dev_url: https://github.com/your-username/tegrastats-api

extra:
  recipe-maintainers:
    - your-username
EOF

# Create build script
log_info "创建构建脚本..."
cat > "$CONDA_BUILD_DIR/build.sh" << 'EOF'
#!/bin/bash
python -m pip install . -vv
EOF
chmod +x "$CONDA_BUILD_DIR/build.sh"

# Build the package
log_info "构建conda包..."
cd "$SCRIPT_DIR"
conda-build "$CONDA_BUILD_DIR" --output-folder "$CONDA_BUILD_DIR/output"

# Find the built package
BUILT_PACKAGE=$(find "$CONDA_BUILD_DIR/output" -name "*.tar.bz2" | head -1)

if [[ -n "$BUILT_PACKAGE" ]]; then
    log_success "Conda包构建完成: $BUILT_PACKAGE"
    
    # Test installation
    log_info "测试包安装..."
    conda install "$BUILT_PACKAGE" -y
    
    # Test CLI
    if tegrastats-api --version >/dev/null 2>&1; then
        log_success "CLI测试通过"
    else
        log_error "CLI测试失败"
        exit 1
    fi
    
    log_success "Conda包构建和测试完成！"
    echo "包位置: $BUILT_PACKAGE"
    echo ""
    echo "安装方法:"
    echo "  conda install $BUILT_PACKAGE"
    echo ""
    echo "或上传到conda-forge后:"
    echo "  conda install -c conda-forge tegrastats-api"
    
else
    log_error "未找到构建的包"
    exit 1
fi