#!/bin/bash

# Tegrastats API 管理脚本

SERVICE_NAME="tegrastats-api"
SERVICE_HOST="0.0.0.0"
SERVICE_PORT="58090"

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
