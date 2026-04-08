"""测试证书数据模型"""

import pytest
from datetime import datetime, timedelta
from src.models.certificate import Certificate, SubjectInfo, CertificateExtensions


def test_subject_info_serialization():
    """测试 SubjectInfo 序列化和反序列化"""
    subject = SubjectInfo(
        vehicle_id="VIN123456789",
        organization="某汽车制造商",
        country="CN"
    )
    
    # 序列化
    data = subject.to_dict()
    assert data["vehicle_id"] == "VIN123456789"
    assert data["organization"] == "某汽车制造商"
    assert data["country"] == "CN"
    
    # 反序列化
    restored = SubjectInfo.from_dict(data)
    assert restored.vehicle_id == subject.vehicle_id
    assert restored.organization == subject.organization
    assert restored.country == subject.country


def test_certificate_extensions_serialization():
    """测试 CertificateExtensions 序列化和反序列化"""
    extensions = CertificateExtensions(
        key_usage="digitalSignature,keyEncipherment",
        extended_key_usage="clientAuth,serverAuth"
    )
    
    # 序列化
    data = extensions.to_dict()
    assert data["key_usage"] == "digitalSignature,keyEncipherment"
    assert data["extended_key_usage"] == "clientAuth,serverAuth"
    
    # 反序列化
    restored = CertificateExtensions.from_dict(data)
    assert restored.key_usage == extensions.key_usage
    assert restored.extended_key_usage == extensions.extended_key_usage


def test_certificate_extensions_default_values():
    """测试 CertificateExtensions 默认值"""
    extensions = CertificateExtensions()
    assert extensions.key_usage == "digitalSignature,keyEncipherment"
    assert extensions.extended_key_usage == "clientAuth,serverAuth"


def test_certificate_serialization():
    """测试 Certificate 序列化和反序列化"""
    now = datetime.now()
    valid_from = now
    valid_to = now + timedelta(days=365)
    
    cert = Certificate(
        version=3,
        serial_number="1234567890ABCDEF",
        issuer="CN=Test CA, O=Test Org, C=CN",
        subject="CN=Vehicle123, O=Test Org, C=CN",
        valid_from=valid_from,
        valid_to=valid_to,
        public_key=b'\x04' + b'\x00' * 64,  # 65 bytes uncompressed public key
        signature=b'\x00' * 64,  # 64 bytes signature
        signature_algorithm="SM2",
        extensions=CertificateExtensions()
    )
    
    # 序列化
    data = cert.to_dict()
    assert data["version"] == 3
    assert data["serial_number"] == "1234567890ABCDEF"
    assert data["issuer"] == "CN=Test CA, O=Test Org, C=CN"
    assert data["subject"] == "CN=Vehicle123, O=Test Org, C=CN"
    assert data["signature_algorithm"] == "SM2"
    assert isinstance(data["public_key"], str)  # hex string
    assert isinstance(data["signature"], str)  # hex string
    
    # 反序列化
    restored = Certificate.from_dict(data)
    assert restored.version == cert.version
    assert restored.serial_number == cert.serial_number
    assert restored.issuer == cert.issuer
    assert restored.subject == cert.subject
    assert restored.valid_from == cert.valid_from
    assert restored.valid_to == cert.valid_to
    assert restored.public_key == cert.public_key
    assert restored.signature == cert.signature
    assert restored.signature_algorithm == cert.signature_algorithm
    assert restored.extensions.key_usage == cert.extensions.key_usage


def test_certificate_is_valid_period():
    """测试证书有效期检查"""
    now = datetime.now()
    
    # 有效证书
    valid_cert = Certificate(
        version=3,
        serial_number="VALID123",
        issuer="CN=CA",
        subject="CN=Vehicle",
        valid_from=now - timedelta(days=1),
        valid_to=now + timedelta(days=364),
        public_key=b'\x04' + b'\x00' * 64,
        signature=b'\x00' * 64,
        signature_algorithm="SM2",
        extensions=CertificateExtensions()
    )
    assert valid_cert.is_valid_period(now) is True
    
    # 过期证书
    expired_cert = Certificate(
        version=3,
        serial_number="EXPIRED123",
        issuer="CN=CA",
        subject="CN=Vehicle",
        valid_from=now - timedelta(days=366),
        valid_to=now - timedelta(days=1),
        public_key=b'\x04' + b'\x00' * 64,
        signature=b'\x00' * 64,
        signature_algorithm="SM2",
        extensions=CertificateExtensions()
    )
    assert expired_cert.is_valid_period(now) is False
    
    # 未生效证书
    future_cert = Certificate(
        version=3,
        serial_number="FUTURE123",
        issuer="CN=CA",
        subject="CN=Vehicle",
        valid_from=now + timedelta(days=1),
        valid_to=now + timedelta(days=365),
        public_key=b'\x04' + b'\x00' * 64,
        signature=b'\x00' * 64,
        signature_algorithm="SM2",
        extensions=CertificateExtensions()
    )
    assert future_cert.is_valid_period(now) is False


def test_certificate_roundtrip():
    """测试证书完整的序列化-反序列化往返"""
    now = datetime.now()
    
    original = Certificate(
        version=3,
        serial_number="ROUNDTRIP123",
        issuer="CN=Test CA, O=Test Org, C=CN",
        subject="CN=Vehicle456, O=Test Org, C=CN",
        valid_from=now,
        valid_to=now + timedelta(days=365),
        public_key=bytes.fromhex("04" + "ab" * 64),
        signature=bytes.fromhex("cd" * 64),
        signature_algorithm="SM2",
        extensions=CertificateExtensions(
            key_usage="digitalSignature",
            extended_key_usage="clientAuth"
        )
    )
    
    # 序列化后反序列化
    data = original.to_dict()
    restored = Certificate.from_dict(data)
    
    # 验证所有字段
    assert restored.version == original.version
    assert restored.serial_number == original.serial_number
    assert restored.issuer == original.issuer
    assert restored.subject == original.subject
    assert restored.valid_from == original.valid_from
    assert restored.valid_to == original.valid_to
    assert restored.public_key == original.public_key
    assert restored.signature == original.signature
    assert restored.signature_algorithm == original.signature_algorithm
    assert restored.extensions.key_usage == original.extensions.key_usage
    assert restored.extensions.extended_key_usage == original.extensions.extended_key_usage
