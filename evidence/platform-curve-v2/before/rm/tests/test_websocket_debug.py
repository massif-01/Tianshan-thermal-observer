#!/usr/bin/env python3
"""
详细的WebSocket测试脚本，用于诊断实时推送问题
"""

import socketio
import time
import json
from datetime import datetime

# 创建Socket.IO客户端，启用详细日志
sio = socketio.Client(logger=True, engineio_logger=True)

# 连接状态标志
connected = False
message_count = 0

@sio.event
def connect():
    global connected
    connected = True
    print("✅ WebSocket连接成功!")
    print(f"连接时间: {datetime.now().strftime('%H:%M:%S')}")

@sio.event
def disconnect():
    global connected
    connected = False
    print("❌ WebSocket连接断开")
    print(f"断开时间: {datetime.now().strftime('%H:%M:%S')}")

@sio.event
def status_update(data):
    global message_count
    message_count += 1
    current_time = datetime.now().strftime('%H:%M:%S')
    
    print(f"\n📊 消息 #{message_count} - {current_time}")
    print(f"时间戳: {data.get('timestamp', 'N/A')}")
    
    # 简化的数据显示
    if 'cpu' in data and 'cores' in data['cpu']:
        cores = data['cpu']['cores']
        avg_usage = sum(core['usage'] for core in cores) / len(cores)
        print(f"CPU平均使用率: {avg_usage:.1f}%")
    
    if 'memory' in data and 'ram' in data['memory']:
        ram = data['memory']['ram']
        usage_percent = (ram['used'] / ram['total']) * 100
        print(f"内存使用率: {usage_percent:.1f}%")
    
    if 'temperature' in data and 'cpu' in data['temperature']:
        print(f"CPU温度: {data['temperature']['cpu']:.1f}°C")

@sio.event
def connect_error(data):
    print(f"❌ 连接错误: {data}")

@sio.event
def error(data):
    print(f"❌ 错误事件: {data}")

def main():
    global connected, message_count
    
    print("🔄 开始WebSocket实时推送测试")
    print("服务器地址: http://10.10.99.98:5000")
    print("=" * 50)
    
    try:
        # 连接到服务器
        print("正在连接...")
        sio.connect('http://10.10.99.98:5000')
        
        # 等待连接建立
        timeout = 10
        wait_time = 0
        while not connected and wait_time < timeout:
            sio.sleep(0.1)
            wait_time += 0.1
        
        if not connected:
            print("❌ 连接超时")
            return
        
        print("\n🕐 等待实时数据推送...")
        print("预期: 每秒接收一次数据")
        print("实际: (按 Ctrl+C 停止)")
        print("-" * 50)
        
        # 记录开始时间
        start_time = time.time()
        last_message_time = start_time
        
        try:
            while True:
                sio.sleep(0.1)
                current_time = time.time()
                
                # 每5秒显示统计信息
                if int(current_time - start_time) % 5 == 0 and int(current_time - start_time) > 0:
                    elapsed = int(current_time - start_time)
                    expected_messages = elapsed
                    actual_rate = message_count / elapsed if elapsed > 0 else 0
                    
                    print(f"\n📈 统计 (运行 {elapsed}秒):")
                    print(f"   预期消息数: {expected_messages}")
                    print(f"   实际消息数: {message_count}")
                    print(f"   实际频率: {actual_rate:.2f} Hz")
                    
                    if message_count == 0:
                        print("⚠️  警告: 没有收到任何数据推送")
                    
                    time.sleep(1)  # 避免重复统计
                
        except KeyboardInterrupt:
            elapsed = time.time() - start_time
            print(f"\n\n✅ 测试完成")
            print(f"运行时长: {elapsed:.1f}秒")
            print(f"总消息数: {message_count}")
            print(f"平均频率: {message_count/elapsed:.2f} Hz" if elapsed > 0 else "0 Hz")
            
            if message_count == 0:
                print("\n❌ 问题: 没有收到任何WebSocket数据推送")
                print("可能原因:")
                print("1. 服务器端数据更新线程未启动")
                print("2. WebSocket事件名称不匹配")
                print("3. 服务器端推送逻辑有问题")
            elif message_count / elapsed < 0.8:
                print(f"\n⚠️  警告: 推送频率低于预期 (预期1Hz)")
    
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    
    finally:
        if connected:
            sio.disconnect()
            print("🔌 连接已关闭")

if __name__ == "__main__":
    main()