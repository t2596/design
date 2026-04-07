"""安全策略管理器

提供安全策略的持久化存储和应用功能。

功能：
- 从数据库加载安全策略
- 保存安全策略到数据库
- 应用安全策略到系统各功能
- 认证失败记录和锁定管理
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

from src.db.postgres import PostgreSQLConnection


@dataclass
class SecurityPolicy:
    """安全策略数据类"""
    session_timeout: int = 86400  # 24小时
    certificate_validity: int = 365  # 1年
    timestamp_tolerance: int = 300  # 5分钟
    concurrent_session_strategy: str = "reject_new"
    max_auth_failures: int = 5
    auth_failure_lockout_duration: int = 300  # 5分钟
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_timeout": self.session_timeout,
            "certificate_validity": self.certificate_validity,
            "timestamp_tolerance": self.timestamp_tolerance,
            "concurrent_session_strategy": self.concurrent_session_strategy,
            "max_auth_failures": self.max_auth_failures,
            "auth_failure_lockout_duration": self.auth_failure_lockout_duration,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityPolicy':
        """从字典创建"""
        return cls(
            session_timeout=data.get("session_timeout", 86400),
            certificate_validity=data.get("certificate_validity", 365),
            timestamp_tolerance=data.get("timestamp_tolerance", 300),
            concurrent_session_strategy=data.get("concurrent_session_strategy", "reject_new"),
            max_auth_failures=data.get("max_auth_failures", 5),
            auth_failure_lockout_duration=data.get("auth_failure_lockout_duration", 300),
            updated_at=data.get("updated_at"),
            updated_by=data.get("updated_by")
        )


class SecurityPolicyManager:
    """安全策略管理器"""
    
    def __init__(self, db_connection: PostgreSQLConnection):
        """初始化安全策略管理器
        
        Args:
            db_connection: PostgreSQL 数据库连接
        """
        self.db = db_connection
        self._cache: Optional[SecurityPolicy] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 60  # 缓存60秒
    
    def get_policy(self, use_cache: bool = True) -> SecurityPolicy:
        """获取当前安全策略
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            SecurityPolicy: 当前安全策略
        """
        # 检查缓存
        if use_cache and self._cache and self._cache_time:
            if datetime.now() - self._cache_time < timedelta(seconds=self._cache_ttl):
                return self._cache
        
        # 从数据库加载
        query = """
            SELECT session_timeout, certificate_validity, timestamp_tolerance,
                   concurrent_session_strategy, max_auth_failures, 
                   auth_failure_lockout_duration, updated_at, updated_by
            FROM security_policy
            ORDER BY updated_at DESC
            LIMIT 1
        """
        
        try:
            result = self.db.execute_query(query, ())
            
            if result and len(result) > 0:
                row = result[0]
                policy = SecurityPolicy(
                    session_timeout=row['session_timeout'],
                    certificate_validity=row['certificate_validity'],
                    timestamp_tolerance=row['timestamp_tolerance'],
                    concurrent_session_strategy=row['concurrent_session_strategy'],
                    max_auth_failures=row['max_auth_failures'],
                    auth_failure_lockout_duration=row['auth_failure_lockout_duration'],
                    updated_at=row['updated_at'],
                    updated_by=row['updated_by']
                )
            else:
                # 如果数据库中没有配置，返回默认配置
                policy = SecurityPolicy()
            
            # 更新缓存
            self._cache = policy
            self._cache_time = datetime.now()
            
            return policy
            
        except Exception as e:
            print(f"Failed to load security policy from database: {e}")
            # 返回默认配置
            return SecurityPolicy()
    
    def update_policy(self, policy: SecurityPolicy, updated_by: str = "admin") -> bool:
        """更新安全策略
        
        Args:
            policy: 新的安全策略
            updated_by: 更新者标识
            
        Returns:
            bool: 是否更新成功
        """
        query = """
            INSERT INTO security_policy (
                session_timeout, certificate_validity, timestamp_tolerance,
                concurrent_session_strategy, max_auth_failures,
                auth_failure_lockout_duration, updated_at, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            policy.session_timeout,
            policy.certificate_validity,
            policy.timestamp_tolerance,
            policy.concurrent_session_strategy,
            policy.max_auth_failures,
            policy.auth_failure_lockout_duration,
            datetime.now(),
            updated_by
        )
        
        try:
            rows_affected = self.db.execute_update(query, params)
            
            # 清除缓存
            self._cache = None
            self._cache_time = None
            
            return rows_affected > 0
            
        except Exception as e:
            print(f"Failed to update security policy: {e}")
            return False
    
    def record_auth_failure(self, vehicle_id: str) -> bool:
        """记录认证失败
        
        Args:
            vehicle_id: 车辆标识
            
        Returns:
            bool: 是否应该锁定该车辆
        """
        policy = self.get_policy()
        
        # 检查是否已有记录
        query = """
            SELECT failure_count, locked_until
            FROM auth_failure_records
            WHERE vehicle_id = %s
        """
        
        try:
            result = self.db.execute_query(query, (vehicle_id,))
            
            if result and len(result) > 0:
                row = result[0]
                failure_count = row['failure_count']
                locked_until = row['locked_until']
                
                # 检查是否仍在锁定期
                if locked_until and datetime.now() < locked_until:
                    return True  # 仍在锁定期
                
                # 更新失败次数
                new_count = failure_count + 1
                
                # 判断是否需要锁定
                should_lock = new_count >= policy.max_auth_failures
                locked_until = None
                if should_lock:
                    locked_until = datetime.now() + timedelta(seconds=policy.auth_failure_lockout_duration)
                
                update_query = """
                    UPDATE auth_failure_records
                    SET failure_count = %s,
                        last_failure_at = %s,
                        locked_until = %s
                    WHERE vehicle_id = %s
                """
                self.db.execute_update(update_query, (new_count, datetime.now(), locked_until, vehicle_id))
                
                return should_lock
            else:
                # 创建新记录
                insert_query = """
                    INSERT INTO auth_failure_records (vehicle_id, failure_count, first_failure_at, last_failure_at)
                    VALUES (%s, 1, %s, %s)
                """
                self.db.execute_update(insert_query, (vehicle_id, datetime.now(), datetime.now()))
                
                return False  # 第一次失败不锁定
                
        except Exception as e:
            print(f"Failed to record auth failure: {e}")
            return False
    
    def reset_auth_failures(self, vehicle_id: str) -> bool:
        """重置认证失败记录（认证成功时调用）
        
        Args:
            vehicle_id: 车辆标识
            
        Returns:
            bool: 是否重置成功
        """
        query = """
            DELETE FROM auth_failure_records
            WHERE vehicle_id = %s
        """
        
        try:
            self.db.execute_update(query, (vehicle_id,))
            return True
        except Exception as e:
            print(f"Failed to reset auth failures: {e}")
            return False
    
    def is_vehicle_locked(self, vehicle_id: str) -> bool:
        """检查车辆是否被锁定
        
        Args:
            vehicle_id: 车辆标识
            
        Returns:
            bool: 是否被锁定
        """
        query = """
            SELECT locked_until
            FROM auth_failure_records
            WHERE vehicle_id = %s
        """
        
        try:
            result = self.db.execute_query(query, (vehicle_id,))
            
            if result and len(result) > 0:
                locked_until = result[0]['locked_until']
                if locked_until and datetime.now() < locked_until:
                    return True
            
            return False
            
        except Exception as e:
            print(f"Failed to check vehicle lock status: {e}")
            return False
    
    def get_session_timeout(self) -> int:
        """获取会话超时时间（秒）"""
        return self.get_policy().session_timeout
    
    def get_certificate_validity(self) -> int:
        """获取证书有效期（天）"""
        return self.get_policy().certificate_validity
    
    def get_timestamp_tolerance(self) -> int:
        """获取时间戳容差（秒）"""
        return self.get_policy().timestamp_tolerance
    
    def get_concurrent_session_strategy(self) -> str:
        """获取并发会话策略"""
        return self.get_policy().concurrent_session_strategy
    
    def should_reject_new_session(self, vehicle_id: str, existing_session_id: str) -> bool:
        """判断是否应该拒绝新会话
        
        Args:
            vehicle_id: 车辆标识
            existing_session_id: 现有会话ID
            
        Returns:
            bool: 是否应该拒绝新会话
        """
        strategy = self.get_concurrent_session_strategy()
        return strategy == "reject_new"


def create_security_policy_manager(db_connection: PostgreSQLConnection) -> SecurityPolicyManager:
    """创建安全策略管理器
    
    Args:
        db_connection: PostgreSQL 数据库连接
        
    Returns:
        SecurityPolicyManager: 安全策略管理器实例
    """
    return SecurityPolicyManager(db_connection)
