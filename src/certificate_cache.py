"""证书验证缓存模块

提供 LRU 缓存功能，用于缓存证书验证结果以提高性能。
"""

import time
from typing import Optional, Tuple
from collections import OrderedDict
from threading import Lock
from src.models.enums import ValidationResult


class CertificateCache:
    """证书验证结果的 LRU 缓存
    
    使用 LRU（最近最少使用）策略缓存证书验证结果，提高认证性能。
    
    属性:
        max_size: 缓存最大容量（默认 10,000）
        ttl_seconds: 缓存条目的生存时间（默认 300 秒 = 5 分钟）
    """
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        """初始化证书缓存
        
        参数:
            max_size: 缓存最大容量
            ttl_seconds: 缓存条目的生存时间（秒）
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()  # 使用 OrderedDict 实现 LRU
        self._lock = Lock()  # 线程安全锁
    
    def get(self, serial_number: str) -> Optional[Tuple[ValidationResult, str]]:
        """从缓存中获取证书验证结果
        
        参数:
            serial_number: 证书序列号
            
        返回:
            Optional[Tuple[ValidationResult, str]]: 如果缓存命中且未过期，
                返回 (验证结果, 消息)；否则返回 None
        """
        with self._lock:
            if serial_number not in self._cache:
                return None
            
            # 获取缓存条目
            entry = self._cache[serial_number]
            timestamp = entry['timestamp']
            result = entry['result']
            message = entry['message']
            
            # 检查是否过期
            current_time = time.time()
            if current_time - timestamp > self.ttl_seconds:
                # 过期，删除缓存条目
                del self._cache[serial_number]
                return None
            
            # 缓存命中，移动到末尾（LRU 策略）
            self._cache.move_to_end(serial_number)
            
            return (result, message)
    
    def put(self, serial_number: str, result: ValidationResult, message: str) -> None:
        """将证书验证结果放入缓存
        
        参数:
            serial_number: 证书序列号
            result: 验证结果
            message: 验证消息
        """
        with self._lock:
            current_time = time.time()
            
            # 如果已存在，先删除（稍后会重新添加到末尾）
            if serial_number in self._cache:
                del self._cache[serial_number]
            
            # 如果缓存已满，删除最旧的条目（第一个条目）
            if len(self._cache) >= self.max_size:
                # popitem(last=False) 删除第一个（最旧的）条目
                self._cache.popitem(last=False)
            
            # 添加新条目到末尾
            self._cache[serial_number] = {
                'timestamp': current_time,
                'result': result,
                'message': message
            }
    
    def invalidate(self, serial_number: str) -> None:
        """使指定证书的缓存失效
        
        当证书被撤销时，应调用此方法使缓存失效。
        
        参数:
            serial_number: 证书序列号
        """
        with self._lock:
            if serial_number in self._cache:
                del self._cache[serial_number]
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """获取当前缓存大小
        
        返回:
            int: 当前缓存中的条目数量
        """
        with self._lock:
            return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """清理所有过期的缓存条目
        
        返回:
            int: 清理的条目数量
        """
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            # 找出所有过期的键
            for serial_number, entry in self._cache.items():
                if current_time - entry['timestamp'] > self.ttl_seconds:
                    expired_keys.append(serial_number)
            
            # 删除过期的条目
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)


# 全局缓存实例
_global_cache: Optional[CertificateCache] = None


def get_certificate_cache() -> CertificateCache:
    """获取全局证书缓存实例
    
    返回:
        CertificateCache: 全局缓存实例
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = CertificateCache(max_size=10000, ttl_seconds=300)
    return _global_cache
