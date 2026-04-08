"""审计日志数据模型"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
from .enums import EventType


@dataclass
class AuditLog:
    """审计日志
    
    验证规则：
    - log_id 必须唯一
    - timestamp 必须为有效时间戳
    - vehicle_id 必须符合车辆标识格式
    - details 长度不超过 1024 字符
    """
    log_id: str
    timestamp: datetime
    event_type: EventType
    vehicle_id: str
    operation_result: bool
    details: str
    ip_address: str
    
    def __post_init__(self):
        """验证 details 长度"""
        if len(self.details) > 1024:
            self.details = self.details[:1024]
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "vehicle_id": self.vehicle_id,
            "operation_result": self.operation_result,
            "details": self.details,
            "ip_address": self.ip_address
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditLog':
        """从字典反序列化"""
        return cls(
            log_id=data["log_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            event_type=EventType(data["event_type"]) if isinstance(data["event_type"], str) else data["event_type"],
            vehicle_id=data["vehicle_id"],
            operation_result=data["operation_result"],
            details=data["details"],
            ip_address=data["ip_address"]
        )
