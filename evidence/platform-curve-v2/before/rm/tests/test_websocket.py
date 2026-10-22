#!/usr/bin/env python3
"""
简单的WebSocket客户端测试脚本
用于测试tegrastats API的实时数据推送功能
"""

import socketio
import time
import json
from datetime import datetime

# 创建Socket.IO客户端
sio = socketio.Client()

print("正在连接到WebSocket服务器...")

# 接收数据的计数器
message_count = 0

def print_data_summary(data):
    """打印数据摘要"""
    global message_count
    message_count += 1
    
    print(f"\n--- 消息 #{message_count} ---")
    print(f"时间戳: {data.get('timestamp', 'N/A')}")
    
    # CPU信息
    if 'cpu' in data and 'cores' in data['cpu']:
        cores = data['cpu']['cores']
        avg_usage = sum(core['usage'] for core in cores) / len(cores)
        print(f"CPU: {len(cores)}核心, 平均使用率: {avg_usage:.1f}%")
    
    # 内存信息
    if 'memory' in data and 'ram' in data['memory']:
        ram = data['memory']['ram']
        usage_percent = (ram['used'] / ram['total']) * 100
        print(f"内存: {ram['used']}/{ram['total']}MB ({usage_percent:.1f}%)")
    
    # 温度信息
    if 'temperature' in data:
        temps = data['temperature']
        cpu_temp = temps.get('cpu', 'N/A')
        print(f"CPU温度: {cpu_temp}°C")
    
    # 功耗信息
    if 'power' in data:
        power = data['power']
        total_power = 0
        for component, info in power.items():
            if isinstance(info, dict) and 'current' in info:
                total_power += info['current']
        print(f"总功耗: {total_power/1000:.1f}W")

@sio.event
def connect():
    print("✅ WebSocket连接成功!")

@sio.event
def disconnect():
    print("WebSocket连接已断开")

@sio.event
def tegrastats_update(data):
    print_data_summary(data)

try:
    # 连接到服务器
    sio.connect('http://10.10.99.98:58090')
    
    # 持续接收数据
    print("等待实时数据... (按 Ctrl+C 停止)")
    print("=" * 50)
    
    try:
        while True:
            sio.sleep(1)  # 保持连接活跃
    except KeyboardInterrupt:
        print(f"\n\n✅ 用户中断，测试完成")
        print(f"总共接收到 {message_count} 条消息")
    
except Exception as e:
    print(f"❌ 连接失败: {e}")
finally:
    try:
        sio.disconnect()
        print("WebSocket连接已断开")
    except:
        pass