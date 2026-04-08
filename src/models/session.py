"""会话数据模型"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set, Dict, Any
from .enums import SessionStatus, ErrorCode


@dataclass
class AuthToken:
    """认证令牌
    
    验证规则：
    - signature 必须通过网关私钥签名
    - expires_at 必须晚于 issued_at
    """
    vehicle_id: str
    issued_at: datetime
    expires_at: datetime
    permissions: Set[str]
    signature: bytes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "permissions": list(self.permissions),
            "signature": self.signature.hex()
        }
    
    def is_expired(self, current_time: datetime) -> bool:
        """检查令牌是否过期"""
        return current_time > self.expires_at


@dataclass
class SessionInfo:
    """会话信息
    
    验证规则：
    - session_id 必须唯一且长度为 32 字节
    - sm4_session_key 必须为 128 位或 256 位
    - expires_at 必须晚于 established_at
    - status 为 ACTIVE 时，当前时间必须在 expires_at 之前
    - last_activity_time 必须在 established_at 和当前时间之间
    """
    session_id: str
    vehicle_id: str
    sm4_session_key: bytes
    established_at: datetime
    expires_at: datetime
    status: SessionStatus
    last_activity_time: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "vehicle_id": self.vehicle_id,
            "sm4_session_key": self.sm4_session_key.hex(),
            "established_at": self.established_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "last_activity_time": self.last_activity_time.isoformat()
        }
    
    def is_expired(self, current_time: datetime) -> bool:
        """检查会话是否过期"""
        return current_time > self.expires_at or self.status != SessionStatus.ACTIVE


@dataclass
class AuthResult:
    """认证结果（Success/Failure 变体）"""
    success: bool
    token: Optional[AuthToken] = None
    session_key: Optional[bytes] = None
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None
    
    @classmethod
    def create_success(cls, token: AuthToken, session_key: bytes) -> "AuthResult":
        """创建成功结果"""
        return cls(success=True, token=token, session_key=session_key)
    
    @classmethod
    def create_failure(cls, error_code: ErrorCode, error_message: str) -> "AuthResult":
        """创建失败结果"""
        return cls(success=False, error_code=error_code, error_message=error_message)
    
    def to_dict(self) -> Dict[str, Any]:
        if self.success:
            return {
                "success": True,
                "token": self.token.to_dict() if self.token else None,
                "session_key": self.session_key.hex() if self.session_key else None
            }
        else:
            return {
                "success": False,
                "error_code": self.error_code.value if self.error_code else None,
                "error_message": self.error_message
            }
