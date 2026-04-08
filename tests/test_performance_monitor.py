"""性能监控模块单元测试"""

import pytest
import time
from src.performance_monitor import (
    PerformanceMonitor,
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


class TestPerformanceMonitor:
    """性能监控器测试类"""
    
    def setup_method(self):
        """每个测试方法前重置性能监控器"""
        reset_performance_monitor()
        self.monitor = get_performance_monitor()
    
    # ==================== 认证性能监控测试 ====================
    
    def test_record_auth_latency_success(self):
        """测试记录成功的认证延迟"""
        self.monitor.record_auth_latency(0.3, success=True)
        
        metrics = self.monitor.get_auth_metrics()
        assert metrics["total_count"] == 1
        assert metrics["success_count"] == 1
        assert metrics["failure_count"] == 0
        assert metrics["avg_latency_ms"] == 300.0
        assert metrics["min_latency_ms"] == 300.0
        assert metrics["max_latency_ms"] == 300.0
    
    def test_record_auth_latency_failure(self):
        """测试记录失败的认证延迟"""
        self.monitor.record_auth_latency(0.2, success=False)
        
        metrics = self.monitor.get_auth_metrics()
        assert metrics["total_count"] == 1
        assert metrics["success_count"] == 0
        assert metrics["failure_count"] == 1
    
    def test_auth_latency_requirement(self):
        """测试认证延迟要求（< 500ms）"""
        # 满足要求的情况
        self.monitor.record_auth_latency(0.4, success=True)
        metrics = self.monitor.get_auth_metrics()
        assert metrics["meets_latency_requirement"] is True
        
        # 不满足要求的情况
        reset_performance_monitor()
        self.monitor = get_performance_monitor()
        self.monitor.record_auth_latency(0.6, success=True)
        metrics = self.monitor.get_auth_metrics()
        assert metrics["meets_latency_requirement"] is False
    
    def test_auth_tps_calculation(self):
        """测试认证 TPS 计算"""
        import time
        
        # 模拟 10 次认证，添加小延迟确保有可测量的时间间隔
        for i in range(10):
            self.monitor.record_auth_latency(0.01, success=True)
            if i == 0:
                time.sleep(0.01)  # 确保有可测量的时间间隔
        
        metrics = self.monitor.get_auth_metrics()
        assert metrics["total_count"] == 10
        assert metrics["tps"] > 0
    
    def test_auth_min_max_latency(self):
        """测试认证最小和最大延迟"""
        self.monitor.record_auth_latency(0.1, success=True)
        self.monitor.record_auth_latency(0.5, success=True)
        self.monitor.record_auth_latency(0.3, success=True)
        
        metrics = self.monitor.get_auth_metrics()
        assert metrics["min_latency_ms"] == 100.0
        assert metrics["max_latency_ms"] == 500.0
    
    # ==================== 加密解密性能监控测试 ====================
    
    def test_record_encrypt_operation(self):
        """测试记录加密操作"""
        data_size = 1024  # 1KB
        elapsed_time = 0.005  # 5ms
        
        self.monitor.record_encrypt_operation(data_size, elapsed_time)
        
        metrics = self.monitor.get_encryption_metrics()
        assert metrics["encrypt_count"] == 1
        assert metrics["encrypt_total_bytes"] == 1024
    
    def test_record_decrypt_operation(self):
        """测试记录解密操作"""
        data_size = 2048  # 2KB
        elapsed_time = 0.006  # 6ms
        
        self.monitor.record_decrypt_operation(data_size, elapsed_time)
        
        metrics = self.monitor.get_encryption_metrics()
        assert metrics["decrypt_count"] == 1
        assert metrics["decrypt_total_bytes"] == 2048
    
    def test_encryption_throughput_calculation(self):
        """测试加密吞吐量计算"""
        # 模拟加密 100MB 数据，耗时 0.5 秒
        data_size = 100 * 1024 * 1024  # 100MB
        elapsed_time = 0.5
        
        self.monitor.record_encrypt_operation(data_size, elapsed_time)
        
        metrics = self.monitor.get_encryption_metrics()
        # 吞吐量应该约为 200 MB/s
        assert metrics["encrypt_throughput_mbps"] > 100
        assert metrics["meets_encrypt_throughput_requirement"] is True
    
    def test_decryption_throughput_calculation(self):
        """测试解密吞吐量计算"""
        # 模拟解密 100MB 数据，耗时 0.5 秒
        data_size = 100 * 1024 * 1024  # 100MB
        elapsed_time = 0.5
        
        self.monitor.record_decrypt_operation(data_size, elapsed_time)
        
        metrics = self.monitor.get_encryption_metrics()
        # 吞吐量应该约为 200 MB/s
        assert metrics["decrypt_throughput_mbps"] > 100
        assert metrics["meets_decrypt_throughput_requirement"] is True
    
    def test_1kb_encryption_latency(self):
        """测试 1KB 数据加密延迟要求（< 10ms）"""
        # 满足要求的情况
        data_size = 1024  # 1KB
        elapsed_time = 0.008  # 8ms
        
        self.monitor.record_encrypt_operation(data_size, elapsed_time)
        
        metrics = self.monitor.get_encryption_metrics()
        assert metrics["avg_encrypt_time_1kb_ms"] < 10
        assert metrics["meets_1kb_latency_requirement"] is True
    
    # ==================== 签名验签性能监控测试 ====================
    
    def test_record_sign_operation(self):
        """测试记录签名操作"""
        elapsed_time = 0.001  # 1ms
        
        self.monitor.record_sign_operation(elapsed_time)
        
        metrics = self.monitor.get_signature_metrics()
        assert metrics["sign_count"] == 1
    
    def test_record_verify_operation(self):
        """测试记录验签操作"""
        elapsed_time = 0.0005  # 0.5ms
        
        self.monitor.record_verify_operation(elapsed_time)
        
        metrics = self.monitor.get_signature_metrics()
        assert metrics["verify_count"] == 1
    
    def test_sign_ops_per_second(self):
        """测试签名操作每秒次数（≥ 1000 次/秒）"""
        # 模拟 1000 次签名操作，总耗时 0.5 秒
        for _ in range(1000):
            self.monitor.record_sign_operation(0.0005)
        
        metrics = self.monitor.get_signature_metrics()
        assert metrics["sign_count"] == 1000
        assert metrics["sign_ops_per_second"] >= 1000
        assert metrics["meets_sign_requirement"] is True
    
    def test_verify_ops_per_second(self):
        """测试验签操作每秒次数（≥ 2000 次/秒）"""
        # 模拟 2000 次验签操作，总耗时 0.5 秒
        for _ in range(2000):
            self.monitor.record_verify_operation(0.00025)
        
        metrics = self.monitor.get_signature_metrics()
        assert metrics["verify_count"] == 2000
        assert metrics["verify_ops_per_second"] >= 2000
        assert metrics["meets_verify_requirement"] is True
    
    # ==================== 会话管理性能监控测试 ====================
    
    def test_record_session_establish(self):
        """测试记录会话建立"""
        elapsed_time = 0.08  # 80ms
        
        self.monitor.record_session_establish(elapsed_time)
        
        metrics = self.monitor.get_session_metrics()
        assert metrics["establish_count"] == 1
        assert metrics["current_sessions"] == 1
        assert metrics["max_sessions"] == 1
    
    def test_record_session_close(self):
        """测试记录会话关闭"""
        self.monitor.record_session_establish(0.08)
        self.monitor.record_session_close()
        
        metrics = self.monitor.get_session_metrics()
        assert metrics["current_sessions"] == 0
        assert metrics["max_sessions"] == 1
    
    def test_record_session_query(self):
        """测试记录会话查询"""
        elapsed_time = 0.003  # 3ms
        
        self.monitor.record_session_query(elapsed_time)
        
        metrics = self.monitor.get_session_metrics()
        assert metrics["query_count"] == 1
    
    def test_session_establish_latency_requirement(self):
        """测试会话建立延迟要求（< 100ms）"""
        # 满足要求的情况
        self.monitor.record_session_establish(0.08)  # 80ms
        
        metrics = self.monitor.get_session_metrics()
        assert metrics["avg_establish_time_ms"] < 100
        assert metrics["meets_establish_latency_requirement"] is True
    
    def test_session_query_latency_requirement(self):
        """测试会话查询延迟要求（< 5ms）"""
        # 满足要求的情况
        self.monitor.record_session_query(0.003)  # 3ms
        
        metrics = self.monitor.get_session_metrics()
        assert metrics["avg_query_time_ms"] < 5
        assert metrics["meets_query_latency_requirement"] is True
    
    def test_concurrent_sessions_tracking(self):
        """测试并发会话数跟踪"""
        # 建立 5 个会话
        for _ in range(5):
            self.monitor.record_session_establish(0.08)
        
        metrics = self.monitor.get_session_metrics()
        assert metrics["current_sessions"] == 5
        assert metrics["max_sessions"] == 5
        
        # 关闭 2 个会话
        self.monitor.record_session_close()
        self.monitor.record_session_close()
        
        metrics = self.monitor.get_session_metrics()
        assert metrics["current_sessions"] == 3
        assert metrics["max_sessions"] == 5  # 最大值不变
    
    # ==================== 综合测试 ====================
    
    def test_get_all_metrics(self):
        """测试获取所有性能指标"""
        # 记录各种操作
        self.monitor.record_auth_latency(0.3, success=True)
        self.monitor.record_encrypt_operation(1024, 0.005)
        self.monitor.record_decrypt_operation(1024, 0.005)
        self.monitor.record_sign_operation(0.001)
        self.monitor.record_verify_operation(0.0005)
        self.monitor.record_session_establish(0.08)
        self.monitor.record_session_query(0.003)
        
        all_metrics = self.monitor.get_all_metrics()
        
        assert "authentication" in all_metrics
        assert "encryption" in all_metrics
        assert "signature" in all_metrics
        assert "session" in all_metrics
        assert "timestamp" in all_metrics
    
    def test_get_performance_summary(self):
        """测试获取性能摘要"""
        # 记录满足所有要求的操作
        self.monitor.record_auth_latency(0.3, success=True)
        
        # 加密 100MB，耗时 0.5 秒（200 MB/s）
        self.monitor.record_encrypt_operation(100 * 1024 * 1024, 0.5)
        self.monitor.record_decrypt_operation(100 * 1024 * 1024, 0.5)
        
        # 1000 次签名，总耗时 0.5 秒（2000 次/秒）
        for _ in range(1000):
            self.monitor.record_sign_operation(0.0005)
        
        # 2000 次验签，总耗时 0.5 秒（4000 次/秒）
        for _ in range(2000):
            self.monitor.record_verify_operation(0.00025)
        
        # 10000 个会话
        for _ in range(10000):
            self.monitor.record_session_establish(0.08)
        
        self.monitor.record_session_query(0.003)
        
        summary = self.monitor.get_performance_summary()
        
        assert "all_requirements_met" in summary
        assert "requirements_status" in summary
        assert "metrics" in summary
        
        # 检查各项要求状态
        status = summary["requirements_status"]
        assert "18.1_auth_latency" in status
        assert "18.2_auth_tps" in status
        assert "18.3_encrypt_throughput" in status
        assert "18.4_decrypt_throughput" in status
        assert "18.5_1kb_latency" in status
        assert "18.6_sign_ops" in status
        assert "18.7_verify_ops" in status
        assert "18.8_concurrent_sessions" in status
        assert "18.9_query_latency" in status
        assert "18.10_establish_latency" in status
    
    def test_reset_metrics(self):
        """测试重置性能指标"""
        # 记录一些操作
        self.monitor.record_auth_latency(0.3, success=True)
        self.monitor.record_encrypt_operation(1024, 0.005)
        
        # 重置
        self.monitor.reset_metrics()
        
        # 验证所有指标已重置
        auth_metrics = self.monitor.get_auth_metrics()
        assert auth_metrics["total_count"] == 0
        
        encryption_metrics = self.monitor.get_encryption_metrics()
        assert encryption_metrics["encrypt_count"] == 0
    
    def test_thread_safety(self):
        """测试线程安全性"""
        import threading
        
        def record_operations():
            for _ in range(100):
                self.monitor.record_auth_latency(0.3, success=True)
                self.monitor.record_encrypt_operation(1024, 0.005)
        
        # 创建多个线程并发记录
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=record_operations)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证计数正确
        auth_metrics = self.monitor.get_auth_metrics()
        assert auth_metrics["total_count"] == 1000  # 10 threads * 100 operations
        
        encryption_metrics = self.monitor.get_encryption_metrics()
        assert encryption_metrics["encrypt_count"] == 1000


class TestPerformanceDecorators:
    """性能监控装饰器测试类"""
    
    def setup_method(self):
        """每个测试方法前重置性能监控器"""
        reset_performance_monitor()
        self.monitor = get_performance_monitor()
    
    def test_monitor_auth_performance_decorator(self):
        """测试认证性能监控装饰器"""
        
        @monitor_auth_performance
        def mock_authenticate():
            time.sleep(0.01)
            return type('AuthResult', (), {'success': True})()
        
        mock_authenticate()
        
        metrics = self.monitor.get_auth_metrics()
        assert metrics["total_count"] == 1
        assert metrics["success_count"] == 1
    
    def test_monitor_encrypt_performance_decorator(self):
        """测试加密性能监控装饰器"""
        
        @monitor_encrypt_performance
        def mock_encrypt(plaintext, key):
            time.sleep(0.001)
            return b"encrypted"
        
        mock_encrypt(b"test data", b"key")
        
        metrics = self.monitor.get_encryption_metrics()
        assert metrics["encrypt_count"] == 1
    
    def test_monitor_decrypt_performance_decorator(self):
        """测试解密性能监控装饰器"""
        
        @monitor_decrypt_performance
        def mock_decrypt(ciphertext, key):
            time.sleep(0.001)
            return b"decrypted"
        
        mock_decrypt(b"encrypted", b"key")
        
        metrics = self.monitor.get_encryption_metrics()
        assert metrics["decrypt_count"] == 1
    
    def test_monitor_sign_performance_decorator(self):
        """测试签名性能监控装饰器"""
        
        @monitor_sign_performance
        def mock_sign(data, private_key):
            time.sleep(0.001)
            return b"signature"
        
        mock_sign(b"data", b"key")
        
        metrics = self.monitor.get_signature_metrics()
        assert metrics["sign_count"] == 1
    
    def test_monitor_verify_performance_decorator(self):
        """测试验签性能监控装饰器"""
        
        @monitor_verify_performance
        def mock_verify(data, signature, public_key):
            time.sleep(0.001)
            return True
        
        mock_verify(b"data", b"signature", b"key")
        
        metrics = self.monitor.get_signature_metrics()
        assert metrics["verify_count"] == 1
    
    def test_monitor_session_establish_context_manager(self):
        """测试会话建立性能监控上下文管理器"""
        
        with monitor_session_establish():
            time.sleep(0.01)
        
        metrics = self.monitor.get_session_metrics()
        assert metrics["establish_count"] == 1
    
    def test_monitor_session_query_context_manager(self):
        """测试会话查询性能监控上下文管理器"""
        
        with monitor_session_query():
            time.sleep(0.001)
        
        metrics = self.monitor.get_session_metrics()
        assert metrics["query_count"] == 1


class TestGlobalMonitor:
    """全局性能监控器测试类"""
    
    def test_get_performance_monitor_singleton(self):
        """测试全局性能监控器单例模式"""
        reset_performance_monitor()
        
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2
    
    def test_reset_performance_monitor(self):
        """测试重置全局性能监控器"""
        monitor1 = get_performance_monitor()
        monitor1.record_auth_latency(0.3, success=True)
        
        reset_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is not monitor2
        
        metrics = monitor2.get_auth_metrics()
        assert metrics["total_count"] == 0
