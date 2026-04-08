"""Redis 客户端连接"""

import redis
from typing import Optional, Any
from config import RedisConfig


class RedisConnection:
    """Redis 连接管理器"""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.client: Optional[redis.Redis] = None
    
    def connect(self):
        """建立 Redis 连接"""
        if self.client is None:
            self.client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=False  # 保持字节类型用于加密数据
            )
    
    def close(self):
        """关闭 Redis 连接"""
        if self.client:
            self.client.close()
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置键值对，可选过期时间（秒）"""
        self.connect()
        return self.client.set(key, value, ex=ex)
    
    def get(self, key: str) -> Optional[bytes]:
        """获取键对应的值"""
        self.connect()
        return self.client.get(key)
    
    def delete(self, key: str) -> int:
        """删除键"""
        self.connect()
        return self.client.delete(key)
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        self.connect()
        return self.client.exists(key) > 0
    
    def scan_keys(self, pattern: str) -> list:
        """扫描匹配模式的所有键
        
        参数:
            pattern: 键模式（如 "session:*"）
            
        返回:
            list: 匹配的键列表
        """
        self.connect()
        keys = []
        cursor = 0
        
        while True:
            cursor, partial_keys = self.client.scan(cursor, match=pattern, count=100)
            keys.extend(partial_keys)
            
            if cursor == 0:
                break
        
        return keys
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
