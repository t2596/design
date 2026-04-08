"""性能监控演示

演示如何使用性能监控模块跟踪系统性能。
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import json
from src.performance_monitor import (
    get_performance_monitor,
    reset_performance_monitor,
    monitor_auth_performance,
    monitor_encrypt_performance,
    monitor_decrypt_performance,
    monitor_sign_performance,
    monitor_verify_performance,
    monitor_session_establish,
    monitor_session_query
)
from src.crypto.sm4 import sm4_encrypt, sm4_decrypt, generate_sm4_key
from src.crypto.sm2 import sm2_sign, sm2_verify, generate_sm2_keypair
from src.models.session import AuthResult, AuthToken
from datetime import datetime, timedelta


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_authentication_monitoring():
    """演示认证性能监控"""
    print_section("认证性能监控演示")
    
    # 创建带性能监控的认证函数
    @monitor_auth_performance
    def mock_authenticate(vehicle_id):
        """模拟认证过程"""
        time.sleep(0.1)  # 模拟认证延迟
        return AuthResult.create_success(
            AuthToken(
                vehicle_id=vehicle_id,
                issued_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=24),
                permissions={"data_transfer"},
                signature=b"mock_signature"
            ),
            generate_sm4_key(16)
        )
    
    # 执行多次认证
    print("\n执行 10 次认证...")
    for i in range(10):
        result = mock_authenticate(f"VEHICLE_{i:03d}")
        print(f"  认证 {i+1}: {'成功' if result.success else '失败'}")
    
    # 获取认证性能指标
    monitor = get_performance_monitor()
    metrics = monitor.get_auth_metrics()
    
    print("\n认证性能指标:")
    print(f"  总认证次数: {metrics['total_count']}")
    print(f"  成功次数: {metrics['success_count']}")
    print(f"  失败次数: {metrics['failure_count']}")
    print(f"  平均延迟: {metrics['avg_latency_ms']:.2f} ms")
    print(f"  最小延迟: {metrics['min_latency_ms']:.2f} ms")
    print(f"  最大延迟: {metrics['max_latency_ms']:.2f} ms")
    print(f"  TPS: {metrics['tps']:.2f}")
    print(f"  满足延迟要求 (< 500ms): {'✓' if metrics['meets_latency_requirement'] else '✗'}")
    print(f"  满足 TPS 要求 (≥ 100): {'✓' if metrics['meets_tps_requirement'] else '✗'}")


def demo_encryption_monitoring():
    """演示加密解密性能监控"""
    print_section("加密解密性能监控演示")
    
    # 生成密钥
    key = generate_sm4_key(16)
    
    # 创建带性能监控的加密解密函数
    @monitor_encrypt_performance
    def encrypt_data(data, k):
        return sm4_encrypt(data, k)
    
    @monitor_decrypt_performance
    def decrypt_data(data, k):
        return sm4_decrypt(data, k)
    
    # 执行多次加密解密
    print("\n执行 100 次加密解密操作（每次 10KB）...")
    data_size = 10 * 1024  # 10KB
    
    for i in range(100):
        plaintext = b"x" * data_size
        ciphertext = encrypt_data(plaintext, key)
        decrypted = decrypt_data(ciphertext, key)
        assert decrypted == plaintext
        
        if (i + 1) % 20 == 0:
            print(f"  完成 {i+1} 次操作")
    
    # 获取加密解密性能指标
    monitor = get_performance_monitor()
    metrics = monitor.get_encryption_metrics()
    
    print("\n加密解密性能指标:")
    print(f"  加密次数: {metrics['encrypt_count']}")
    print(f"  加密总字节数: {metrics['encrypt_total_bytes'] / (1024*1024):.2f} MB")
    print(f"  加密吞吐量: {metrics['encrypt_throughput_mbps']:.2f} MB/s")
    print(f"  解密次数: {metrics['decrypt_count']}")
    print(f"  解密总字节数: {metrics['decrypt_total_bytes'] / (1024*1024):.2f} MB")
    print(f"  解密吞吐量: {metrics['decrypt_throughput_mbps']:.2f} MB/s")
    print(f"  1KB 平均加密时间: {metrics['avg_encrypt_time_1kb_ms']:.2f} ms")
    print(f"  满足加密吞吐量要求 (≥ 100 MB/s): {'✓' if metrics['meets_encrypt_throughput_requirement'] else '✗'}")
    print(f"  满足解密吞吐量要求 (≥ 100 MB/s): {'✓' if metrics['meets_decrypt_throughput_requirement'] else '✗'}")
    print(f"  满足 1KB 延迟要求 (< 10ms): {'✓' if metrics['meets_1kb_latency_requirement'] else '✗'}")


def demo_signature_monitoring():
    """演示签名验签性能监控"""
    print_section("签名验签性能监控演示")
    
    # 生成密钥对
    private_key, public_key = generate_sm2_keypair()
    
    # 创建带性能监控的签名验签函数
    @monitor_sign_performance
    def sign_data(data, pk):
        return sm2_sign(data, pk)
    
    @monitor_verify_performance
    def verify_signature(data, sig, pk):
        return sm2_verify(data, sig, pk)
    
    # 执行多次签名验签
    print("\n执行 100 次签名验签操作...")
    data = b"Test data for signature performance"
    
    for i in range(100):
        signature = sign_data(data, private_key)
        result = verify_signature(data, signature, public_key)
        assert result is True
        
        if (i + 1) % 20 == 0:
            print(f"  完成 {i+1} 次操作")
    
    # 获取签名验签性能指标
    monitor = get_performance_monitor()
    metrics = monitor.get_signature_metrics()
    
    print("\n签名验签性能指标:")
    print(f"  签名次数: {metrics['sign_count']}")
    print(f"  签名速度: {metrics['sign_ops_per_second']:.2f} 次/秒")
    print(f"  验签次数: {metrics['verify_count']}")
    print(f"  验签速度: {metrics['verify_ops_per_second']:.2f} 次/秒")
    print(f"  满足签名性能要求 (≥ 1000 次/秒): {'✓' if metrics['meets_sign_requirement'] else '✗'}")
    print(f"  满足验签性能要求 (≥ 2000 次/秒): {'✓' if metrics['meets_verify_requirement'] else '✗'}")


def demo_session_monitoring():
    """演示会话管理性能监控"""
    print_section("会话管理性能监控演示")
    
    monitor = get_performance_monitor()
    
    # 模拟会话建立
    print("\n建立 100 个会话...")
    for i in range(100):
        with monitor_session_establish():
            time.sleep(0.001)  # 模拟会话建立延迟
        
        if (i + 1) % 20 == 0:
            print(f"  建立 {i+1} 个会话")
    
    # 模拟会话查询
    print("\n执行 100 次会话查询...")
    for i in range(100):
        with monitor_session_query():
            time.sleep(0.0001)  # 模拟会话查询延迟
        
        if (i + 1) % 20 == 0:
            print(f"  完成 {i+1} 次查询")
    
    # 模拟会话关闭
    print("\n关闭 50 个会话...")
    for i in range(50):
        monitor.record_session_close()
    
    # 获取会话管理性能指标
    metrics = monitor.get_session_metrics()
    
    print("\n会话管理性能指标:")
    print(f"  当前活跃会话数: {metrics['current_sessions']}")
    print(f"  最大并发会话数: {metrics['max_sessions']}")
    print(f"  会话建立次数: {metrics['establish_count']}")
    print(f"  平均建立时间: {metrics['avg_establish_time_ms']:.2f} ms")
    print(f"  会话查询次数: {metrics['query_count']}")
    print(f"  平均查询时间: {metrics['avg_query_time_ms']:.2f} ms")
    print(f"  满足并发会话要求 (≥ 10,000): {'✓' if metrics['meets_concurrent_requirement'] else '✗'}")
    print(f"  满足查询延迟要求 (< 5ms): {'✓' if metrics['meets_query_latency_requirement'] else '✗'}")
    print(f"  满足建立延迟要求 (< 100ms): {'✓' if metrics['meets_establish_latency_requirement'] else '✗'}")


def demo_comprehensive_monitoring():
    """演示综合性能监控"""
    print_section("综合性能监控演示")
    
    monitor = get_performance_monitor()
    
    # 获取所有性能指标
    all_metrics = monitor.get_all_metrics()
    
    print("\n所有性能指标:")
    print(json.dumps(all_metrics, indent=2, ensure_ascii=False))
    
    # 获取性能摘要
    summary = monitor.get_performance_summary()
    
    print("\n性能要求满足情况:")
    print(f"  所有要求是否满足: {'✓ 是' if summary['all_requirements_met'] else '✗ 否'}")
    print("\n各项要求状态:")
    for req_id, status in summary['requirements_status'].items():
        req_name = req_id.replace('_', ' ').title()
        print(f"  {req_name}: {'✓' if status else '✗'}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  车联网安全通信网关 - 性能监控演示")
    print("=" * 60)
    
    # 重置性能监控器
    reset_performance_monitor()
    
    # 演示各个模块的性能监控
    demo_authentication_monitoring()
    demo_encryption_monitoring()
    demo_signature_monitoring()
    demo_session_monitoring()
    demo_comprehensive_monitoring()
    
    print("\n" + "=" * 60)
    print("  演示完成")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
