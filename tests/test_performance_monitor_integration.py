"""性能监控模块集成测试

测试性能监控与现有模块的集成。
"""

import pytest
import time
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
from src.authentication import mutual_authentication, establish_session
from src.models.certificate import Certificate, SubjectInfo
from src.models.session import AuthResult, AuthToken
from datetime import datetime, timedelta


class TestPerformanceMonitorIntegration:
    """性能监控集成测试类"""
    
    def setup_method(self):
        """每个测试方法前重置性能监控器"""
        reset_performance_monitor()
        self.monitor = get_performance_monitor()
    
    def test_sm4_encryption_performance_tracking(self):
        """测试 SM4 加密性能跟踪"""
        # 生成密钥
        key = generate_sm4_key(16)
        plaintext = b"Test data for encryption performance tracking" * 100
        
        # 使用装饰器包装的加密函数
        @monitor_encrypt_performance
        def encrypt_with_monitoring(data, k):
            return sm4_encrypt(data, k)
        
        # 执行加密
        ciphertext = encrypt_with_monitoring(plaintext, key)
        
        # 验证性能指标已记录
        metrics = self.monitor.get_encryption_metrics()
        assert metrics["encrypt_count"] == 1
        assert metrics["encrypt_total_bytes"] == len(plaintext)
        assert metrics["encrypt_throughput_mbps"] > 0
    
    def test_sm4_decryption_performance_tracking(self):
        """测试 SM4 解密性能跟踪"""
        # 生成密钥和加密数据
        key = generate_sm4_key(16)
        plaintext = b"Test data for decryption performance tracking" * 100
        ciphertext = sm4_encrypt(plaintext, key)
        
        # 使用装饰器包装的解密函数
        @monitor_decrypt_performance
        def decrypt_with_monitoring(data, k):
            return sm4_decrypt(data, k)
        
        # 执行解密
        decrypted = decrypt_with_monitoring(ciphertext, key)
        
        # 验证性能指标已记录
        metrics = self.monitor.get_encryption_metrics()
        assert metrics["decrypt_count"] == 1
        assert metrics["decrypt_total_bytes"] == len(ciphertext)
        assert metrics["decrypt_throughput_mbps"] > 0
        
        # 验证解密正确
        assert decrypted == plaintext
    
    def test_sm2_signature_performance_tracking(self):
        """测试 SM2 签名性能跟踪"""
        # 生成密钥对
        private_key, public_key = generate_sm2_keypair()
        data = b"Test data for signature performance tracking"
        
        # 使用装饰器包装的签名函数
        @monitor_sign_performance
        def sign_with_monitoring(d, pk):
            return sm2_sign(d, pk)
        
        # 执行签名
        signature = sign_with_monitoring(data, private_key)
        
        # 验证性能指标已记录
        metrics = self.monitor.get_signature_metrics()
        assert metrics["sign_count"] == 1
        assert metrics["sign_ops_per_second"] > 0
    
    def test_sm2_verification_performance_tracking(self):
        """测试 SM2 验签性能跟踪"""
        # 生成密钥对和签名
        private_key, public_key = generate_sm2_keypair()
        data = b"Test data for verification performance tracking"
        signature = sm2_sign(data, private_key)
        
        # 使用装饰器包装的验签函数
        @monitor_verify_performance
        def verify_with_monitoring(d, s, pk):
            return sm2_verify(d, s, pk)
        
        # 执行验签
        result = verify_with_monitoring(data, signature, public_key)
        
        # 验证性能指标已记录
        metrics = self.monitor.get_signature_metrics()
        assert metrics["verify_count"] == 1
        assert metrics["verify_ops_per_second"] > 0
        
        # 验证签名正确
        assert result is True
    
    def test_authentication_performance_tracking(self):
        """测试认证性能跟踪"""
        # 创建模拟的认证函数
        @monitor_auth_performance
        def mock_authenticate():
            time.sleep(0.1)  # 模拟认证延迟
            return AuthResult.create_success(
                AuthToken(
                    vehicle_id="TEST_VEHICLE",
                    issued_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(hours=24),
                    permissions={"data_transfer"},
                    signature=b"mock_signature"
                ),
                generate_sm4_key(16)
            )
        
        # 执行认证
        result = mock_authenticate()
        
        # 验证性能指标已记录
        metrics = self.monitor.get_auth_metrics()
        assert metrics["total_count"] == 1
        assert metrics["success_count"] == 1
        assert metrics["avg_latency_ms"] > 0
    
    def test_session_establish_performance_tracking(self):
        """测试会话建立性能跟踪"""
        # 使用上下文管理器跟踪会话建立
        with monitor_session_establish():
            time.sleep(0.05)  # 模拟会话建立延迟
        
        # 验证性能指标已记录
        metrics = self.monitor.get_session_metrics()
        assert metrics["establish_count"] == 1
        assert metrics["current_sessions"] == 1
        assert metrics["avg_establish_time_ms"] > 0
    
    def test_session_query_performance_tracking(self):
        """测试会话查询性能跟踪"""
        # 使用上下文管理器跟踪会话查询
        with monitor_session_query():
            time.sleep(0.002)  # 模拟会话查询延迟
        
        # 验证性能指标已记录
        metrics = self.monitor.get_session_metrics()
        assert metrics["query_count"] == 1
        assert metrics["avg_query_time_ms"] > 0
    
    def test_comprehensive_performance_tracking(self):
        """测试综合性能跟踪"""
        # 模拟完整的认证和数据传输流程
        
        # 1. 生成密钥
        sm4_key = generate_sm4_key(16)
        private_key, public_key = generate_sm2_keypair()
        
        # 2. 认证
        @monitor_auth_performance
        def mock_authenticate():
            time.sleep(0.1)
            return AuthResult.create_success(
                AuthToken(
                    vehicle_id="TEST_VEHICLE",
                    issued_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(hours=24),
                    permissions={"data_transfer"},
                    signature=b"mock_signature"
                ),
                sm4_key
            )
        
        auth_result = mock_authenticate()
        
        # 3. 建立会话
        with monitor_session_establish():
            time.sleep(0.05)
        
        # 4. 加密数据
        @monitor_encrypt_performance
        def encrypt_data(data, key):
            return sm4_encrypt(data, key)
        
        plaintext = b"Business data" * 1000
        ciphertext = encrypt_data(plaintext, sm4_key)
        
        # 5. 签名
        @monitor_sign_performance
        def sign_data(data, pk):
            return sm2_sign(data, pk)
        
        signature = sign_data(ciphertext, private_key)
        
        # 6. 验签
        @monitor_verify_performance
        def verify_signature(data, sig, pk):
            return sm2_verify(data, sig, pk)
        
        verify_result = verify_signature(ciphertext, signature, public_key)
        
        # 7. 解密
        @monitor_decrypt_performance
        def decrypt_data(data, key):
            return sm4_decrypt(data, key)
        
        decrypted = decrypt_data(ciphertext, sm4_key)
        
        # 8. 查询会话
        with monitor_session_query():
            time.sleep(0.002)
        
        # 验证所有性能指标
        all_metrics = self.monitor.get_all_metrics()
        
        assert all_metrics["authentication"]["total_count"] == 1
        assert all_metrics["encryption"]["encrypt_count"] == 1
        assert all_metrics["encryption"]["decrypt_count"] == 1
        assert all_metrics["signature"]["sign_count"] == 1
        assert all_metrics["signature"]["verify_count"] == 1
        assert all_metrics["session"]["establish_count"] == 1
        assert all_metrics["session"]["query_count"] == 1
        
        # 验证数据正确性
        assert verify_result is True
        assert decrypted == plaintext
    
    def test_performance_summary_with_real_operations(self):
        """测试使用真实操作的性能摘要"""
        # 执行多次真实的加密解密操作
        key = generate_sm4_key(16)
        
        @monitor_encrypt_performance
        def encrypt_data(data, k):
            return sm4_encrypt(data, k)
        
        @monitor_decrypt_performance
        def decrypt_data(data, k):
            return sm4_decrypt(data, k)
        
        # 使用较小的数据量以避免测试超时
        # 加密和解密 10 次，每次 10KB（总共 100KB）
        data_size = 10 * 1024  # 10KB
        for _ in range(10):
            plaintext = b"x" * data_size
            ciphertext = encrypt_data(plaintext, key)
            decrypted = decrypt_data(ciphertext, key)
            assert decrypted == plaintext
        
        # 获取性能摘要
        summary = self.monitor.get_performance_summary()
        
        assert "all_requirements_met" in summary
        assert "requirements_status" in summary
        assert "metrics" in summary
        
        # 验证加密解密指标
        encryption_metrics = summary["metrics"]["encryption"]
        assert encryption_metrics["encrypt_count"] == 10
        assert encryption_metrics["decrypt_count"] == 10
        assert encryption_metrics["encrypt_throughput_mbps"] > 0
        assert encryption_metrics["decrypt_throughput_mbps"] > 0
    
    def test_concurrent_operations_performance(self):
        """测试并发操作性能"""
        import threading
        
        key = generate_sm4_key(16)
        private_key, public_key = generate_sm2_keypair()
        
        @monitor_encrypt_performance
        def encrypt_data(data, k):
            return sm4_encrypt(data, k)
        
        @monitor_sign_performance
        def sign_data(data, pk):
            return sm2_sign(data, pk)
        
        def worker():
            for _ in range(10):
                # 加密
                plaintext = b"test data" * 100
                ciphertext = encrypt_data(plaintext, key)
                
                # 签名
                signature = sign_data(plaintext, private_key)
        
        # 创建多个线程并发执行
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证性能指标
        encryption_metrics = self.monitor.get_encryption_metrics()
        signature_metrics = self.monitor.get_signature_metrics()
        
        assert encryption_metrics["encrypt_count"] == 50  # 5 threads * 10 operations
        assert signature_metrics["sign_count"] == 50
    
    def test_performance_requirements_validation(self):
        """测试性能要求验证"""
        # 模拟满足所有性能要求的操作
        
        # 1. 认证延迟 < 500ms
        @monitor_auth_performance
        def fast_auth():
            time.sleep(0.3)  # 300ms
            return AuthResult.create_success(
                AuthToken(
                    vehicle_id="TEST",
                    issued_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(hours=24),
                    permissions=set(),
                    signature=b"sig"
                ),
                generate_sm4_key(16)
            )
        
        fast_auth()
        
        # 2. 加密吞吐量 ≥ 100 MB/s（模拟）
        # 实际测试中，真实的 SM4 加密速度取决于硬件
        # 这里我们记录足够的数据量和时间来满足要求
        self.monitor.record_encrypt_operation(100 * 1024 * 1024, 0.5)  # 100MB in 0.5s = 200 MB/s
        self.monitor.record_decrypt_operation(100 * 1024 * 1024, 0.5)
        
        # 3. 签名验签性能
        for _ in range(1000):
            self.monitor.record_sign_operation(0.0005)  # 2000 ops/s
        
        for _ in range(2000):
            self.monitor.record_verify_operation(0.00025)  # 4000 ops/s
        
        # 4. 会话管理
        for _ in range(10000):
            self.monitor.record_session_establish(0.08)  # 80ms
        
        self.monitor.record_session_query(0.003)  # 3ms
        
        # 获取性能摘要
        summary = self.monitor.get_performance_summary()
        
        # 验证所有要求状态
        status = summary["requirements_status"]
        
        assert status["18.1_auth_latency"] is True
        assert status["18.3_encrypt_throughput"] is True
        assert status["18.4_decrypt_throughput"] is True
        assert status["18.5_1kb_latency"] is True
        assert status["18.6_sign_ops"] is True
        assert status["18.7_verify_ops"] is True
        assert status["18.8_concurrent_sessions"] is True
        assert status["18.9_query_latency"] is True
        assert status["18.10_establish_latency"] is True
