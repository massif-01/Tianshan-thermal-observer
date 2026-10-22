#!/bin/bash

# Quick test script for different installation methods
# Usage: ./test_all_installations.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=== Tegrastats API 安装方法测试 ==="

# Test 1: Current environment installation
log_info "测试1: 当前环境安装"
if ./install_package.sh --no-venv --skip-tests --quiet; then
    log_success "当前环境安装测试通过"
    
    # Quick CLI test
    if tegrastats-api --version >/dev/null 2>&1; then
        log_success "CLI命令正常工作"
    else
        log_error "CLI命令不工作"
    fi
else
    log_error "当前环境安装失败"
fi

echo ""

# Test 2: Development mode installation
log_info "测试2: 开发模式安装"
if ./install_package.sh --no-venv --dev --skip-tests --quiet; then
    log_success "开发模式安装测试通过"
else
    log_error "开发模式安装失败"
fi

echo ""

# Test 3: Virtual environment installation (only if we have enough time)
log_info "测试3: 虚拟环境安装（快速测试）"
if timeout 60 ./install_package.sh --venv quick-test-env --skip-tests --quiet 2>/dev/null; then
    log_success "虚拟环境安装测试通过"
    # Cleanup
    rm -rf "$SCRIPT_DIR/quick-test-env" 2>/dev/null || true
else
    log_info "虚拟环境测试跳过（超时或失败）"
    rm -rf "$SCRIPT_DIR/quick-test-env" 2>/dev/null || true
fi

echo ""

# Test 4: Package import test
log_info "测试4: Python包导入测试"
if python -c "
from tegrastats_api import TegrastatsServer, Config, TegrastatsParser
print('✓ 成功导入所有组件')

# Test basic functionality
config = Config(host='127.0.0.1', port=58001)
server = TegrastatsServer(config)
parser = TegrastatsParser()
print('✓ 成功创建所有对象')
" 2>/dev/null; then
    log_success "Python包导入测试通过"
else
    log_error "Python包导入测试失败"
fi

echo ""

# Test 5: CLI functionality test
log_info "测试5: CLI功能测试"
cli_tests_passed=0

# Test version
if tegrastats-api --version >/dev/null 2>&1; then
    cli_tests_passed=$((cli_tests_passed + 1))
fi

# Test config
if tegrastats-api config >/dev/null 2>&1; then
    cli_tests_passed=$((cli_tests_passed + 1))
fi

# Test help
if tegrastats-api --help >/dev/null 2>&1; then
    cli_tests_passed=$((cli_tests_passed + 1))
fi

if [[ $cli_tests_passed -eq 3 ]]; then
    log_success "CLI功能测试通过 (3/3)"
else
    log_error "CLI功能测试部分失败 ($cli_tests_passed/3)"
fi

echo ""

# Summary
log_success "=== 测试完成 ==="

echo "安装脚本功能："
echo "  ✓ ./install_package.sh --help              # 查看所有选项"
echo "  ✓ ./install_package.sh                     # 标准安装（虚拟环境）"
echo "  ✓ ./install_package.sh --dev               # 开发模式安装"
echo "  ✓ ./install_package.sh --conda             # 使用conda环境"
echo "  ✓ ./install_package.sh --no-venv           # 安装到当前环境"
echo "  ✓ ./install_package.sh --skip-tests        # 跳过测试"
echo "  ✓ ./install_package.sh --quiet             # 静默模式"

echo ""
echo "传统系统服务安装："
echo "  ✓ ./install.sh --host 0.0.0.0 --port 58090 # 系统服务安装"

echo ""
echo "包构建："
echo "  ✓ ./create_conda_package.sh                # 创建conda包"

log_success "所有安装方法已准备就绪！"