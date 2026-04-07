#!/usr/bin/env python3
"""测试审计日志功能

验证审计日志是否正常工作：
1. 查询审计日志
2. 检查证书操作是否记录
3. 导出审计报告
"""

import os
import sys
import requests
from datetime import datetime, timedelta

# 配置
GATEWAY_HOST = os.getenv("GATEWAY_HOST", "localhost")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8000"))
API_TOKEN = os.getenv("API_TOKEN", "dev-token-12345")

BASE_URL = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}"


def test_query_audit_logs():
    """测试 1: 查询审计日志"""
    print("\n" + "="*60)
    print("测试 1: 查询审计日志")
    print("="*60)
    
    print("\n1. 查询所有审计日志...")
    response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ 查询成功")
        print(f"  - 总记录数: {data['total']}")
        
        if data['total'] > 0:
            print(f"\n最近的 5 条日志:")
            for log in data['logs'][:5]:
                print(f"  - [{log['timestamp']}] {log['event_type']}: {log['vehicle_id']} - {log['details']}")
            return True
        else:
            print("  ⚠ 没有审计日志记录")
            return False
    else:
        print(f"✗ 查询失败: {response.status_code} - {response.text}")
        return False


def test_query_by_event_type():
    """测试 2: 按事件类型查询"""
    print("\n" + "="*60)
    print("测试 2: 按事件类型查询")
    print("="*60)
    
    event_types = [
        "CERTIFICATE_ISSUED",
        "CERTIFICATE_REVOKED",
        "AUTHENTICATION_SUCCESS",
        "AUTHENTICATION_FAILURE"
    ]
    
    for event_type in event_types:
        print(f"\n查询事件类型: {event_type}")
        response = requests.get(
            f"{BASE_URL}/api/audit/logs",
            params={"event_type": event_type, "limit": 10},
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ 找到 {data['total']} 条记录")
        else:
            print(f"  ✗ 查询失败: {response.status_code}")
    
    return True


def test_query_by_vehicle():
    """测试 3: 按车辆 ID 查询"""
    print("\n" + "="*60)
    print("测试 3: 按车辆 ID 查询")
    print("="*60)
    
    # 先获取一个车辆 ID
    response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        params={"limit": 1},
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data['total'] > 0:
            vehicle_id = data['logs'][0]['vehicle_id']
            print(f"\n查询车辆: {vehicle_id}")
            
            response2 = requests.get(
                f"{BASE_URL}/api/audit/logs",
                params={"vehicle_id": vehicle_id},
                headers={"Authorization": f"Bearer {API_TOKEN}"}
            )
            
            if response2.status_code == 200:
                data2 = response2.json()
                print(f"  ✓ 找到 {data2['total']} 条记录")
                return True
            else:
                print(f"  ✗ 查询失败")
                return False
        else:
            print("  ⚠ 没有日志记录可供测试")
            return None
    else:
        print(f"✗ 查询失败")
        return False


def test_query_by_time_range():
    """测试 4: 按时间范围查询"""
    print("\n" + "="*60)
    print("测试 4: 按时间范围查询")
    print("="*60)
    
    # 查询最近 24 小时的日志
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    print(f"\n查询时间范围: {start_time.isoformat()} 至 {end_time.isoformat()}")
    
    response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        params={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        },
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ 找到 {data['total']} 条记录")
        return True
    else:
        print(f"  ✗ 查询失败: {response.status_code}")
        return False


def test_export_json_report():
    """测试 5: 导出 JSON 报告"""
    print("\n" + "="*60)
    print("测试 5: 导出 JSON 报告")
    print("="*60)
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    print(f"\n导出最近 7 天的审计报告（JSON 格式）...")
    
    response = requests.get(
        f"{BASE_URL}/api/audit/export",
        params={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "format": "json"
        },
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        print(f"  ✓ 导出成功")
        print(f"  - 内容长度: {len(response.text)} 字节")
        
        # 保存到文件
        filename = f"audit_report_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"  - 已保存到: {filename}")
        
        return True
    else:
        print(f"  ✗ 导出失败: {response.status_code} - {response.text}")
        return False


def test_export_csv_report():
    """测试 6: 导出 CSV 报告"""
    print("\n" + "="*60)
    print("测试 6: 导出 CSV 报告")
    print("="*60)
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    print(f"\n导出最近 7 天的审计报告（CSV 格式）...")
    
    response = requests.get(
        f"{BASE_URL}/api/audit/export",
        params={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "format": "csv"
        },
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        print(f"  ✓ 导出成功")
        print(f"  - 内容长度: {len(response.text)} 字节")
        
        # 保存到文件
        filename = f"audit_report_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.csv"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"  - 已保存到: {filename}")
        
        # 显示前几行
        lines = response.text.split('\n')
        print(f"\n  CSV 内容预览（前 5 行）:")
        for line in lines[:5]:
            print(f"    {line}")
        
        return True
    else:
        print(f"  ✗ 导出失败: {response.status_code} - {response.text}")
        return False


def test_certificate_operation_logging():
    """测试 7: 验证证书操作是否记录审计日志"""
    print("\n" + "="*60)
    print("测试 7: 验证证书操作是否记录审计日志")
    print("="*60)
    
    print("\n1. 颁发一个测试证书...")
    
    # 生成测试公钥
    from src.crypto.sm2 import generate_sm2_keypair
    _, public_key = generate_sm2_keypair()
    
    response = requests.post(
        f"{BASE_URL}/api/certificates/issue",
        json={
            "vehicle_id": f"TEST_AUDIT_{int(datetime.utcnow().timestamp())}",
            "organization": "Test Org",
            "country": "CN",
            "public_key": public_key.hex()
        },
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        cert_data = response.json()
        serial_number = cert_data['serial_number']
        print(f"  ✓ 证书颁发成功: {serial_number}")
        
        # 等待一下确保日志已写入
        import time
        time.sleep(2)
        
        # 查询审计日志
        print(f"\n2. 查询证书颁发的审计日志...")
        response2 = requests.get(
            f"{BASE_URL}/api/audit/logs",
            params={"event_type": "CERTIFICATE_ISSUED", "limit": 10},
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        
        if response2.status_code == 200:
            data = response2.json()
            
            # 检查是否有刚才颁发的证书的日志
            found = False
            for log in data['logs']:
                if serial_number in log['details']:
                    found = True
                    print(f"  ✓ 找到审计日志:")
                    print(f"    - 时间: {log['timestamp']}")
                    print(f"    - 事件: {log['event_type']}")
                    print(f"    - 详情: {log['details']}")
                    break
            
            if found:
                return True
            else:
                print(f"  ⚠ 未找到证书 {serial_number} 的审计日志")
                print(f"  提示: 证书操作可能没有记录审计日志")
                return False
        else:
            print(f"  ✗ 查询审计日志失败")
            return False
    else:
        print(f"  ✗ 证书颁发失败: {response.status_code} - {response.text}")
        return False


def check_database_audit_logs():
    """测试 8: 直接检查数据库中的审计日志"""
    print("\n" + "="*60)
    print("测试 8: 检查数据库中的审计日志")
    print("="*60)
    
    print("\n提示: 可以使用以下命令直接查询数据库:")
    print("\nkubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \\")
    print("  psql -U gateway_user -d gateway_db -c \"SELECT COUNT(*) FROM audit_logs;\"")
    print("\nkubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \\")
    print("  psql -U gateway_user -d gateway_db -c \"SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;\"")
    
    return None


def main():
    """主函数"""
    print("="*60)
    print("审计日志功能测试")
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
    
    # 运行测试
    results = []
    
    results.append(("查询审计日志", test_query_audit_logs()))
    results.append(("按事件类型查询", test_query_by_event_type()))
    results.append(("按车辆 ID 查询", test_query_by_vehicle()))
    results.append(("按时间范围查询", test_query_by_time_range()))
    results.append(("导出 JSON 报告", test_export_json_report()))
    results.append(("导出 CSV 报告", test_export_csv_report()))
    results.append(("证书操作日志", test_certificate_operation_logging()))
    check_database_audit_logs()
    
    # 显示结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for test_name, result in results:
        if result is None:
            status = "⊘ 跳过"
        elif result:
            status = "✓ 通过"
        else:
            status = "✗ 失败"
        print(f"{test_name}: {status}")
    
    # 过滤掉 None 结果
    valid_results = [r for _, r in results if r is not None]
    
    if valid_results and all(valid_results):
        print("\n✓ 所有测试通过！审计日志功能正常工作")
        return 0
    elif not valid_results or not any(valid_results):
        print("\n✗ 所有测试失败！审计日志功能可能未正常工作")
        print("\n可能的原因:")
        print("1. 数据库中没有审计日志记录")
        print("2. 审计日志 API 未正确实现")
        print("3. 关键操作未调用审计日志记录功能")
        return 1
    else:
        print("\n⚠ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
