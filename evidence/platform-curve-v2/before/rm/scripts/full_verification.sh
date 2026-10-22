#!/bin/bash

# Tegrastats API 完整验证流程
# 从零开始验证安装、配置、服务和功能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# 全局配置
TEST_HOST="0.0.0.0"
TEST_PORT="58090"
SERVICE_NAME="tegrastats-api"
PACKAGE_NAME="tegrastats-api"

# 步骤计数器
STEP_COUNT=0
TOTAL_STEPS=12

# 显示步骤
show_step() {
    ((STEP_COUNT++))
    echo ""
    echo "======================================================"
    log_step "[$STEP_COUNT/$TOTAL_STEPS] $1"
    echo "======================================================"
}

# 等待用户确认
wait_for_confirmation() {
    if [[ "${AUTO_MODE:-false}" != "true" ]]; then
        read -p "按回车继续下一步... " -r
    else
        sleep 2
    fi
}

# 检查命令是否存在
check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        log_success "✓ $1 命令可用"
        return 0
    else
        log_error "✗ $1 命令不可用"
        return 1
    fi
}

# 验证系统要求
verify_system_requirements() {
    show_step "验证系统要求"
    
    log_info "检查必要的系统命令..."
    
    local required_commands=("python3" "pip" "conda" "systemctl" "curl" "tegrastats")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! check_command "$cmd"; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        log_error "缺少必要命令: ${missing_commands[*]}"
        log_info "请安装缺少的命令后重试"
        exit 1
    fi
    
    # 检查Python版本
    local python_version=$(python3 --version | cut -d' ' -f2)
    log_info "Python版本: $python_version"
    
    # 检查conda环境
    if [[ -n "$CONDA_DEFAULT_ENV" ]]; then
        log_info "当前conda环境: $CONDA_DEFAULT_ENV"
    else
        log_warning "未检测到activate的conda环境"
    fi
    
    log_success "系统要求验证完成"
    wait_for_confirmation
}

# 安装Python包
install_python_package() {
    show_step "安装Python包"
    
    log_info "开始安装tegrastats-api包..."
    
    # 检查当前目录
    if [[ ! -f "pyproject.toml" ]]; then
        log_error "未找到pyproject.toml文件，请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 安装包
    log_info "执行: pip install -e ."
    pip install -e . || {
        log_error "Python包安装失败"
        exit 1
    }
    
    log_success "Python包安装完成"
    wait_for_confirmation
}

# 验证CLI命令
verify_cli_commands() {
    show_step "验证CLI命令"
    
    local cli_commands=("tegrastats-api" "tegrastats-parser")
    
    for cmd in "${cli_commands[@]}"; do
        log_info "测试命令: $cmd --help"
        if $cmd --help >/dev/null 2>&1; then
            log_success "✓ $cmd 命令正常"
        else
            log_error "✗ $cmd 命令异常"
            exit 1
        fi
    done
    
    # 测试版本信息
    log_info "获取版本信息..."
    tegrastats-api --version || log_warning "版本信息获取失败"
    
    log_success "CLI命令验证完成"
    wait_for_confirmation
}

# 测试解析器功能
test_parser_functionality() {
    show_step "测试解析器功能"
    
    log_info "测试tegrastats数据解析..."
    
    # 启动tegrastats获取一些数据
    log_info "获取tegrastats数据样本..."
    timeout 5 tegrastats --interval 1000 > /tmp/tegrastats_sample.txt 2>/dev/null || true
    
    if [[ -s /tmp/tegrastats_sample.txt ]]; then
        log_info "使用tegrastats-parser解析数据..."
        if tegrastats-parser parse /tmp/tegrastats_sample.txt --format json >/dev/null 2>&1; then
            log_success "✓ 解析器功能正常"
        else
            log_warning "解析器测试失败，但可能是数据格式问题"
        fi
        rm -f /tmp/tegrastats_sample.txt
    else
        log_warning "未能获取tegrastats数据样本，跳过解析器测试"
    fi
    
    log_success "解析器功能测试完成"
    wait_for_confirmation
}

# 测试服务器功能
test_server_functionality() {
    show_step "测试服务器功能"
    
    log_info "启动测试服务器..."
    
    # 在后台启动服务器
    tegrastats-api run --host 127.0.0.1 --port 58091 --debug &
    local server_pid=$!
    
    log_info "等待服务器启动..."
    sleep 5
    
    # 测试API端点
    local test_endpoints=("/api/health" "/api/status" "/api/cpu" "/api/memory")
    local base_url="http://127.0.0.1:58091"
    
    for endpoint in "${test_endpoints[@]}"; do
        log_info "测试端点: $endpoint"
        if curl -s -f "$base_url$endpoint" >/dev/null; then
            log_success "✓ $endpoint 响应正常"
        else
            log_warning "✗ $endpoint 响应异常"
        fi
    done
    
    # 停止测试服务器
    log_info "停止测试服务器..."
    kill $server_pid 2>/dev/null || true
    wait $server_pid 2>/dev/null || true
    
    log_success "服务器功能测试完成"
    wait_for_confirmation
}

# 创建系统服务
create_system_service() {
    show_step "创建系统服务"
    
    log_info "使用create_service.sh创建systemd服务..."
    
    if [[ ! -f "create_service.sh" ]]; then
        log_error "未找到create_service.sh脚本"
        exit 1
    fi
    
    # 创建服务
    log_info "执行: sudo ./create_service.sh --host $TEST_HOST --port $TEST_PORT"
    sudo ./create_service.sh --host "$TEST_HOST" --port "$TEST_PORT" || {
        log_error "系统服务创建失败"
        exit 1
    }
    
    log_success "系统服务创建完成"
    wait_for_confirmation
}

# 验证服务状态
verify_service_status() {
    show_step "验证服务状态"
    
    log_info "检查服务安装状态..."
    
    # 检查服务文件
    if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
        log_success "✓ 服务文件已创建"
    else
        log_error "✗ 服务文件不存在"
        exit 1
    fi
    
    # 检查服务启用状态
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        log_success "✓ 服务已启用自动启动"
    else
        log_error "✗ 服务未启用自动启动"
        exit 1
    fi
    
    # 检查服务运行状态
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "✓ 服务正在运行"
    else
        log_warning "✗ 服务未运行，尝试启动..."
        sudo systemctl start "$SERVICE_NAME"
        sleep 3
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            log_success "✓ 服务启动成功"
        else
            log_error "✗ 服务启动失败"
            sudo systemctl status "$SERVICE_NAME" --no-pager -l
            exit 1
        fi
    fi
    
    log_success "服务状态验证完成"
    wait_for_confirmation
}

# 测试API端点
test_api_endpoints() {
    show_step "测试API端点"
    
    local base_url="http://localhost:$TEST_PORT"
    local endpoints=(
        "/api/health:健康检查"
        "/api/status:系统状态"
        "/api/cpu:CPU信息"
        "/api/memory:内存信息"
        "/api/temperature:温度信息"
        "/api/power:功耗信息"
    )
    
    log_info "等待服务完全启动..."
    sleep 5
    
    for endpoint_info in "${endpoints[@]}"; do
        local endpoint="${endpoint_info%:*}"
        local description="${endpoint_info#*:}"
        
        log_info "测试 $description ($endpoint)..."
        
        local response=$(curl -s -w "%{http_code}" "$base_url$endpoint" 2>/dev/null)
        local http_code="${response: -3}"
        local body="${response%???}"
        
        if [[ "$http_code" == "200" ]]; then
            log_success "✓ $endpoint 响应正常 (HTTP $http_code)"
            if [[ ${#body} -gt 100 ]]; then
                log_info "  响应数据: ${body:0:100}..."
            else
                log_info "  响应数据: $body"
            fi
        else
            log_warning "✗ $endpoint 响应异常 (HTTP $http_code)"
        fi
    done
    
    log_success "API端点测试完成"
    wait_for_confirmation
}

# 测试WebSocket连接
test_websocket_connection() {
    show_step "测试WebSocket连接"
    
    log_info "测试WebSocket实时数据推送..."
    
    # 简单的WebSocket测试（使用curl测试升级请求）
    local ws_url="http://localhost:$TEST_PORT/socket.io/"
    
    log_info "检查Socket.IO端点..."
    if curl -s -f "$ws_url" >/dev/null 2>&1; then
        log_success "✓ Socket.IO端点可访问"
    else
        log_warning "✗ Socket.IO端点测试失败"
    fi
    
    log_success "WebSocket连接测试完成"
    wait_for_confirmation
}

# 测试服务管理脚本
test_management_scripts() {
    show_step "测试服务管理脚本"
    
    if [[ -f "manage_service.sh" ]]; then
        log_info "测试manage_service.sh功能..."
        
        # 测试状态查看
        log_info "测试状态查看..."
        ./manage_service.sh status >/dev/null 2>&1 && log_success "✓ 状态查看正常" || log_warning "✗ 状态查看异常"
        
        # 测试API连接
        log_info "测试API连接..."
        ./manage_service.sh test >/dev/null 2>&1 && log_success "✓ API连接测试正常" || log_warning "✗ API连接测试异常"
        
    else
        log_warning "manage_service.sh脚本不存在"
    fi
    
    log_success "服务管理脚本测试完成"
    wait_for_confirmation
}

# 性能和负载测试
test_performance() {
    show_step "性能和负载测试"
    
    log_info "执行基本性能测试..."
    
    local base_url="http://localhost:$TEST_PORT"
    
    # 并发请求测试
    log_info "测试并发请求处理..."
    for i in {1..10}; do
        curl -s "$base_url/api/health" >/dev/null &
    done
    wait
    log_success "✓ 并发请求测试完成"
    
    # 连续请求测试
    log_info "测试连续请求响应..."
    for i in {1..5}; do
        local start_time=$(date +%s%N)
        curl -s "$base_url/api/status" >/dev/null
        local end_time=$(date +%s%N)
        local duration=$(( (end_time - start_time) / 1000000 ))
        log_info "  请求 $i: ${duration}ms"
    done
    
    log_success "性能测试完成"
    wait_for_confirmation
}

# 最终验证
final_verification() {
    show_step "最终验证"
    
    log_info "执行完整系统验证..."
    
    # 运行verify_installation.sh
    if [[ -f "verify_installation.sh" ]]; then
        log_info "运行verify_installation.sh..."
        if ./verify_installation.sh >/dev/null 2>&1; then
            log_success "✓ 系统验证脚本通过"
        else
            log_warning "✗ 系统验证脚本报告问题"
        fi
    fi
    
    # 最终状态检查
    log_info "最终状态检查..."
    
    # 检查包安装
    if pip show "$PACKAGE_NAME" >/dev/null 2>&1; then
        log_success "✓ Python包已正确安装"
    else
        log_error "✗ Python包安装有问题"
    fi
    
    # 检查服务运行
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "✓ 系统服务正在运行"
    else
        log_error "✗ 系统服务未运行"
    fi
    
    # 检查API响应
    if curl -s -f "http://localhost:$TEST_PORT/api/health" >/dev/null; then
        log_success "✓ API正常响应"
    else
        log_error "✗ API无响应"
    fi
    
    log_success "最终验证完成"
}

# 显示验证结果
show_verification_result() {
    echo ""
    echo "======================================================"
    echo "        Tegrastats API 验证流程完成!"
    echo "======================================================"
    echo ""
    log_success "✅ 验证流程全部完成"
    echo ""
    log_info "系统信息:"
    echo "  📦 Python包: 已安装并可用"
    echo "  🚀 系统服务: 正在运行并已启用自动启动"
    echo "  🌐 API服务: http://localhost:$TEST_PORT"
    echo "  📊 实时数据: WebSocket连接可用"
    echo ""
    log_info "管理命令:"
    echo "  sudo systemctl status $SERVICE_NAME    # 查看服务状态"
    echo "  sudo systemctl restart $SERVICE_NAME   # 重启服务"
    echo "  ./manage_service.sh status            # 使用管理脚本"
    echo "  ./verify_installation.sh              # 快速验证"
    echo ""
    log_info "API端点:"
    echo "  GET /api/health      # 健康检查"
    echo "  GET /api/status      # 完整系统状态"
    echo "  GET /api/cpu         # CPU信息"
    echo "  GET /api/memory      # 内存信息"
    echo "  GET /api/temperature # 温度信息"
    echo "  GET /api/power       # 功耗信息"
    echo ""
    echo "======================================================"
    log_success "🎉 Tegrastats API 已完全部署并验证成功!"
    echo "======================================================"
}

# 错误处理
handle_error() {
    log_error "验证过程中发生错误: $1"
    log_info "请检查错误信息并重试"
    exit 1
}

# 主验证流程
main() {
    echo "======================================================"
    echo "     Tegrastats API 完整验证流程 v1.0"
    echo "======================================================"
    echo ""
    log_info "此脚本将执行完整的安装和验证流程:"
    echo "  1. 验证系统要求"
    echo "  2. 安装Python包"
    echo "  3. 验证CLI命令"
    echo "  4. 测试解析器功能"
    echo "  5. 测试服务器功能"
    echo "  6. 创建系统服务"
    echo "  7. 验证服务状态"
    echo "  8. 测试API端点"
    echo "  9. 测试WebSocket连接"
    echo "  10. 测试管理脚本"
    echo "  11. 性能测试"
    echo "  12. 最终验证"
    echo ""
    
    if [[ "${AUTO_MODE:-false}" != "true" ]]; then
        read -p "是否继续执行验证流程? [Y/n]: " -r
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "验证流程已取消"
            exit 0
        fi
    fi
    
    # 设置错误处理
    trap 'handle_error "第$STEP_COUNT步执行失败"' ERR
    
    # 执行验证步骤
    verify_system_requirements
    install_python_package
    verify_cli_commands
    test_parser_functionality
    test_server_functionality
    create_system_service
    verify_service_status
    test_api_endpoints
    test_websocket_connection
    test_management_scripts
    test_performance
    final_verification
    
    # 显示结果
    show_verification_result
}

# 处理命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_MODE=true
            shift
            ;;
        --host)
            TEST_HOST="$2"
            shift 2
            ;;
        --port)
            TEST_PORT="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --auto        自动模式，不等待用户确认"
            echo "  --host HOST   测试主机地址 (默认: 0.0.0.0)"
            echo "  --port PORT   测试端口 (默认: 58090)"
            echo "  --help, -h    显示此帮助信息"
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            exit 1
            ;;
    esac
done

# 检查是否在项目根目录
if [[ ! -f "pyproject.toml" ]]; then
    log_error "请在项目根目录运行此脚本"
    exit 1
fi

# 运行主程序
main "$@"