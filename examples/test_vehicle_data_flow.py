#!/usr/bin/env python3
"""测试车辆数据完整流程

验证从客户端到数据库到 Web 界面的完整数据流。
"""

import os
import sys
import time
import requests
from datetime import datetime

# 配置
GATEWAY_HOST = os.getenv("GATEWAY_HOST", "localhost")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8000"))
API_TOKEN = os.getenv("API_TOKEN", "dev-token-12345")
VEHICLE_ID = "TEST_FLOW_001"

BASE_URL = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}"


def test_certificate_issue():
    """测试证书颁发"""
    print("\n1. 测试证书颁发...")
    
    response = requests.post(
        f"{BASE_URL}/api/certificates/issue",
        json={
            "vehicle_id": VEHICLE_ID,
            "organization": "Test Org",
            "country": "CN",
            "public_key": "0" * 128  # 模拟公钥
        },
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        cert = response.json()
        print(f"✓ 证书颁发成功: {cert['serial_number']}")
        return cert['serial_number']
    else:
        print(f"✗ 证书颁发失败: {response.status_code} - {response.text}")
        return None


def test_vehicle_register(cert_serial):
    """测试车辆注册"""
    print("\n2. 测试车辆注册...")
    
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "vehicle_id": VEHICLE_ID,
            "certificate_serial": cert_serial
        },
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ 车辆注册成功: {result['session_id']}")
        return result['session_id']
    else:
        print(f"✗ 车辆注册失败: {response.status_code} - {response.text}")
        return None


def test_send_vehicle_data(session_id):
    """测试发送车辆数据"""
    print("\n3. 测试发送车辆数据...")
    
    vehicle_data = {
        "vehicle_id": VEHICLE_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "state": "巡航",
        "gps": {
            "latitude": 39.9042,
            "longitude": 116.4074,
            "altitude": 50.0,
            "heading": 90.0,
            "satellites": 12
        },
        "motion": {
            "speed": 80.5,
            "acceleration": 0.5,
            "odometer": 12345,
            "trip_distance": 25.3
        },
        "fuel": {
            "level": 65.5,
            "consumption": 8.2,
            "range": 393.0
        },
        "temperature": {
            "engine": 85.5,
            "cabin": 22.0,
            "outside": 18.5
        },
        "battery": {
            "voltage": 12.6,
            "current": 15.2
        },
        "diagnostics": {
            "engine_load": 45.5,
            "rpm": 2500,
            "throttle_position": 35.0
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/auth/data",
        params={
            "vehicle_id": VEHICLE_ID,
            "session_id": session_id
        },
        json=vehicle_data,
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ 数据发送成功: {result['timestamp']}")
        return True
    else:
        print(f"✗ 数据发送失败: {response.status_code} - {response.text}")
        return False


def test_query_online_vehicles():
    """测试查询在线车辆"""
    print("\n4. 测试查询在线车辆...")
    
    response = requests.get(
        f"{BASE_URL}/api/vehicles/online",
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        vehicles = response.json()
        print(f"✓ 在线车辆数量: {len(vehicles)}")
        
        # 查找测试车辆
        test_vehicle = next((v for v in vehicles if v['vehicle_id'] == VEHICLE_ID), None)
        if test_vehicle:
            print(f"✓ 找到测试车辆: {VEHICLE_ID}")
            return True
        else:
            print(f"✗ 未找到测试车辆: {VEHICLE_ID}")
            return False
    else:
        print(f"✗ 查询在线车辆失败: {response.status_code} - {response.text}")
        return False


def test_query_vehicle_data():
    """测试查询车辆数据"""
    print("\n5. 测试查询车辆数据...")
    
    # 查询最新数据
    response = requests.get(
        f"{BASE_URL}/api/vehicles/{VEHICLE_ID}/data/latest",
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ 查询最新数据成功")
        print(f"  - 时间戳: {data.get('timestamp')}")
        print(f"  - 状态: {data.get('state')}")
        print(f"  - 速度: {data.get('motion', {}).get('speed')} km/h")
        print(f"  - 位置: ({data.get('gps', {}).get('latitude')}, {data.get('gps', {}).get('longitude')})")
        return True
    else:
        print(f"✗ 查询车辆数据失败: {response.status_code} - {response.text}")
        return False


def main():
    """主函数"""
    print("="*60)
    print("车辆数据完整流程测试")
    print("="*60)
    print(f"Gateway: {BASE_URL}")
    print(f"Vehicle ID: {VEHICLE_ID}")
    
    try:
        # 1. 颁发证书
        cert_serial = test_certificate_issue()
        if not cert_serial:
            print("\n✗ 测试失败：无法颁发证书")
            return 1
        
        time.sleep(1)
        
        # 2. 注册车辆
        session_id = test_vehicle_register(cert_serial)
        if not session_id:
            print("\n✗ 测试失败：无法注册车辆")
            return 1
        
        time.sleep(1)
        
        # 3. 发送车辆数据
        if not test_send_vehicle_data(session_id):
            print("\n✗ 测试失败：无法发送车辆数据")
            return 1
        
        time.sleep(2)
        
        # 4. 查询在线车辆
        if not test_query_online_vehicles():
            print("\n✗ 测试失败：无法查询在线车辆")
            return 1
        
        time.sleep(1)
        
        # 5. 查询车辆数据
        if not test_query_vehicle_data():
            print("\n✗ 测试失败：无法查询车辆数据")
            return 1
        
        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60)
        print("\n提示：现在可以在 Web 界面查看车辆数据")
        print(f"  - 访问 Web 界面")
        print(f"  - 查看在线车辆列表")
        print(f"  - 点击车辆 {VEHICLE_ID} 查看详细数据")
        
        return 0
        
    except requests.exceptions.ConnectionError:
        print(f"\n✗ 无法连接到 Gateway: {BASE_URL}")
        print("请确保 Gateway 服务正在运行")
        return 1
    except Exception as e:
        print(f"\n✗ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
