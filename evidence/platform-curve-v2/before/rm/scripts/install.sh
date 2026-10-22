#!/bin/bash

# Tegrastats API 一键安装脚本
# 自动创建conda环境、安装依赖、部署服务并启动

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置参数
CONDA_ENV_NAME="tegrastats-api"
SERVICE_NAME="tegrastats-api"
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="58090"
PYTHON_VERSION="3.9"

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

# 显示用法
show_usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --host HOST       服务监听地址 (默认: $DEFAULT_HOST)"
    echo "  --port PORT       服务监听端口 (默认: $DEFAULT_PORT)"
    echo "  --env-name NAME   conda环境名称 (默认: $CONDA_ENV_NAME)"
    echo "  --python VERSION  Python版本 (默认: $PYTHON_VERSION)"
    echo "  --help, -h        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                              # 使用默认配置"
    echo "  $0 --host 127.0.0.1 --port 8080 # 自定义地址和端口"
    echo "  $0 --env-name my-tegrastats      # 自定义环境名"
}

# 检查系统要求
check_requirements() {
    log_step "检查系统要求"
    
    # 检查是否为root用户
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        log_info "正确用法: ./install.sh"
        exit 1
    fi
    
    # 检查必要命令
    local required_commands=("conda" "curl" "systemctl" "tegrastats")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        log_error "缺少必要命令: ${missing_commands[*]}"
        log_info "请安装缺少的命令后重试"
        exit 1
    fi
    
    # 检查项目文件
    if [[ ! -f "pyproject.toml" ]]; then
        log_error "未找到pyproject.toml文件"
        log_info "请在项目根目录运行此脚本"
        exit 1
    fi
    
    log_success "系统要求检查通过"
}

# 初始化conda
init_conda() {
    log_step "初始化conda环境"
    
    # 检查conda是否已初始化
    if [[ ! -f "$HOME/.bashrc" ]] || ! grep -q "conda initialize" "$HOME/.bashrc" 2>/dev/null; then
        log_info "初始化conda..."
        conda init bash
        log_success "conda初始化完成"
        log_warning "请运行 'source ~/.bashrc' 或重新打开终端后再次运行此脚本"
        exit 0
    fi
    
    # 加载conda配置
    if [[ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    elif [[ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
    else
        eval "$(conda shell.bash hook)" 2>/dev/null || {
            log_error "无法加载conda配置"
            exit 1
        }
    fi
    
    log_success "conda环境已加载"
}

# 创建或更新conda环境
setup_conda_env() {
    log_step "设置conda环境: $CONDA_ENV_NAME"
    
    # 检查环境是否已存在
    if conda env list | grep -q "^${CONDA_ENV_NAME}\\s"; then
        log_warning "环境已存在: $CONDA_ENV_NAME"
        read -p "是否删除现有环境并重新创建? [y/N]: " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "删除现有环境..."
            conda env remove -n "$CONDA_ENV_NAME" -y
        else
            log_info "使用现有环境"
        fi
    fi
    
    # 创建环境（如果不存在）
    if ! conda env list | grep -q "^${CONDA_ENV_NAME}\\s"; then
        log_info "创建conda环境: $CONDA_ENV_NAME (Python $PYTHON_VERSION)"
        conda create -n "$CONDA_ENV_NAME" python="$PYTHON_VERSION" -y
        log_success "conda环境创建完成"
    fi
    
    # 激活环境
    log_info "激活环境: $CONDA_ENV_NAME"
    conda activate "$CONDA_ENV_NAME"
    log_success "环境已激活: $(python --version)"
}

# 安装Python包和依赖
install_package() {
    log_step "安装Python包和依赖"
    
    # 确保在正确的环境中
    if [[ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV_NAME" ]]; then
        log_warning "当前不在目标环境中，重新激活..."
        conda activate "$CONDA_ENV_NAME"
    fi
    
    log_info "升级pip..."
    pip install --upgrade pip
    
    log_info "安装项目依赖..."
    pip install -e .
    
    # 验证安装
    log_info "验证安装..."
    if ! command -v tegrastats-api >/dev/null 2>&1; then
        log_error "tegrastats-api命令未找到"
        exit 1
    fi
    
    log_success "Python包安装完成"
    
    # 显示安装信息
    log_info "已安装的CLI命令:"
    echo "  • tegrastats-api --version: $(tegrastats-api --version 2>/dev/null || echo '获取版本失败')"
    echo "  • tegrastats-parser --help: 可用"
}

# 创建systemd服务
create_service() {
    log_step "创建systemd服务"
    
    # 获取环境路径
    local env_path="$CONDA_PREFIX"
    local python_path="$env_path/bin/python"
    local exec_path="$env_path/bin/tegrastats-api"
    local working_dir="$(pwd)"
    
    # 验证路径
    if [[ ! -f "$exec_path" ]]; then
        log_error "找不到tegrastats-api执行文件: $exec_path"
        exit 1
    fi
    
    log_info "创建服务文件..."
    log_info "  环境路径: $env_path"
    log_info "  执行文件: $exec_path"
    log_info "  监听地址: $SERVICE_HOST:$SERVICE_PORT"
    
    # 创建服务文件
    sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << EOF
[Unit]
Description=Tegrastats API Server
Documentation=https://github.com/your-repo/tegrastats-api
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=$USER
Group=$(id -gn)
WorkingDirectory=$working_dir
Environment=PATH=$env_path/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$working_dir
Environment=TEGRASTATS_API_HOST=$SERVICE_HOST
Environment=TEGRASTATS_API_PORT=$SERVICE_PORT
Environment=TEGRASTATS_API_ALLOW_UNSAFE_WERKZEUG=true
ExecStart=$exec_path run --host $SERVICE_HOST --port $SERVICE_PORT
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=false
ReadWritePaths=$working_dir
ReadWritePaths=/tmp
ReadWritePaths=/var/tmp

[Install]
WantedBy=multi-user.target
EOF
    
    log_success "服务文件已创建"
    
    # 重载systemd配置
    log_info "重载systemd配置..."
    sudo systemctl daemon-reload
    
    # 启用服务
    log_info "启用服务自动启动..."
    sudo systemctl enable "$SERVICE_NAME"
    
    log_success "systemd服务配置完成"
}

# 启动和验证服务
start_and_verify_service() {
    log_step "启动和验证服务"
    
    # 启动服务
    log_info "启动服务..."
    sudo systemctl start "$SERVICE_NAME"
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 5
    
    # 检查服务状态
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "✓ 服务正在运行"
    else
        log_error "✗ 服务启动失败"
        log_info "查看服务日志:"
        sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager
        exit 1
    fi
    
    # 测试API响应
    log_info "测试API响应..."
    local api_url="http://$SERVICE_HOST:$SERVICE_PORT/api/health"
    local max_attempts=10
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "尝试连接API ($attempt/$max_attempts)..."
        
        if curl -s -f "$api_url" >/dev/null 2>&1; then
            log_success "✓ API响应正常"
            break
        else
            if [[ $attempt -eq $max_attempts ]]; then
                log_error "✗ API连接失败"
                log_info "检查服务日志:"
                sudo journalctl -u "$SERVICE_NAME" -n 10 --no-pager
                exit 1
            fi
            sleep 2
            ((attempt++))
        fi
    done
    
    # 测试其他端点
    local endpoints=("/api/status" "/api/cpu" "/api/memory")
    for endpoint in "${endpoints[@]}"; do
        local url="http://$SERVICE_HOST:$SERVICE_PORT$endpoint"
        if curl -s -f "$url" >/dev/null 2>&1; then
            log_success "✓ $endpoint 正常"
        else
            log_warning "✗ $endpoint 可能有问题"
        fi
    done
    
    log_success "服务验证完成"
}

# 创建管理脚本
create_management_script() {
    log_step "创建管理脚本"
    
    local script_path="./manage_tegrastats.sh"
    
    cat > "$script_path" << 'EOF'
#!/bin/bash

# Tegrastats API 管理脚本

SERVICE_NAME="tegrastats-api"
SERVICE_HOST="__SERVICE_HOST__"
SERVICE_PORT="__SERVICE_PORT__"

case "$1" in
    start)
        echo "启动服务..."
        sudo systemctl start $SERVICE_NAME
        ;;
    stop)
        echo "停止服务..."
        sudo systemctl stop $SERVICE_NAME
        ;;
    restart)
        echo "重启服务..."
        sudo systemctl restart $SERVICE_NAME
        ;;
    status)
        echo "服务状态:"
        sudo systemctl status $SERVICE_NAME --no-pager -l
        ;;
    logs)
        echo "查看日志 (按Ctrl+C退出):"
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    test)
        echo "测试API连接..."
        if curl -s "http://$SERVICE_HOST:$SERVICE_PORT/api/health" | grep -q "healthy"; then
            echo "✓ API连接正常"
            echo "✓ 健康检查: http://$SERVICE_HOST:$SERVICE_PORT/api/health"
            echo "✓ 系统状态: http://$SERVICE_HOST:$SERVICE_PORT/api/status"
        else
            echo "✗ API连接失败"
            exit 1
        fi
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动服务"
        echo "  stop    - 停止服务"
        echo "  restart - 重启服务"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看实时日志"
        echo "  test    - 测试API连接"
        exit 1
        ;;
esac
EOF
    
    # 替换配置变量
    sed -i "s/__SERVICE_HOST__/$SERVICE_HOST/g" "$script_path"
    sed -i "s/__SERVICE_PORT__/$SERVICE_PORT/g" "$script_path"
    
    # 设置执行权限
    chmod +x "$script_path"
    
    log_success "管理脚本已创建: $script_path"
}

# 显示安装完成信息
show_completion_summary() {
    echo ""
    echo "======================================================"
    log_success "🎉 Tegrastats API 安装完成!"
    echo "======================================================"
    echo ""
    log_info "安装信息:"
    echo "  📦 Conda环境: $CONDA_ENV_NAME"
    echo "  🚀 系统服务: $SERVICE_NAME"
    echo "  🌐 API地址: http://$SERVICE_HOST:$SERVICE_PORT"
    echo "  📊 健康检查: http://$SERVICE_HOST:$SERVICE_PORT/api/health"
    echo ""
    log_info "管理命令:"
    echo "  ./manage_tegrastats.sh start     # 启动服务"
    echo "  ./manage_tegrastats.sh stop      # 停止服务"
    echo "  ./manage_tegrastats.sh restart   # 重启服务"
    echo "  ./manage_tegrastats.sh status    # 查看状态"
    echo "  ./manage_tegrastats.sh logs      # 查看日志"
    echo "  ./manage_tegrastats.sh test      # 测试API"
    echo ""
    log_info "系统命令:"
    echo "  sudo systemctl status $SERVICE_NAME    # 查看服务状态"
    echo "  sudo systemctl restart $SERVICE_NAME   # 重启服务"
    echo "  sudo journalctl -u $SERVICE_NAME -f    # 查看实时日志"
    echo ""
    log_info "API端点:"
    echo "  GET /api/health        # 健康检查"
    echo "  GET /api/status        # 完整系统状态"
    echo "  GET /api/cpu           # CPU信息"
    echo "  GET /api/memory        # 内存信息"
    echo "  GET /api/temperature   # 温度信息"
    echo "  GET /api/power         # 功耗信息"
    echo ""
    log_info "卸载:"
    echo "  如需卸载，请运行: ./uninstall.sh"
    echo ""
    echo "======================================================"
    log_success "✅ 服务已启动并设置为开机自启动"
    echo "======================================================"
}

# 主安装流程
main() {
    echo "======================================================"
    echo "       Tegrastats API 一键安装脚本 v1.0"
    echo "======================================================"
    echo ""
    log_info "此脚本将自动完成以下操作:"
    echo "  1. 检查系统要求"
    echo "  2. 初始化conda环境"
    echo "  3. 创建专用conda环境 ($CONDA_ENV_NAME)"
    echo "  4. 安装Python包和依赖"
    echo "  5. 创建systemd服务"
    echo "  6. 启动服务并验证"
    echo "  7. 创建管理脚本"
    echo ""
    log_info "配置信息:"
    echo "  • 服务地址: $SERVICE_HOST:$SERVICE_PORT"
    echo "  • Conda环境: $CONDA_ENV_NAME"
    echo "  • Python版本: $PYTHON_VERSION"
    echo ""
    
    read -p "是否继续安装? [Y/n]: " -r
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_info "安装已取消"
        exit 0
    fi
    
    echo ""
    
    # 执行安装步骤
    check_requirements
    init_conda
    setup_conda_env
    install_package
    create_service
    start_and_verify_service
    create_management_script
    
    # 显示完成信息
    show_completion_summary
}

# 错误处理
handle_error() {
    log_error "安装过程中发生错误: $1"
    log_info "请检查错误信息并重试"
    
    # 清理操作
    log_info "执行清理操作..."
    
    # 停止服务（如果已创建）
    if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
        sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
        sudo systemctl daemon-reload
    fi
    
    exit 1
}

# 设置错误处理
trap 'handle_error "第$STEP步执行失败"' ERR

# 解析命令行参数
SERVICE_HOST="$DEFAULT_HOST"
SERVICE_PORT="$DEFAULT_PORT"

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            SERVICE_HOST="$2"
            shift 2
            ;;
        --port)
            SERVICE_PORT="$2"
            shift 2
            ;;
        --env-name)
            CONDA_ENV_NAME="$2"
            shift 2
            ;;
        --python)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
done

# 运行主程序
main "$@"