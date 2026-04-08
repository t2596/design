"""PostgreSQL 数据库连接"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
from config import PostgreSQLConfig


class PostgreSQLConnection:
    """PostgreSQL 连接管理器"""
    
    def __init__(self, config: PostgreSQLConfig):
        self.config = config
        self.connection: Optional[psycopg2.extensions.connection] = None
    
    def connect(self):
        """建立数据库连接"""
        if self.connection is None or self.connection.closed:
            self.connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )
    
    def close(self):
        """关闭数据库连接"""
        if self.connection and not self.connection.closed:
            self.connection.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        self.connect()
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """执行更新操作并返回影响的行数"""
        self.connect()
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
