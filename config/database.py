"""数据库配置"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class PostgreSQLConfig:
    """PostgreSQL 配置"""
    host: str
    port: int
    database: str
    user: str
    password: str
    
    @classmethod
    def from_env(cls) -> "PostgreSQLConfig":
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "vehicle_iot_gateway"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "")
        )
    
    def get_connection_string(self) -> str:
        """获取连接字符串"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class RedisConfig:
    """Redis 配置"""
    host: str
    port: int
    db: int
    password: Optional[str]
    
    @classmethod
    def from_env(cls) -> "RedisConfig":
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD")
        )
