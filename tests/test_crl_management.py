"""CRL 管理功能单元测试"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
from src.certificate_manager import (
    get_crl,
    get_certificate_chain,
    check_certificate_expiry
)
from src.models.certificate import Certificate, CertificateExtensions
from src.crypto.sm2 import generate_sm2_keypair


class TestGetCRL:
    """测试 CRL 获取功能"""
    
    @pytest.fixture
    def mock_db_conn(self):
        """创建模拟数据库连接"""
        mock_conn = Mock()
        mock_conn.execute_query = Mock()
        return mock_conn
    
    def test_get_crl_empty(self, mock_db_conn):
        """测试获取空的 CRL"""
        # 模拟空的 CRL
        mock_db_conn.execute_query.return_value = []
        
        crl_list = get_crl(mock_db_conn)
        
        assert crl_list == []
        assert mock_db_conn.execute_query.call_count == 1
    
    def test_get_crl_with_revoked_certificates(self, mock_db_conn):
        """测试获取包含撤销证书的 CRL"""
        # 模拟包含多个撤销证书的 CRL（返回字典列表）
        mock_db_conn.execute_query.return_value = [
            {"serial_number": "serial123"},
            {"serial_number": "serial456"},
            {"serial_number": "serial789"}
        ]
        
        crl_list = get_crl(mock_db_conn)
        
        assert len(crl_list) == 3
        assert "serial123" in crl_list
        assert "serial456" in crl_list
        assert "serial789" in crl_list
    
    def test_get_crl_single_revoked_certificate(self, mock_db_conn):
        """测试获取包含单个撤销证书的 CRL"""
        # 模拟包含单个撤销证书的 CRL（返回字典列表）
        mock_db_conn.execute_query.return_value = [{"serial_number": "single_serial"}]
        
        crl_list = get_crl(mock_db_conn)
        
        assert len(crl_list) == 1
        assert crl_list[0] == "single_serial"
    
    def test_get_crl_query_format(self, mock_db_conn):
        """测试 CRL 查询格式正确"""
        mock_db_conn.execute_query.return_value = []
        
        get_crl(mock_db_conn)
        
        # 验证查询语句
        call_args = mock_db_conn.execute_query.call_args
        query = call_args[0][0]
        assert "SELECT serial_number FROM certificate_revocation_list" in query


class TestGetCertificateChain:
    """测试证书链获取功能"""
    
    @pytest.fixture
    def vehicle_keypair(self):
        """生成车辆密钥对"""
        return generate_sm2_keypair()
    
    @pytest.fixture
    def valid_certificate(self, vehicle_keypair):
        """创建有效证书"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        return Certificate(
            version=3,
            serial_number="test_serial_123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=VIN123,O=Test,C=CN",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
    
    def test_get_certificate_chain_single_level(self, valid_certificate):
        """测试获取单层证书链"""
        chain = get_certificate_chain(valid_certificate)
        
        assert len(chain) == 1
        assert chain[0] == valid_certificate
    
    def test_get_certificate_chain_ca_issued(self, valid_certificate):
        """测试 CA 直接签发的证书链"""
        # 证书由 CA 直接签发
        assert valid_certificate.issuer == "CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN"
        
        chain = get_certificate_chain(valid_certificate)
        
        assert len(chain) == 1
        assert chain[0].serial_number == valid_certificate.serial_number
    
    def test_get_certificate_chain_none_certificate(self):
        """测试 None 证书"""
        with pytest.raises(ValueError, match="cert 不能为 None"):
            get_certificate_chain(None)
    
    def test_get_certificate_chain_empty_serial_number(self, vehicle_keypair):
        """测试空序列号的证书"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="",  # 空序列号
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        with pytest.raises(ValueError, match="证书序列号不能为空"):
            get_certificate_chain(cert)
    
    def test_get_certificate_chain_non_ca_issuer(self, vehicle_keypair):
        """测试非 CA 签发的证书（多层证书链场景）"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        # 创建由中间 CA 签发的证书
        cert = Certificate(
            version=3,
            serial_number="intermediate_cert",
            issuer="CN=Intermediate CA,O=Test,C=CN",  # 非根 CA
            subject="CN=VIN456,O=Test,C=CN",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        # 当前实现返回单个证书
        chain = get_certificate_chain(cert)
        
        assert len(chain) == 1
        assert chain[0] == cert


class TestCheckCertificateExpiry:
    """测试证书过期检查功能"""
    
    @pytest.fixture
    def vehicle_keypair(self):
        """生成车辆密钥对"""
        return generate_sm2_keypair()
    
    def test_check_certificate_expiry_valid(self, vehicle_keypair):
        """测试检查有效证书"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="valid_cert",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow() - timedelta(days=10),
            valid_to=datetime.utcnow() + timedelta(days=100),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        result = check_certificate_expiry(cert)
        
        assert result["status"] == "valid"
        assert result["days_until_expiry"] > 0
        assert "有效" in result["message"]
        assert result["valid_from"] == cert.valid_from
        assert result["valid_to"] == cert.valid_to
        assert isinstance(result["current_time"], datetime)
    
    def test_check_certificate_expiry_expired(self, vehicle_keypair):
        """测试检查已过期证书"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="expired_cert",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow() - timedelta(days=400),
            valid_to=datetime.utcnow() - timedelta(days=35),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        result = check_certificate_expiry(cert)
        
        assert result["status"] == "expired"
        assert result["days_until_expiry"] < 0
        assert "已过期" in result["message"]
        assert "35 天" in result["message"]
    
    def test_check_certificate_expiry_not_yet_valid(self, vehicle_keypair):
        """测试检查尚未生效的证书"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="future_cert",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow() + timedelta(days=10),
            valid_to=datetime.utcnow() + timedelta(days=375),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        result = check_certificate_expiry(cert)
        
        assert result["status"] == "not_yet_valid"
        assert "尚未生效" in result["message"]
    
    def test_check_certificate_expiry_expiring_soon(self, vehicle_keypair):
        """测试检查即将过期的证书（30天内）"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="expiring_soon_cert",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow() - timedelta(days=335),
            valid_to=datetime.utcnow() + timedelta(days=15),  # 15 天后过期
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        result = check_certificate_expiry(cert)
        
        assert result["status"] == "valid"
        assert 0 < result["days_until_expiry"] <= 30
        assert "将在" in result["message"]
        assert "天后过期" in result["message"]
    
    def test_check_certificate_expiry_none_certificate(self):
        """测试 None 证书"""
        with pytest.raises(ValueError, match="cert 不能为 None"):
            check_certificate_expiry(None)
    
    def test_check_certificate_expiry_invalid_valid_from(self, vehicle_keypair):
        """测试无效的 valid_from"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="invalid_cert",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from="not_a_datetime",  # 无效类型
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        with pytest.raises(ValueError, match="cert.valid_from 必须是 datetime 对象"):
            check_certificate_expiry(cert)
    
    def test_check_certificate_expiry_invalid_valid_to(self, vehicle_keypair):
        """测试无效的 valid_to"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="invalid_cert",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow(),
            valid_to="not_a_datetime",  # 无效类型
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        with pytest.raises(ValueError, match="cert.valid_to 必须是 datetime 对象"):
            check_certificate_expiry(cert)
    
    def test_check_certificate_expiry_invalid_period(self, vehicle_keypair):
        """测试无效的有效期（valid_from >= valid_to）"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        now = datetime.utcnow()
        cert = Certificate(
            version=3,
            serial_number="invalid_period_cert",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=now + timedelta(days=10),
            valid_to=now,  # valid_to 早于 valid_from
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        with pytest.raises(ValueError, match="cert.valid_from 必须早于 cert.valid_to"):
            check_certificate_expiry(cert)
    
    def test_check_certificate_expiry_result_structure(self, vehicle_keypair):
        """测试返回结果的结构完整性"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="structure_test_cert",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow() - timedelta(days=10),
            valid_to=datetime.utcnow() + timedelta(days=100),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        result = check_certificate_expiry(cert)
        
        # 验证所有必需字段存在
        assert "status" in result
        assert "valid_from" in result
        assert "valid_to" in result
        assert "current_time" in result
        assert "days_until_expiry" in result
        assert "message" in result
        
        # 验证字段类型
        assert isinstance(result["status"], str)
        assert isinstance(result["valid_from"], datetime)
        assert isinstance(result["valid_to"], datetime)
        assert isinstance(result["current_time"], datetime)
        assert isinstance(result["days_until_expiry"], int)
        assert isinstance(result["message"], str)
    
    def test_check_certificate_expiry_does_not_modify_certificate(self, vehicle_keypair):
        """测试检查过期状态不修改证书对象"""
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="immutable_cert",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow() - timedelta(days=10),
            valid_to=datetime.utcnow() + timedelta(days=100),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        # 保存原始值
        original_serial = cert.serial_number
        original_valid_from = cert.valid_from
        original_valid_to = cert.valid_to
        
        # 执行检查
        check_certificate_expiry(cert)
        
        # 验证证书未被修改
        assert cert.serial_number == original_serial
        assert cert.valid_from == original_valid_from
        assert cert.valid_to == original_valid_to
