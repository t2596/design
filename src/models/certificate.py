"""证书数据模型"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class SubjectInfo:
    """证书主体信息"""
    vehicle_id: str
    organization: str
    country: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "organization": self.organization,
            "country": self.country
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubjectInfo':
        """从字典反序列化"""
        return cls(
            vehicle_id=data["vehicle_id"],
            organization=data["organization"],
            country=data["country"]
        )


@dataclass
class CertificateExtensions:
    """证书扩展信息"""
    key_usage: str = "digitalSignature,keyEncipherment"
    extended_key_usage: str = "clientAuth,serverAuth"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_usage": self.key_usage,
            "extended_key_usage": self.extended_key_usage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CertificateExtensions':
        """从字典反序列化"""
        return cls(
            key_usage=data.get("key_usage", "digitalSignature,keyEncipherment"),
            extended_key_usage=data.get("extended_key_usage", "clientAuth,serverAuth")
        )


@dataclass
class Certificate:
    """数字证书
    
    验证规则：
    - serial_number 必须唯一
    - valid_from 必须早于 valid_to
    - 当前时间必须在 valid_from 和 valid_to 之间
    - signature 必须通过 CA 公钥验证
    - signature_algorithm 必须为 "SM2"
    """
    version: int
    serial_number: str
    issuer: str
    subject: str
    valid_from: datetime
    valid_to: datetime
    public_key: bytes
    signature: bytes
    signature_algorithm: str
    extensions: CertificateExtensions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "serial_number": self.serial_number,
            "issuer": self.issuer,
            "subject": self.subject,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat(),
            "public_key": self.public_key.hex(),
            "signature": self.signature.hex(),
            "signature_algorithm": self.signature_algorithm,
            "extensions": self.extensions.to_dict()
        }
    
    def is_valid_period(self, current_time: datetime) -> bool:
        """检查证书是否在有效期内"""
        return self.valid_from <= current_time <= self.valid_to
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Certificate':
        """从字典反序列化"""
        return cls(
            version=data["version"],
            serial_number=data["serial_number"],
            issuer=data["issuer"],
            subject=data["subject"],
            valid_from=datetime.fromisoformat(data["valid_from"]),
            valid_to=datetime.fromisoformat(data["valid_to"]),
            public_key=bytes.fromhex(data["public_key"]),
            signature=bytes.fromhex(data["signature"]),
            signature_algorithm=data["signature_algorithm"],
            extensions=CertificateExtensions.from_dict(data["extensions"])
        )
