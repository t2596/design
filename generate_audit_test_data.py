#!/usr/bin/env python3
"""
生成审计日志测试数据

此脚本会：
1. 注册几个测试车辆（生成认证成功日志）
2. 发送一些车辆数据（生成数据传输日志）
3. 颁发和撤销证书（生成证书操作日志）
"""

import requests
import json
import time
from datetime import datetime

# 配置
GATEWAY_URL = "http://8.147.67.31:32620"
TOKEN = "dev-token-12345"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def register_vehicle(vehicle_id):
    """注册车辆"""
    print(f"注册车辆: {vehicle_id}")
    
    url = f"{GATEWAY_URL}/api/auth/register"
    data = {
        "vehicle_id": vehicle_id,
        "certificate_serial": f"CERT_{vehicle_id}",
        "public_key": "0" * 128  # 模拟公钥
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"  ✓ 注册成功，会话ID: {result['session_id']}")
            return result
        else:
            print(f"  ✗ 注册失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"  ✗ 注册异常: {e}")
        return None

def send_vehicle_data(vehicle_id, session_id):
    """发送车辆数据"""
    print(f"发送车辆数据: {vehicle_id}")
    
    url = f"{GATEWAY_URL}/api/auth/data"
    params = {
        "vehicle_id": vehicle_id,
        "session_id": session_id
    }
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "state": "running",
        "gps": {
            "latitude": 39.9042,
            "longitude": 116.4074,
            "altitude": 50.0,
            "heading": 90.0,
            "satellites": 12
        },
        "motion": {
            "speed": 60.5,
            "acceleration": 0.5,
            "odometer": 12345.6,
            "trip_distance": 123.4
        },
        "fuel": {
            "level": 75.5,
            "consumption": 8.5,
            "range": 450.0
        },
        "temperature": {
            "engine": 85.0,
            "cabin": 22.0,
            "outside": 18.0
        },
        "battery": {
            "voltage": 12.6,
            "current": 5.2
        },
        "diagnostics": {
            "engine_load": 45.0,
            "rpm": 2500,
            "throttle_position": 30.0
        }
    }
    
    try:
        response = requests.post(url, params=params, json=data, headers=headers)
        if response.status_code == 200:
            print(f"  ✓ 数据发送成功")
            return True
        else:
            print(f"  ✗ 数据发送失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ✗ 数据发送异常: {e}")
        return False

def issue_certificate(vehicle_id):
    """颁发证书"""
    print(f"颁发证书: {vehicle_id}")
    
    url = f"{GATEWAY_URL}/api/certificates/issue"
    data = {
        "vehicle_id": vehicle_id,
        "organization": "Test Manufacturer",
        "country": "CN",
        "public_key": "0" * 128  # 模拟公钥
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"  ✓ 证书颁发成功，序列号: {result['serial_number']}")
            return result['serial_number']
        else:
            print(f"  ✗ 证书颁发失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"  ✗ 证书颁发异常: {e}")
        return None

def revoke_certificate(serial_number):
    """撤销证书"""
    print(f"撤销证书: {serial_number}")
    
    url = f"{GATEWAY_URL}/api/certificates/revoke"
    data = {
        "serial_number": serial_number,
        "reason": "测试撤销"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"  ✓ 证书撤销成功")
            return True
        else:
            print(f"  ✗ 证书撤销失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ✗ 证书撤销异常: {e}")
        return False

def main():
    print("=" * 60)
    print("生成审计日志测试数据")
    print("=" * 60)
    print()
    
    # 测试车辆列表
    test_vehicles = [
        "VIN_TEST_001",
        "VIN_TEST_002",
        "VIN_TEST_003"
    ]
    
    sessions = {}
    
    # 1. 注册车辆
    print("\n--- 步骤 1: 注册车辆 ---")
    for vehicle_id in test_vehicles:
        result = register_vehicle(vehicle_id)
        if result:
            sessions[vehicle_id] = result['session_id']
        time.sleep(0.5)
    
    # 2. 发送车辆数据
    print("\n--- 步骤 2: 发送车辆数据 ---")
    for vehicle_id, session_id in sessions.items():
        send_vehicle_data(vehicle_id, session_id)
        time.sleep(0.5)
    
    # 3. 颁发证书
    print("\n--- 步骤 3: 颁发证书 ---")
    cert_serials = []
    for vehicle_id in test_vehicles[:2]:  # 只为前两个车辆颁发证书
        serial = issue_certificate(vehicle_id)
        if serial:
            cert_serials.append(serial)
        time.sleep(0.5)
    
    # 4. 撤销证书
    print("\n--- 步骤 4: 撤销证书 ---")
    if cert_serials:
        revoke_certificate(cert_serials[0])  # 撤销第一个证书
    
    print("\n" + "=" * 60)
    print("测试数据生成完成")
    print("=" * 60)
    print("\n现在可以运行 test_audit_logs_api.sh 来验证审计日志功能")

if __name__ == "__main__":
    main()
