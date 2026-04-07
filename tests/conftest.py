"""pytest 配置文件"""

import pytest
from unittest.mock import MagicMock, patch
from config import PostgreSQLConfig, RedisConfig
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


# 创建一个全局的内存字典来模拟 Redis
_redis_store = {}


class MockRedisConnection:
    """Mock Redis 连接用于测试"""
    def __init__(self, config):
        self.config = config
        self.client = None
    
    def connect(self):
        pass
    
    def close(self):
        pass
    
    def set(self, key: str, value, ex=None):
        _redis_store[key] = value
        return True
    
    def get(self, key: str):
        return _redis_store.get(key)
    
    def delete(self, key: str):
        if key in _redis_store:
            del _redis_store[key]
            return 1
        return 0
    
    def exists(self, key: str):
        return key in _redis_store
    
    def keys(self, pattern: str):
        # 简单的模式匹配
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in _redis_store.keys() if k.startswith(prefix)]
        return [k for k in _redis_store.keys() if k == pattern]
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


@pytest.fixture
def postgres_config():
    """PostgreSQL 测试配置"""
    return PostgreSQLConfig(
        host="localhost",
        port=5432,
        database="vehicle_iot_gateway_test",
        user="postgres",
        password="test"
    )


@pytest.fixture
def redis_config():
    """Redis 测试配置"""
    return RedisConfig(
        host="localhost",
        port=6379,
        db=1,  # 使用不同的数据库用于测试
        password=None
    )


@pytest.fixture(autouse=True)
def mock_redis_connection():
    """自动 Mock Redis 连接用于所有测试"""
    # 清空 redis_store 在每个测试之前
    _redis_store.clear()
    
    # Patch RedisConnection in both places where it's imported
    with patch('src.db.redis_client.RedisConnection', MockRedisConnection), \
         patch('src.secure_messaging.RedisConnection', MockRedisConnection):
        yield MockRedisConnection
    
    # 清空 redis_store 在每个测试之后
    _redis_store.clear()
