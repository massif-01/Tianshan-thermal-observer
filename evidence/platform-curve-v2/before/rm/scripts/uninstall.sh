#!/bin/bash

# Tegrastats API 卸载脚本
# 完全移除Python包、systemd服务、配置文件和虚拟环境

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 服务配置
SERVICE_NAME="tegrastats-api"
SERVICE_FILE="${SERVICE_NAME}.service"
PACKAGE_NAME="tegrastats-api"
CONDA_ENV_NAME="tegrastats-api-test"  # 更新为实际环境名

# 检测当前安装情况
detect_installation() {
    log_info "检测当前安装情况..."
    
    # 检测Python包
    local package_installed=false
    if pip show ${PACKAGE_NAME} &> /dev/null; then
        package_installed=true
        log_success "✓ Python包已安装: ${PACKAGE_NAME}"
    else
        log_warning "✗ Python包未安装: ${PACKAGE_NAME}"
    fi
    
    # 检测systemd服务
    local service_installed=false
    if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
        service_installed=true
        if systemctl is-active --quiet ${SERVICE_NAME}; then
            log_success "✓ systemd服务正在运行: ${SERVICE_NAME}"
        else
            log_info "◯ systemd服务已安装但未运行: ${SERVICE_NAME}"
        fi
    else
        log_warning "✗ systemd服务未安装: ${SERVICE_NAME}"
    fi
    
    # 检测环境类型
    local service_file="/etc/systemd/system/${SERVICE_FILE}" 
    if [[ -f "$service_file" ]]; then
        local env_path=$(grep "ExecStart=" "$service_file" | sed 's/.*ExecStart=\([^[:space:]]*\)\/bin\/tegrastats-api.*/\1/')
        if [[ "$env_path" =~ envs ]]; then
            local env_name=$(basename "$env_path")
            if [[ "$env_name" == "base" ]]; then
                log_info "◯ 使用conda base环境"
            else
                log_info "◯ 使用conda专用环境: $env_name"
            fi
        elif [[ "$env_path" =~ miniconda3$ ]]; then
            log_info "◯ 使用conda base环境"
        else
            log_info "◯ 使用系统Python或其他环境"
        fi
    fi
    
    return 0
}

# 确认卸载
confirm_uninstall() {
    echo "======================================================"
    echo "       Tegrastats API 卸载脚本 v1.0"
    echo "======================================================"
    echo ""
    
    # 检测当前安装情况
    detect_installation
    echo ""
    
    log_warning "此操作将移除以下内容:"
    echo "  • Python包 (${PACKAGE_NAME})"
    echo "  • systemd服务 (${SERVICE_NAME})"
    echo "  • 服务配置文件 (/etc/systemd/system/${SERVICE_FILE})"
    echo "  • CLI命令和可执行文件"
    echo "  • 管理脚本和日志文件"
    echo "  • Python缓存和临时文件"
    echo ""
    log_info "conda环境处理策略:"
    echo "  • 如果使用专用环境：将询问是否删除"
    echo "  • 如果使用base或现有环境：仅移除包，保留环境"
    echo ""
    log_warning "注意: 项目源代码将被保留"
    echo ""
    
    read -p "您确定要继续卸载吗? [y/N]: " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "卸载已取消"
        exit 0
    fi
    echo ""
}

# 卸载Python包
uninstall_python_package() {
    log_info "卸载Python包..."
    
    # 检查包是否已安装
    if pip show ${PACKAGE_NAME} &> /dev/null; then
        log_info "正在卸载Python包: ${PACKAGE_NAME}"
        pip uninstall ${PACKAGE_NAME} -y || log_warning "卸载Python包时出现错误"
        log_success "Python包已卸载"
    else
        log_warning "Python包未安装: ${PACKAGE_NAME}"
    fi
    
    # 检查并清理CLI命令
    local cli_commands=("tegrastats-api" "tegrastats-parser" "tegrastats-server")
    for cmd in "${cli_commands[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            local cmd_path=$(which "$cmd")
            log_info "发现CLI命令: $cmd ($cmd_path)"
            # CLI命令通常会随包卸载自动删除，这里只是记录
        fi
    done
}

# 停止和禁用服务
stop_and_disable_service() {
    log_info "停止和禁用服务..."
    
    # 检查服务是否存在
    if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
        # 停止服务
        if systemctl is-active --quiet ${SERVICE_NAME}; then
            log_info "正在停止服务..."
            sudo systemctl stop ${SERVICE_NAME} || log_warning "停止服务时出现错误"
        fi
        
        # 禁用服务
        if systemctl is-enabled --quiet ${SERVICE_NAME}; then
            log_info "正在禁用开机自启动..."
            sudo systemctl disable ${SERVICE_NAME} || log_warning "禁用服务时出现错误"
        fi
        
        log_success "服务已停止并禁用"
    else
        log_warning "服务不存在，跳过停止操作"
    fi
}

# 移除systemd服务文件
remove_service_file() {
    log_info "移除systemd服务文件..."
    
    local service_path="/etc/systemd/system/${SERVICE_FILE}"
    
    if [[ -f "$service_path" ]]; then
        sudo rm -f "$service_path"
        log_success "服务文件已删除: $service_path"
        
        # 重载systemd
        sudo systemctl daemon-reload
        log_success "systemd配置已重载"
    else
        log_warning "服务文件不存在: $service_path"
    fi
}

# 检测并移除conda虚拟环境
remove_conda_env() {
    log_info "检查Python环境配置..."
    
    # 从systemd服务文件中检测实际使用的环境
    local service_file="/etc/systemd/system/${SERVICE_FILE}"
    local detected_env=""
    local env_path=""
    
    if [[ -f "$service_file" ]]; then
        # 从服务文件中提取Python路径
        env_path=$(grep "ExecStart=" "$service_file" | sed 's/.*ExecStart=\([^[:space:]]*\)\/bin\/tegrastats-api.*/\1/')
        if [[ -n "$env_path" && "$env_path" =~ envs ]]; then
            detected_env=$(basename "$env_path")
            log_info "从服务文件检测到环境: $detected_env"
            log_info "环境路径: $env_path"
        fi
    fi
    
    # 初始化conda
    if command -v conda &> /dev/null; then
        # 尝试初始化conda
        source "$HOME/miniconda3/etc/profile.d/conda.sh" 2>/dev/null || {
            eval "$($HOME/miniconda3/bin/conda shell.bash hook)" 2>/dev/null || {
                log_warning "无法初始化conda环境"
                return 0
            }
        }
        
        # 如果检测到了环境，询问是否删除
        if [[ -n "$detected_env" ]]; then
            # 检查是否是常见的基础环境
            if [[ "$detected_env" == "base" ]]; then
                log_info "检测到使用base环境，不会删除"
                log_info "只卸载Python包，保留环境"
                return 0
            fi
            
            # 检查环境是否存在
            if conda env list | grep -q "^${detected_env}"; then
                echo ""
                log_warning "检测到conda环境: $detected_env"
                log_warning "这个环境可能包含其他项目的依赖"
                echo ""
                read -p "是否删除整个conda环境 '$detected_env'? [y/N]: " -r
                
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    log_info "正在删除conda虚拟环境: ${detected_env}"
                    
                    # 先退出环境（如果当前在该环境中）
                    conda deactivate 2>/dev/null || true
                    
                    # 删除环境
                    conda env remove -n ${detected_env} -y
                    log_success "conda虚拟环境已删除: ${detected_env}"
                else
                    log_info "保留conda环境: ${detected_env}"
                    log_info "仅卸载了Python包，环境中的其他包保持不变"
                fi
            else
                log_warning "conda虚拟环境不存在: ${detected_env}"
            fi
        else
            # 回退到原来的逻辑
            if conda env list | grep -q "^${CONDA_ENV_NAME}"; then
                echo ""
                read -p "是否删除conda环境 '$CONDA_ENV_NAME'? [y/N]: " -r
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    log_info "正在删除conda虚拟环境: ${CONDA_ENV_NAME}"
                    conda deactivate 2>/dev/null || true
                    conda env remove -n ${CONDA_ENV_NAME} -y
                    log_success "conda虚拟环境已删除"
                fi
            else
                log_info "未检测到专用的conda环境，可能使用了现有环境"
                log_info "Python包已卸载，环境保持不变"
            fi
        fi
    else
        log_warning "未找到conda，跳过虚拟环境清理"
    fi
}

# 清理项目文件
cleanup_project_files() {
    log_info "清理项目临时文件..."
    
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # 清理Python缓存目录
    local cache_dirs=("__pycache__" "src/__pycache__" "src/tegrastats_api/__pycache__" "utils/__pycache__" ".pytest_cache" "build" "dist" "*.egg-info")
    
    for pattern in "${cache_dirs[@]}"; do
        for dir in $(find "$script_dir" -name "$pattern" -type d 2>/dev/null); do
            if [[ -d "$dir" ]]; then
                rm -rf "$dir"
                log_success "删除缓存目录: $(basename $dir)"
            fi
        done
    done
    
    # 清理日志文件
    local log_files=("app.log" "tegrastats-api.log" "server.log")
    for log_file in "${log_files[@]}"; do
        if [[ -f "$script_dir/$log_file" ]]; then
            rm -f "$script_dir/$log_file"
            log_success "删除日志文件: $log_file"
        fi
    done
    
    # 清理临时文件
    local temp_files=("/tmp/${SERVICE_FILE}" "/tmp/tegrastats-*")
    for temp_file in "${temp_files[@]}"; do
        if [[ -f "$temp_file" ]]; then
            rm -f "$temp_file"
            log_success "删除临时文件: $(basename $temp_file)"
        fi
    done
    
    # 清理编译文件
    find "$script_dir" -name "*.pyc" -delete 2>/dev/null || true
    find "$script_dir" -name "*.pyo" -delete 2>/dev/null || true
    
    log_success "项目临时文件清理完成"
}

# 移除管理脚本（可选）
remove_management_scripts() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local management_scripts=("manage_service.sh" "create_service.sh" "verify_installation.sh")
    
    echo ""
    read -p "是否删除管理脚本? [y/N]: " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for script in "${management_scripts[@]}"; do
            if [[ -f "$script_dir/$script" ]]; then
                rm -f "$script_dir/$script"
                log_success "已删除: $script"
            fi
        done
    else
        log_info "保留管理脚本"
    fi
}

# 检查残留进程
check_remaining_processes() {
    log_info "检查残留进程..."
    
    local process_patterns=("tegrastats-api" "python.*tegrastats" "tegrastats")
    local found_processes=()
    
    for pattern in "${process_patterns[@]}"; do
        local processes=$(ps aux | grep -E "$pattern" | grep -v grep | grep -v uninstall.sh)
        if [[ -n "$processes" ]]; then
            found_processes+=("$processes")
        fi
    done
    
    if [[ ${#found_processes[@]} -gt 0 ]]; then
        log_warning "发现可能的残留进程:"
        for proc in "${found_processes[@]}"; do
            echo "$proc"
        done
        echo ""
        
        read -p "是否终止这些进程? [y/N]: " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for proc in "${found_processes[@]}"; do
                local pids=$(echo "$proc" | awk '{print $2}')
                for pid in $pids; do
                    if kill -TERM "$pid" 2>/dev/null; then
                        log_info "已终止进程: $pid"
                        sleep 2
                        # 如果进程仍然存在，强制终止
                        if kill -0 "$pid" 2>/dev/null; then
                            kill -KILL "$pid" 2>/dev/null
                            log_warning "强制终止进程: $pid"
                        fi
                    fi
                done
            done
        fi
    else
        log_success "未发现残留进程"
    fi
}

# 显示卸载完成信息
show_uninstall_summary() {
    echo ""
    echo "======================================================"
    log_success "Tegrastats API 卸载完成!"
    echo "======================================================"
    echo ""
    log_info "已完成的操作:"
    echo "  ✅ 卸载Python包和CLI命令"
    echo "  ✅ 停止并禁用systemd服务"
    echo "  ✅ 删除服务配置文件"
    echo "  ✅ 移除conda虚拟环境"
    echo "  ✅ 清理临时文件和缓存"
    echo "  ✅ 检查并清理残留进程"
    echo ""
    log_info "保留的文件:"
    echo "  📁 项目源代码和配置文件"
    echo "  📁 ESP32S3示例代码"
    echo "  📁 文档和README文件"
    echo ""
    log_warning "如需完全删除项目，请手动删除项目目录"
    echo ""
    
    # 验证卸载
    if ! systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
        log_success "服务卸载验证通过"
    else
        log_warning "服务可能未完全卸载，请检查"
    fi
    
    echo "======================================================"
}

# 备份配置文件（可选）
backup_configs() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local backup_dir="$script_dir/backup_$(date +%Y%m%d_%H%M%S)"
    
    read -p "是否备份配置文件? [y/N]: " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "创建配置备份..."
        
        mkdir -p "$backup_dir"
        
        # 备份主要配置文件
        [[ -f "$script_dir/config.py" ]] && cp "$script_dir/config.py" "$backup_dir/"
        [[ -f "$script_dir/requirements.txt" ]] && cp "$script_dir/requirements.txt" "$backup_dir/"
        [[ -f "/etc/systemd/system/${SERVICE_FILE}" ]] && sudo cp "/etc/systemd/system/${SERVICE_FILE}" "$backup_dir/"
        
        log_success "配置文件已备份到: $backup_dir"
    fi
}

# 主卸载流程
main() {
    # 确认卸载操作
    confirm_uninstall
    
    # 备份配置文件
    backup_configs
    
    # 执行卸载步骤
    stop_and_disable_service
    remove_service_file
    uninstall_python_package
    remove_conda_env
    cleanup_project_files
    check_remaining_processes
    remove_management_scripts
    
    # 显示卸载总结
    show_uninstall_summary
}

# 错误处理
trap 'log_error "卸载过程中发生错误"; exit 1' ERR

# 检查是否以root权限运行
if [[ $EUID -eq 0 ]]; then
    log_error "请不要以root用户运行此脚本"
    log_info "正确用法: ./uninstall.sh"
    exit 1
fi

# 运行主程序
main "$@"