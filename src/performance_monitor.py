"""性能监控模块

提供认证、加密解密、签名验签和会话管理的性能监控功能。
"""

import time
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    
    # 认证性能指标
    auth_total_count: int = 0
    auth_success_count: int = 0
    auth_failure_count: int = 0
    auth_total_latency: float = 0.0  # 总延迟（秒）
    auth_min_latency: float = float('inf')
    auth_max_latency: float = 0.0
    auth_recent_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    # 加密解密性能指标
    encrypt_total_count: int = 0
    encrypt_total_bytes: int = 0
    encrypt_total_time: float = 0.0
    decrypt_total_count: int = 0
    decrypt_total_bytes: int = 0
    decrypt_total_time: float = 0.0
    
    # 签名验签性能指标
    sign_total_count: int = 0
    sign_total_time: float = 0.0
    verify_total_count: int = 0
    verify_total_time: float = 0.0
    
    # 会话管理性能指标
    session_establish_count: int = 0
    session_establish_total_time: float = 0.0
    session_query_count: int = 0
    session_query_total_time: float = 0.0
    session_current_count: int = 0
    session_max_count: int = 0
    
    # 时间窗口统计（用于计算 TPS）
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_reset_time: datetime = field(default_factory=datetime.utcnow)


class PerformanceMonitor:
    """性能监控器
    
    提供线程安全的性能指标收集和查询功能。
    
    验证需求: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10
    """
    
    def __init__(self):
        """初始化性能监控器"""
        self.metrics = PerformanceMetrics()
        self.lock = threading.Lock()
    
    # ==================== 认证性能监控 ====================
    
    def record_auth_latency(self, latency: float, success: bool = True):
        """记录认证延迟
        
        参数:
            latency: 认证延迟（秒）
            success: 认证是否成功
            
        验证需求: 18.1, 18.2
        """
        with self.lock:
            self.metrics.auth_total_count += 1
            if success:
                self.metrics.auth_success_count += 1
            else:
                self.metrics.auth_failure_count += 1
            
            self.metrics.auth_total_latency += latency
            self.metrics.auth_min_latency = min(self.metrics.auth_min_latency, latency)
            self.metrics.auth_max_latency = max(self.metrics.auth_max_latency, latency)
            self.metrics.auth_recent_latencies.append(latency)
    
    def get_auth_metrics(self) -> Dict:
        """获取认证性能指标
        
        返回:
            Dict: 包含以下指标的字典
                - total_count: 总认证次数
                - success_count: 成功认证次数
                - failure_count: 失败认证次数
                - avg_latency_ms: 平均延迟（毫秒）
                - min_latency_ms: 最小延迟（毫秒）
                - max_latency_ms: 最大延迟（毫秒）
                - tps: 每秒事务数
                - meets_latency_requirement: 是否满足延迟要求（< 500ms）
                - meets_tps_requirement: 是否满足 TPS 要求（≥ 100）
                
        验证需求: 18.1, 18.2
        """
        with self.lock:
            if self.metrics.auth_total_count == 0:
                return {
                    "total_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "avg_latency_ms": 0.0,
                    "min_latency_ms": 0.0,
                    "max_latency_ms": 0.0,
                    "tps": 0.0,
                    "meets_latency_requirement": True,
                    "meets_tps_requirement": False
                }
            
            avg_latency = self.metrics.auth_total_latency / self.metrics.auth_total_count
            elapsed_time = (datetime.utcnow() - self.metrics.start_time).total_seconds()
            tps = self.metrics.auth_total_count / elapsed_time if elapsed_time > 0 else 0.0
            
            return {
                "total_count": self.metrics.auth_total_count,
                "success_count": self.metrics.auth_success_count,
                "failure_count": self.metrics.auth_failure_count,
                "avg_latency_ms": avg_latency * 1000,
                "min_latency_ms": self.metrics.auth_min_latency * 1000,
                "max_latency_ms": self.metrics.auth_max_latency * 1000,
                "tps": tps,
                "meets_latency_requirement": avg_latency < 0.5,  # < 500ms
                "meets_tps_requirement": tps >= 100  # ≥ 100 TPS
            }
    
    # ==================== 加密解密性能监控 ====================
    
    def record_encrypt_operation(self, data_size: int, elapsed_time: float):
        """记录加密操作
        
        参数:
            data_size: 数据大小（字节）
            elapsed_time: 加密耗时（秒）
            
        验证需求: 18.3, 18.5
        """
        with self.lock:
            self.metrics.encrypt_total_count += 1
            self.metrics.encrypt_total_bytes += data_size
            self.metrics.encrypt_total_time += elapsed_time
    
    def record_decrypt_operation(self, data_size: int, elapsed_time: float):
        """记录解密操作
        
        参数:
            data_size: 数据大小（字节）
            elapsed_time: 解密耗时（秒）
            
        验证需求: 18.4, 18.5
        """
        with self.lock:
            self.metrics.decrypt_total_count += 1
            self.metrics.decrypt_total_bytes += data_size
            self.metrics.decrypt_total_time += elapsed_time
    
    def get_encryption_metrics(self) -> Dict:
        """获取加密解密性能指标
        
        返回:
            Dict: 包含以下指标的字典
                - encrypt_count: 加密操作次数
                - encrypt_throughput_mbps: 加密吞吐量（MB/s）
                - decrypt_count: 解密操作次数
                - decrypt_throughput_mbps: 解密吞吐量（MB/s）
                - avg_encrypt_time_1kb_ms: 1KB 数据平均加密时间（毫秒）
                - meets_encrypt_throughput_requirement: 是否满足加密吞吐量要求（≥ 100 MB/s）
                - meets_decrypt_throughput_requirement: 是否满足解密吞吐量要求（≥ 100 MB/s）
                - meets_1kb_latency_requirement: 是否满足 1KB 延迟要求（< 10ms）
                
        验证需求: 18.3, 18.4, 18.5
        """
        with self.lock:
            encrypt_throughput = 0.0
            decrypt_throughput = 0.0
            avg_encrypt_time_1kb = 0.0
            
            if self.metrics.encrypt_total_time > 0:
                # 吞吐量 = 总字节数 / 总时间 / (1024 * 1024) MB/s
                encrypt_throughput = self.metrics.encrypt_total_bytes / self.metrics.encrypt_total_time / (1024 * 1024)
                # 估算 1KB 数据的平均加密时间
                avg_encrypt_time_1kb = (self.metrics.encrypt_total_time / self.metrics.encrypt_total_bytes) * 1024 * 1000
            
            if self.metrics.decrypt_total_time > 0:
                decrypt_throughput = self.metrics.decrypt_total_bytes / self.metrics.decrypt_total_time / (1024 * 1024)
            
            return {
                "encrypt_count": self.metrics.encrypt_total_count,
                "encrypt_total_bytes": self.metrics.encrypt_total_bytes,
                "encrypt_throughput_mbps": encrypt_throughput,
                "decrypt_count": self.metrics.decrypt_total_count,
                "decrypt_total_bytes": self.metrics.decrypt_total_bytes,
                "decrypt_throughput_mbps": decrypt_throughput,
                "avg_encrypt_time_1kb_ms": avg_encrypt_time_1kb,
                "meets_encrypt_throughput_requirement": encrypt_throughput >= 100,  # ≥ 100 MB/s
                "meets_decrypt_throughput_requirement": decrypt_throughput >= 100,  # ≥ 100 MB/s
                "meets_1kb_latency_requirement": avg_encrypt_time_1kb < 10  # < 10ms
            }
    
    # ==================== 签名验签性能监控 ====================
    
    def record_sign_operation(self, elapsed_time: float):
        """记录签名操作
        
        参数:
            elapsed_time: 签名耗时（秒）
            
        验证需求: 18.6
        """
        with self.lock:
            self.metrics.sign_total_count += 1
            self.metrics.sign_total_time += elapsed_time
    
    def record_verify_operation(self, elapsed_time: float):
        """记录验签操作
        
        参数:
            elapsed_time: 验签耗时（秒）
            
        验证需求: 18.7
        """
        with self.lock:
            self.metrics.verify_total_count += 1
            self.metrics.verify_total_time += elapsed_time
    
    def get_signature_metrics(self) -> Dict:
        """获取签名验签性能指标
        
        返回:
            Dict: 包含以下指标的字典
                - sign_count: 签名操作次数
                - sign_ops_per_second: 每秒签名次数
                - verify_count: 验签操作次数
                - verify_ops_per_second: 每秒验签次数
                - meets_sign_requirement: 是否满足签名性能要求（≥ 1000 次/秒）
                - meets_verify_requirement: 是否满足验签性能要求（≥ 2000 次/秒）
                
        验证需求: 18.6, 18.7
        """
        with self.lock:
            sign_ops_per_second = 0.0
            verify_ops_per_second = 0.0
            
            if self.metrics.sign_total_time > 0:
                sign_ops_per_second = self.metrics.sign_total_count / self.metrics.sign_total_time
            
            if self.metrics.verify_total_time > 0:
                verify_ops_per_second = self.metrics.verify_total_count / self.metrics.verify_total_time
            
            return {
                "sign_count": self.metrics.sign_total_count,
                "sign_ops_per_second": sign_ops_per_second,
                "verify_count": self.metrics.verify_total_count,
                "verify_ops_per_second": verify_ops_per_second,
                "meets_sign_requirement": sign_ops_per_second >= 1000,  # ≥ 1000 次/秒
                "meets_verify_requirement": verify_ops_per_second >= 2000  # ≥ 2000 次/秒
            }
    
    # ==================== 会话管理性能监控 ====================
    
    def record_session_establish(self, elapsed_time: float):
        """记录会话建立操作
        
        参数:
            elapsed_time: 会话建立耗时（秒）
            
        验证需求: 18.10
        """
        with self.lock:
            self.metrics.session_establish_count += 1
            self.metrics.session_establish_total_time += elapsed_time
            self.metrics.session_current_count += 1
            self.metrics.session_max_count = max(
                self.metrics.session_max_count,
                self.metrics.session_current_count
            )
    
    def record_session_close(self):
        """记录会话关闭操作
        
        验证需求: 18.8
        """
        with self.lock:
            self.metrics.session_current_count = max(0, self.metrics.session_current_count - 1)
    
    def record_session_query(self, elapsed_time: float):
        """记录会话查询操作
        
        参数:
            elapsed_time: 会话查询耗时（秒）
            
        验证需求: 18.9
        """
        with self.lock:
            self.metrics.session_query_count += 1
            self.metrics.session_query_total_time += elapsed_time
    
    def get_session_metrics(self) -> Dict:
        """获取会话管理性能指标
        
        返回:
            Dict: 包含以下指标的字典
                - current_sessions: 当前活跃会话数
                - max_sessions: 最大并发会话数
                - establish_count: 会话建立次数
                - avg_establish_time_ms: 平均会话建立时间（毫秒）
                - query_count: 会话查询次数
                - avg_query_time_ms: 平均会话查询时间（毫秒）
                - meets_concurrent_requirement: 是否满足并发会话要求（≥ 10,000）
                - meets_query_latency_requirement: 是否满足查询延迟要求（< 5ms）
                - meets_establish_latency_requirement: 是否满足建立延迟要求（< 100ms）
                
        验证需求: 18.8, 18.9, 18.10
        """
        with self.lock:
            avg_establish_time = 0.0
            avg_query_time = 0.0
            
            if self.metrics.session_establish_count > 0:
                avg_establish_time = (self.metrics.session_establish_total_time / 
                                     self.metrics.session_establish_count) * 1000
            
            if self.metrics.session_query_count > 0:
                avg_query_time = (self.metrics.session_query_total_time / 
                                 self.metrics.session_query_count) * 1000
            
            return {
                "current_sessions": self.metrics.session_current_count,
                "max_sessions": self.metrics.session_max_count,
                "establish_count": self.metrics.session_establish_count,
                "avg_establish_time_ms": avg_establish_time,
                "query_count": self.metrics.session_query_count,
                "avg_query_time_ms": avg_query_time,
                "meets_concurrent_requirement": self.metrics.session_max_count >= 10000,  # ≥ 10,000
                "meets_query_latency_requirement": avg_query_time < 5,  # < 5ms
                "meets_establish_latency_requirement": avg_establish_time < 100  # < 100ms
            }
    
    # ==================== 综合性能报告 ====================
    
    def get_all_metrics(self) -> Dict:
        """获取所有性能指标
        
        返回:
            Dict: 包含所有性能指标的字典
            
        验证需求: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10
        """
        return {
            "authentication": self.get_auth_metrics(),
            "encryption": self.get_encryption_metrics(),
            "signature": self.get_signature_metrics(),
            "session": self.get_session_metrics(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def reset_metrics(self):
        """重置所有性能指标
        
        用于开始新的性能测试周期。
        """
        with self.lock:
            self.metrics = PerformanceMetrics()
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要
        
        返回:
            Dict: 包含性能摘要和是否满足所有要求的字典
            
        验证需求: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10
        """
        auth_metrics = self.get_auth_metrics()
        encryption_metrics = self.get_encryption_metrics()
        signature_metrics = self.get_signature_metrics()
        session_metrics = self.get_session_metrics()
        
        all_requirements_met = (
            auth_metrics["meets_latency_requirement"] and
            auth_metrics["meets_tps_requirement"] and
            encryption_metrics["meets_encrypt_throughput_requirement"] and
            encryption_metrics["meets_decrypt_throughput_requirement"] and
            encryption_metrics["meets_1kb_latency_requirement"] and
            signature_metrics["meets_sign_requirement"] and
            signature_metrics["meets_verify_requirement"] and
            session_metrics["meets_concurrent_requirement"] and
            session_metrics["meets_query_latency_requirement"] and
            session_metrics["meets_establish_latency_requirement"]
        )
        
        return {
            "all_requirements_met": all_requirements_met,
            "requirements_status": {
                "18.1_auth_latency": auth_metrics["meets_latency_requirement"],
                "18.2_auth_tps": auth_metrics["meets_tps_requirement"],
                "18.3_encrypt_throughput": encryption_metrics["meets_encrypt_throughput_requirement"],
                "18.4_decrypt_throughput": encryption_metrics["meets_decrypt_throughput_requirement"],
                "18.5_1kb_latency": encryption_metrics["meets_1kb_latency_requirement"],
                "18.6_sign_ops": signature_metrics["meets_sign_requirement"],
                "18.7_verify_ops": signature_metrics["meets_verify_requirement"],
                "18.8_concurrent_sessions": session_metrics["meets_concurrent_requirement"],
                "18.9_query_latency": session_metrics["meets_query_latency_requirement"],
                "18.10_establish_latency": session_metrics["meets_establish_latency_requirement"]
            },
            "metrics": {
                "authentication": auth_metrics,
                "encryption": encryption_metrics,
                "signature": signature_metrics,
                "session": session_metrics
            }
        }


# 全局性能监控器实例
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例
    
    返回:
        PerformanceMonitor: 全局性能监控器实例
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def reset_performance_monitor():
    """重置全局性能监控器"""
    global _global_monitor
    _global_monitor = None



# ==================== 装饰器和上下文管理器 ====================

from functools import wraps
from contextlib import contextmanager


def monitor_auth_performance(func):
    """装饰器：监控认证性能
    
    用法:
        @monitor_auth_performance
        def authenticate_vehicle(...):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        monitor = get_performance_monitor()
        start_time = time.time()
        success = False
        
        try:
            result = func(*args, **kwargs)
            # 假设返回的 AuthResult 有 success 属性
            if hasattr(result, 'success'):
                success = result.success
            else:
                success = True
            return result
        except Exception as e:
            success = False
            raise
        finally:
            elapsed_time = time.time() - start_time
            monitor.record_auth_latency(elapsed_time, success)
    
    return wrapper


def monitor_encrypt_performance(func):
    """装饰器：监控加密性能
    
    用法:
        @monitor_encrypt_performance
        def sm4_encrypt(plaintext, key):
            ...
    """
    @wraps(func)
    def wrapper(plaintext, *args, **kwargs):
        monitor = get_performance_monitor()
        data_size = len(plaintext) if isinstance(plaintext, (bytes, str)) else 0
        start_time = time.time()
        
        try:
            result = func(plaintext, *args, **kwargs)
            return result
        finally:
            elapsed_time = time.time() - start_time
            monitor.record_encrypt_operation(data_size, elapsed_time)
    
    return wrapper


def monitor_decrypt_performance(func):
    """装饰器：监控解密性能
    
    用法:
        @monitor_decrypt_performance
        def sm4_decrypt(ciphertext, key):
            ...
    """
    @wraps(func)
    def wrapper(ciphertext, *args, **kwargs):
        monitor = get_performance_monitor()
        data_size = len(ciphertext) if isinstance(ciphertext, bytes) else 0
        start_time = time.time()
        
        try:
            result = func(ciphertext, *args, **kwargs)
            return result
        finally:
            elapsed_time = time.time() - start_time
            monitor.record_decrypt_operation(data_size, elapsed_time)
    
    return wrapper


def monitor_sign_performance(func):
    """装饰器：监控签名性能
    
    用法:
        @monitor_sign_performance
        def sm2_sign(data, private_key):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        monitor = get_performance_monitor()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_time = time.time() - start_time
            monitor.record_sign_operation(elapsed_time)
    
    return wrapper


def monitor_verify_performance(func):
    """装饰器：监控验签性能
    
    用法:
        @monitor_verify_performance
        def sm2_verify(data, signature, public_key):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        monitor = get_performance_monitor()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_time = time.time() - start_time
            monitor.record_verify_operation(elapsed_time)
    
    return wrapper


@contextmanager
def monitor_session_establish():
    """上下文管理器：监控会话建立性能
    
    用法:
        with monitor_session_establish():
            session = establish_session(...)
    """
    monitor = get_performance_monitor()
    start_time = time.time()
    
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        monitor.record_session_establish(elapsed_time)


@contextmanager
def monitor_session_query():
    """上下文管理器：监控会话查询性能
    
    用法:
        with monitor_session_query():
            session = get_session(session_id)
    """
    monitor = get_performance_monitor()
    start_time = time.time()
    
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        monitor.record_session_query(elapsed_time)
