#!/usr/bin/env python3
"""
简化的WebSocket测试脚本
"""

import socketio
import time

sio = socketio.Client()
message_count = 0

@sio.event
def connect():
    print("✅ 连接成功")

@sio.event  
def disconnect():
    print("❌ 连接断开")

@sio.event
def tegrastats_update(data):
    global message_count
    message_count += 1
    timestamp = data.get('timestamp', 'N/A')
    print(f"📊 消息#{message_count}: {timestamp}")

try:
    print("连接到 http://10.10.99.98:58090")
    sio.connect('http://10.10.99.98:58090')
    
    print("等待15秒...")
    start_time = time.time()
    
    while time.time() - start_time < 15:
        sio.sleep(0.1)
    
    print(f"\n总共收到 {message_count} 条消息")
    print(f"实际频率: {message_count/15:.2f} Hz")
    
except Exception as e:
    print(f"错误: {e}")
finally:
    sio.disconnect()