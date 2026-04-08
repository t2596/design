#!/usr/bin/env python3
"""测试会话超时和优雅退出功能

验证：
1. 客户端正常退出时会自动注销
2. 后端会检测并清理超时会话
"""

import os
import sys
import time
import requests
import signal
import subprocess
from datetime import datetime

# 配置
GATEWAY_HOST = os.getenv("GATEWAY_HOST", "localhost")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8000"))
API_TOKEN = os.getenv("API_TOKEN", "dev-token-12345")

BASE_URL = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}"


def get_online_vehicles():
    """获取在线车辆列表"""
    response = requests.get(
        f"{BASE_URL}/api/vehicles/online",
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    if response.status_code == 200:
        return response.json()['vehicles']
    return []


def test_graceful_shutdown():
    """测试 1: 优雅退出（Ctrl+C）"""
    print("\n" + "="*60)
    print("测试 1: 客户端优雅退出")
    print("="*60)
    
    vehicle_id = "TEST_GRACEFUL_001"
    
    print(f"\n1. 启动客户端 {vehicle_id}...")
    
    # 启动客户端进程
    client_process = subprocess.Popen(
        [
            sys.executable,
            "client/vehicle_client.py",
            "--vehicle-id", vehicle_id,
            "--gateway-host", GATEWAY_HOST,
            "--gateway-port", str(GATEWAY_PORT),
            "--mode", "continuous",
            "--interval", "5"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待客户端启动并发送几次数据
    print("   等待客户端启动...")
    time.sleep(15)
    
    # 检查车辆是否在线
    print(f"\n2. 检查车辆是否在线...")
    vehicles = get_online_vehicles()
    vehicle_ids = [v['vehicle_id'] for v in vehicles]
    
    if vehicle_id in vehicle_ids:
        print(f"   ✓ 车辆 {vehicle_id} 在线")
    else:
        print(f"   ✗ 车辆 {vehicle_id} 不在线（测试失败）")
        client_process.terminate()
        return False
    
    # 发送 SIGINT（模拟 Ctrl+C）
    print(f"\n3. 发送 Ctrl+C 信号...")
    client_process.send_signal(signal.SIGINT)
    
    # 等待进程退出
    try:
        stdout, stderr = client_process.communicate(timeout=10)
        print("   客户端已退出")
        
        # 检查是否有注销消息
        if "车辆注销成功" in stdout or "车辆注销成功" in stderr:
            print("   ✓ 客户端执行了注销操作")
        else:
            print("   ⚠ 未检测到注销消息")
    except subprocess.TimeoutExpired:
        print("   ⚠ 客户端未在 10 秒内退出，强制终止")
        client_process.kill()
    
    # 立即检查车辆是否离线
    print(f"\n4. 检查车辆是否已离线...")
    time.sleep(2)
    vehicles = get_online_vehicles()
    vehicle_ids = [v['vehicle_id'] for v in vehicles]
    
    if vehicle_id not in vehicle_ids:
        print(f"   ✓ 车辆 {vehicle_id} 已离线（优雅退出成功）")
        return True
    else:
        print(f"   ✗ 车辆 {vehicle_id} 仍在线（优雅退出失败）")
        return False


def test_timeout_detection():
    """测试 2: 超时检测"""
    print("\n" + "="*60)
    print("测试 2: 会话超时检测")
    print("="*60)
    
    vehicle_id = "TEST_TIMEOUT_002"
    
    print(f"\n1. 注册车辆 {vehicle_id}（不发送数据）...")
    
    # 直接调用注册 API
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "vehicle_id": vehicle_id,
            "certificate_serial": "test-cert-002"
        },
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code != 200:
        print(f"   ✗ 注册失败: {response.text}")
        return False
    
    session_id = response.json()['session_id']
    print(f"   ✓ 注册成功，会话 ID: {session_id}")
    
    # 检查车辆是否在线
    print(f"\n2. 检查车辆是否在线...")
    time.sleep(2)
    vehicles = get_online_vehicles()
    vehicle_ids = [v['vehicle_id'] for v in vehicles]
    
    if vehicle_id in vehicle_ids:
        print(f"   ✓ 车辆 {vehicle_id} 在线")
    else:
        print(f"   ✗ 车辆 {vehicle_id} 不在线")
        return False
    
    # 等待超时（5 分钟 + 缓冲）
    timeout_seconds = 300
    buffer_seconds = 10
    wait_time = timeout_seconds + buffer_seconds
    
    print(f"\n3. 等待会话超时（{wait_time} 秒）...")
    print(f"   提示: 这需要约 {wait_time // 60} 分钟，请耐心等待...")
    
    # 显示倒计时
    for remaining in range(wait_time, 0, -30):
        print(f"   剩余 {remaining} 秒...")
        time.sleep(30)
    
    # 检查车辆是否已离线
    print(f"\n4. 检查车辆是否已离线...")
    vehicles = get_online_vehicles()
    vehicle_ids = [v['vehicle_id'] for v in vehicles]
    
    if vehicle_id not in vehicle_ids:
        print(f"   ✓ 车辆 {vehicle_id} 已离线（超时检测成功）")
        return True
    else:
        print(f"   ✗ 车辆 {vehicle_id} 仍在线（超时检测失败）")
        
        # 手动清理
        print(f"\n5. 手动注销车辆...")
        requests.post(
            f"{BASE_URL}/api/auth/unregister",
            params={"vehicle_id": vehicle_id, "session_id": session_id},
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        return False


def test_quick_timeout():
    """测试 3: 快速超时测试（修改后端超时时间为 60 秒后使用）"""
    print("\n" + "="*60)
    print("测试 3: 快速超时测试（需要修改后端超时时间）")
    print("="*60)
    
    print("\n提示: 此测试需要将后端超时时间改为 60 秒")
    print("修改 src/api/routes/vehicles.py 中的 timeout_seconds = 60")
    print("然后重新部署后端")
    
    choice = input("\n是否已修改并重新部署？(y/n): ")
    if choice.lower() != 'y':
        print("跳过此测试")
        return None
    
    vehicle_id = "TEST_QUICK_003"
    
    print(f"\n1. 注册车辆 {vehicle_id}...")
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "vehicle_id": vehicle_id,
            "certificate_serial": "test-cert-003"
        },
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code != 200:
        print(f"   ✗ 注册失败")
        return False
    
    print(f"   ✓ 注册成功")
    
    # 等待 70 秒
    print(f"\n2. 等待 70 秒...")
    for i in range(7):
        print(f"   {(7-i)*10} 秒...")
        time.sleep(10)
    
    # 检查是否离线
    print(f"\n3. 检查车辆是否已离线...")
    vehicles = get_online_vehicles()
    vehicle_ids = [v['vehicle_id'] for v in vehicles]
    
    if vehicle_id not in vehicle_ids:
        print(f"   ✓ 车辆 {vehicle_id} 已离线")
        return True
    else:
        print(f"   ✗ 车辆 {vehicle_id} 仍在线")
        return False


def main():
    """主函数"""
    print("="*60)
    print("会话超时和优雅退出功能测试")
    print("="*60)
    print(f"Gateway: {BASE_URL}")
    
    # 检查 Gateway 是否可访问
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"\n✗ Gateway 不可访问: {BASE_URL}")
            return 1
    except Exception as e:
        print(f"\n✗ 无法连接到 Gateway: {str(e)}")
        return 1
    
    print(f"✓ Gateway 可访问\n")
    
    # 测试选择
    print("请选择测试:")
    print("1. 测试优雅退出（约 30 秒）")
    print("2. 测试超时检测（约 5 分钟）")
    print("3. 快速超时测试（需要修改后端，约 70 秒）")
    print("4. 运行所有测试")
    
    choice = input("\n请输入选择 (1-4): ")
    
    results = []
    
    if choice == "1":
        results.append(("优雅退出", test_graceful_shutdown()))
    elif choice == "2":
        results.append(("超时检测", test_timeout_detection()))
    elif choice == "3":
        result = test_quick_timeout()
        if result is not None:
            results.append(("快速超时", result))
    elif choice == "4":
        results.append(("优雅退出", test_graceful_shutdown()))
        
        print("\n是否继续测试超时检测（需要 5 分钟）？(y/n): ")
        if input().lower() == 'y':
            results.append(("超时检测", test_timeout_detection()))
    else:
        print("无效选择")
        return 1
    
    # 显示结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
