#!/usr/bin/env python3
"""
测试认证失败锁定功能

此脚本会：
1. 设置较低的认证失败阈值（3次）
2. 模拟多次认证失败
3. 验证车辆被锁定
4. 等待锁定期过后验证可以再次认证
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

def update_security_policy(max_failures=3, lockout_duration=60):
    """更新安全策略"""
    print(f"设置安全策略: max_failures={max_failures}, lockout_duration={lockout_duration}秒")
    
    url = f"{GATEWAY_URL}/api/config/security"
    data = {
        "session_timeout": 86400,
        "certificate_validity": 365,
        "timestamp_tolerance": 300,
        "concurrent_session_strategy": "reject_new",
        "max_auth_failures": max_failures,
        "auth_failure_lockout_duration": lockout_duration
    }
    
    try:
        response = requests.put(url, json=data, headers=headers)
        if response.status_code == 200:
            print("  ✓ 安全策略更新成功")
            return True
        else:
            print(f"  ✗ 安全策略更新失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ✗ 安全策略更新异常: {e}")
        return False

def simulate_auth_failure(vehicle_id, attempt_num):
    """模拟认证失败（通过发送无效数据）"""
    print(f"  尝试 {attempt_num}: 模拟认证失败...")
    
    # 注意：这里我们需要一个会失败的API调用
    # 由于当前的register API比较宽松，我们使用数据库直接插入失败记录
    # 在实际环境中，应该有一个会验证并失败的认证端点
    
    url = f"{GATEWAY_URL}/api/auth/register"
    data = {
        "vehicle_id": vehicle_id,
        "public_key": "invalid_key"  # 无效的公钥
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        # 即使成功也算一次"尝试"
        print(f"    响应: {response.status_code}")
        return response.status_code
    except Exception as e:
        print(f"    异常: {e}")
        return None

def try_register_vehicle(vehicle_id):
    """尝试注册车辆"""
    print(f"尝试注册车辆: {vehicle_id}")
    
    url = f"{GATEWAY_URL}/api/auth/register"
    data = {
        "vehicle_id": vehicle_id,
        "public_key": "0" * 128  # 有效的公钥格式
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            print(f"  ✓ 注册成功")
            return True
        elif response.status_code == 403:
            print(f"  ✗ 注册被拒绝（车辆被锁定）")
            return False
        else:
            print(f"  ✗ 注册失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ✗ 注册异常: {e}")
        return False

def check_database_records():
    """检查数据库中的认证失败记录"""
    print("检查数据库中的认证失败记录...")
    # 这需要kubectl命令，在Python中调用
    import subprocess
    
    try:
        result = subprocess.run([
            "kubectl", "exec", "-it", "deployment/postgres", "-n", "vehicle-iot-gateway", "--",
            "psql", "-U", "postgres", "-d", "vehicle_iot_gateway", "-c",
            "SELECT vehicle_id, failure_count, locked_until FROM auth_failure_records;"
        ], capture_output=True, text=True)
        
        print(result.stdout)
    except Exception as e:
        print(f"  无法检查数据库: {e}")

def main():
    print("=" * 60)
    print("测试认证失败锁定功能")
    print("=" * 60)
    print()
    
    test_vehicle_id = "VIN_LOCKOUT_TEST_001"
    
    # 步骤 1: 设置安全策略
    print("\n--- 步骤 1: 设置安全策略 ---")
    if not update_security_policy(max_failures=3, lockout_duration=60):
        print("无法设置安全策略，测试终止")
        return
    
    time.sleep(1)
    
    # 步骤 2: 第一次尝试（应该成功）
    print("\n--- 步骤 2: 第一次注册尝试（应该成功） ---")
    try_register_vehicle(test_vehicle_id)
    
    time.sleep(1)
    
    # 步骤 3: 检查数据库记录
    print("\n--- 步骤 3: 检查数据库记录 ---")
    check_database_records()
    
    # 步骤 4: 模拟多次失败（通过直接操作数据库）
    print("\n--- 步骤 4: 模拟认证失败 ---")
    print("注意：由于当前API实现，我们需要手动在数据库中插入失败记录")
    print("请运行以下SQL命令来模拟失败：")
    print(f"""
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \\
  psql -U postgres -d vehicle_iot_gateway -c \\
  "INSERT INTO auth_failure_records (vehicle_id, failure_count, first_failure_at, last_failure_at, locked_until) 
   VALUES ('{test_vehicle_id}', 5, NOW(), NOW(), NOW() + INTERVAL '60 seconds') 
   ON CONFLICT (vehicle_id) DO UPDATE 
   SET failure_count = 5, locked_until = NOW() + INTERVAL '60 seconds';"
    """)
    
    input("\n按Enter键继续测试锁定功能...")
    
    # 步骤 5: 尝试注册（应该被拒绝）
    print("\n--- 步骤 5: 尝试注册被锁定的车辆（应该被拒绝） ---")
    try_register_vehicle(test_vehicle_id)
    
    # 步骤 6: 检查数据库记录
    print("\n--- 步骤 6: 再次检查数据库记录 ---")
    check_database_records()
    
    # 步骤 7: 等待锁定期过后
    print("\n--- 步骤 7: 等待锁定期过后 ---")
    print("等待60秒...")
    for i in range(60, 0, -10):
        print(f"  剩余 {i} 秒...")
        time.sleep(10)
    
    # 步骤 8: 再次尝试注册（应该成功）
    print("\n--- 步骤 8: 锁定期过后再次尝试注册（应该成功） ---")
    try_register_vehicle(test_vehicle_id)
    
    # 步骤 9: 恢复默认配置
    print("\n--- 步骤 9: 恢复默认安全策略 ---")
    update_security_policy(max_failures=5, lockout_duration=300)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n功能验证要点：")
    print("1. 安全策略能够成功更新")
    print("2. 认证失败记录能够正确记录")
    print("3. 达到失败阈值后车辆被锁定")
    print("4. 锁定期间拒绝认证请求")
    print("5. 锁定期过后可以再次认证")

if __name__ == "__main__":
    main()
