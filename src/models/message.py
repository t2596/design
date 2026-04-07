"""安全报文数据模型"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
from .enums import MessageType


@dataclass
class MessageHeader:
    """消息头
    
    包含发送方和接收方标识
    
    验证需求: 8.3
    """
    version: int
    message_type: MessageType
    sender_id: str
    receiver_id: str
    session_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "version": self.version,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageHeader':
        """从字典反序列化
        
        Args:
            data: 包含消息头数据的字典
            
        Returns:
            MessageHeader 实例
            
        Raises:
            ValueError: 如果数据格式无效
        """
        try:
            return cls(
                version=data["version"],
                message_type=MessageType(data["message_type"]),
                sender_id=data["sender_id"],
                receiver_id=data["receiver_id"],
                session_id=data["session_id"]
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid message header data: {e}")
    
    def validate(self) -> None:
        """验证消息头字段
        
        Raises:
            ValueError: 如果验证失败
        """
        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("Invalid version: must be a positive integer")
        
        if not isinstance(self.message_type, MessageType):
            raise ValueError("Invalid message_type: must be a MessageType enum")
        
        if not self.sender_id or not isinstance(self.sender_id, str):
            raise ValueError("Invalid sender_id: must be a non-empty string")
        
        if not self.receiver_id or not isinstance(self.receiver_id, str):
            raise ValueError("Invalid receiver_id: must be a non-empty string")
        
        if not self.session_id or not isinstance(self.session_id, str):
            raise ValueError("Invalid session_id: must be a non-empty string")


@dataclass
class SecureMessage:
    """安全报文
    
    验证规则：
    - timestamp 不得超过当前时间 ±5 分钟（防重放攻击）
    - nonce 必须唯一且长度为 16 字节
    - signature 必须通过发送方公钥验证
    - encrypted_payload 必须使用 SM4 加密
    
    验证需求: 8.3, 8.6
    """
    header: MessageHeader
    encrypted_payload: bytes
    signature: bytes
    timestamp: datetime
    nonce: bytes
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "header": self.header.to_dict(),
            "encrypted_payload": self.encrypted_payload.hex(),
            "signature": self.signature.hex(),
            "timestamp": self.timestamp.isoformat(),
            "nonce": self.nonce.hex()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecureMessage':
        """从字典反序列化
        
        Args:
            data: 包含安全报文数据的字典
            
        Returns:
            SecureMessage 实例
            
        Raises:
            ValueError: 如果数据格式无效
        """
        try:
            return cls(
                header=MessageHeader.from_dict(data["header"]),
                encrypted_payload=bytes.fromhex(data["encrypted_payload"]),
                signature=bytes.fromhex(data["signature"]),
                timestamp=datetime.fromisoformat(data["timestamp"]),
                nonce=bytes.fromhex(data["nonce"])
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid secure message data: {e}")
    
    def is_timestamp_valid(self, current_time: datetime, tolerance_seconds: int = 300) -> bool:
        """检查时间戳是否在有效范围内（默认 5 分钟）
        
        Args:
            current_time: 当前时间
            tolerance_seconds: 时间容差（秒），默认 300 秒（5 分钟）
            
        Returns:
            如果时间戳在有效范围内返回 True，否则返回 False
        """
        time_diff = abs((current_time - self.timestamp).total_seconds())
        return time_diff <= tolerance_seconds
    
    def is_nonce_valid(self) -> bool:
        """检查 nonce 是否有效（长度为 16 字节）
        
        Returns:
            如果 nonce 长度为 16 字节返回 True，否则返回 False
        """
        return len(self.nonce) == 16
    
    def validate(self, current_time: datetime = None, tolerance_seconds: int = 300) -> None:
        """验证安全报文的所有字段
        
        Args:
            current_time: 当前时间，如果为 None 则使用系统当前时间
            tolerance_seconds: 时间容差（秒），默认 300 秒（5 分钟）
            
        Raises:
            ValueError: 如果验证失败
        """
        # 验证消息头
        self.header.validate()
        
        # 验证 nonce 长度
        if not self.is_nonce_valid():
            raise ValueError(f"Invalid nonce length: expected 16 bytes, got {len(self.nonce)} bytes")
        
        # 验证时间戳
        if current_time is None:
            current_time = datetime.now()
        
        if not self.is_timestamp_valid(current_time, tolerance_seconds):
            raise ValueError(
                f"Invalid timestamp: message timestamp {self.timestamp.isoformat()} "
                f"is outside the valid range (±{tolerance_seconds} seconds from {current_time.isoformat()})"
            )
        
        # 验证加密载荷非空
        if not self.encrypted_payload:
            raise ValueError("Invalid encrypted_payload: must not be empty")
        
        # 验证签名非空
        if not self.signature:
            raise ValueError("Invalid signature: must not be empty")
    
    def has_required_fields(self) -> bool:
        """检查是否包含所有必需字段
        
        Returns:
            如果包含所有必需字段返回 True，否则返回 False
        """
        return all([
            self.header is not None,
            self.encrypted_payload is not None,
            self.signature is not None,
            self.timestamp is not None,
            self.nonce is not None
        ])
