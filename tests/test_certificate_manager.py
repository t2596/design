"""证书管理模块单元测试"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from src.certificate_manager import (
    generate_unique_serial_number,
    create_distinguished_name,
    create_certificate_extensions,
    encode_tbs_certificate,
    issue_certificate
)
from src.models.certificate import SubjectInfo, Certificate, CertificateExtensions
from src.crypto.sm2 import generate_sm2_keypair


class TestGenerateUniqueSerialNumber:
    """测试唯一序列号生成"""
    
    def test_serial_number_length(self):
        """测试序列号长度为 64 字符"""
        serial = generate_unique_serial_number()
        assert len(serial) == 64
    
    def test_serial_number_is_hex(self):
        """测试序列号是十六进制字符串"""
        serial = generate_unique_serial_number()
        # 验证所有字符都是十六进制字符
        assert all(c in '0123456789abcdef' for c in serial)
    
    def test_serial_numbers_are_unique(self):
        """测试生成的序列号是唯一的"""
        serials = [generate_unique_serial_number() for _ in range(100)]
        # 验证所有序列号都不相同
        assert len(serials) == len(set(serials))


class TestCreateDistinguishedName:
    """测试识别名称创建"""
    
    def test_distinguished_name_format(self):
        """测试识别名称格式正确"""
        subject_info = SubjectInfo(
            vehicle_id="VIN123456789",
            organization="Test Org",
            country="CN"
        )
        dn = create_distinguished_name(subject_info)
        assert dn == "CN=VIN123456789,O=Test Org,C=CN"
    
    def test_distinguished_name_with_special_chars(self):
        """测试包含特殊字符的识别名称"""
        subject_info = SubjectInfo(
            vehicle_id="VIN-123-456",
            organization="Test & Co.",
            country="US"
        )
        dn = create_distinguished_name(subject_info)
        assert "VIN-123-456" in dn
        assert "Test & Co." in dn


class TestCreateCertificateExtensions:
    """测试证书扩展创建"""
    
    def test_default_extensions(self):
        """测试默认扩展值"""
        subject_info = SubjectInfo(
            vehicle_id="VIN123",
            organization="Test",
            country="CN"
        )
        ext = create_certificate_extensions(subject_info)
        assert ext.key_usage == "digitalSignature,keyEncipherment"
        assert ext.extended_key_usage == "clientAuth,serverAuth"


class TestEncodeTBSCertificate:
    """测试待签名证书编码"""
    
    def test_encode_produces_bytes(self):
        """测试编码产生字节序列"""
        cert = Certificate(
            version=3,
            serial_number="test123",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=b'\x00' * 64,
            signature=b'',
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        tbs = encode_tbs_certificate(cert)
        assert isinstance(tbs, bytes)
        assert len(tbs) > 0
    
    def test_encode_is_deterministic(self):
        """测试相同证书的编码结果一致"""
        cert = Certificate(
            version=3,
            serial_number="test123",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime(2024, 1, 1, 0, 0, 0),
            valid_to=datetime(2025, 1, 1, 0, 0, 0),
            public_key=b'\x00' * 64,
            signature=b'',
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        tbs1 = encode_tbs_certificate(cert)
        tbs2 = encode_tbs_certificate(cert)
        assert tbs1 == tbs2


class TestIssueCertificate:
    """测试证书颁发功能"""
    
    @pytest.fixture
    def ca_keypair(self):
        """生成 CA 密钥对"""
        return generate_sm2_keypair()
    
    @pytest.fixture
    def vehicle_keypair(self):
        """生成车辆密钥对"""
        return generate_sm2_keypair()
    
    @pytest.fixture
    def subject_info(self):
        """创建测试用证书主体信息"""
        return SubjectInfo(
            vehicle_id="VIN123456789",
            organization="Test Vehicle Manufacturer",
            country="CN"
        )
    
    @pytest.fixture
    def mock_db_conn(self):
        """创建模拟数据库连接"""
        mock_conn = Mock()
        mock_conn.execute_update = Mock()
        return mock_conn
    
    def test_issue_certificate_success(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试成功颁发证书"""
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = issue_certificate(
            subject_info,
            vehicle_public_key,
            ca_private_key,
            ca_public_key,
            mock_db_conn
        )
        
        # 验证证书基本属性
        assert cert.version == 3
        assert len(cert.serial_number) == 64
        assert cert.signature_algorithm == "SM2"
        assert cert.valid_from < cert.valid_to
        
        # 验证有效期为 1 年
        validity_period = cert.valid_to - cert.valid_from
        assert 364 <= validity_period.days <= 366  # 允许 1 天误差
        
        # 验证签名存在且长度正确
        assert cert.signature is not None
        assert len(cert.signature) == 64
        
        # 验证数据库操作被调用
        assert mock_db_conn.execute_update.call_count == 2  # 存储证书 + 审计日志
    
    def test_issue_certificate_invalid_subject_info(self, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试无效的主体信息"""
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        with pytest.raises(ValueError, match="subject_info 不能为 None"):
            issue_certificate(None, vehicle_public_key, ca_private_key, ca_public_key, mock_db_conn)
    
    def test_issue_certificate_empty_vehicle_id(self, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试空的车辆标识"""
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        subject_info = SubjectInfo(
            vehicle_id="",
            organization="Test",
            country="CN"
        )
        
        with pytest.raises(ValueError, match="vehicle_id 不能为空"):
            issue_certificate(subject_info, vehicle_public_key, ca_private_key, ca_public_key, mock_db_conn)
    
    def test_issue_certificate_invalid_public_key_length(self, subject_info, ca_keypair, mock_db_conn):
        """测试无效的公钥长度"""
        ca_private_key, ca_public_key = ca_keypair
        invalid_public_key = b'\x00' * 32  # 错误长度
        
        with pytest.raises(ValueError, match="public_key 长度必须为 64 字节"):
            issue_certificate(subject_info, invalid_public_key, ca_private_key, ca_public_key, mock_db_conn)
    
    def test_issue_certificate_invalid_private_key_length(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试无效的私钥长度"""
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        invalid_private_key = b'\x00' * 16  # 错误长度
        
        with pytest.raises(ValueError, match="ca_private_key 长度必须为 32 字节"):
            issue_certificate(subject_info, vehicle_public_key, invalid_private_key, ca_public_key, mock_db_conn)
    
    def test_issue_certificate_signature_verification(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试证书签名可以验证"""
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = issue_certificate(
            subject_info,
            vehicle_public_key,
            ca_private_key,
            ca_public_key,
            mock_db_conn
        )
        
        # 验证签名
        from src.crypto.sm2 import sm2_verify
        tbs = encode_tbs_certificate(cert)
        assert sm2_verify(tbs, cert.signature, ca_public_key)
    
    def test_issue_certificate_subject_fields(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试证书主体字段正确"""
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = issue_certificate(
            subject_info,
            vehicle_public_key,
            ca_private_key,
            ca_public_key,
            mock_db_conn
        )
        
        # 验证主体字段
        assert subject_info.vehicle_id in cert.subject
        assert subject_info.organization in cert.subject
        assert subject_info.country in cert.subject
    
    def test_issue_certificate_issuer_is_ca(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试证书颁发者是 CA"""
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = issue_certificate(
            subject_info,
            vehicle_public_key,
            ca_private_key,
            ca_public_key,
            mock_db_conn
        )
        
        assert "Vehicle IoT Security Gateway CA" in cert.issuer
    
    def test_issue_certificate_public_key_stored(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试证书包含正确的公钥"""
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = issue_certificate(
            subject_info,
            vehicle_public_key,
            ca_private_key,
            ca_public_key,
            mock_db_conn
        )
        
        assert cert.public_key == vehicle_public_key


class TestVerifyCertificate:
    """测试证书验证功能"""
    
    @pytest.fixture
    def ca_keypair(self):
        """生成 CA 密钥对"""
        return generate_sm2_keypair()
    
    @pytest.fixture
    def vehicle_keypair(self):
        """生成车辆密钥对"""
        return generate_sm2_keypair()
    
    @pytest.fixture
    def subject_info(self):
        """创建测试用证书主体信息"""
        return SubjectInfo(
            vehicle_id="VIN123456789",
            organization="Test Vehicle Manufacturer",
            country="CN"
        )
    
    @pytest.fixture
    def mock_db_conn(self):
        """创建模拟数据库连接"""
        mock_conn = Mock()
        mock_conn.execute_update = Mock()
        return mock_conn
    
    @pytest.fixture
    def valid_certificate(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """创建有效证书"""
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        return issue_certificate(
            subject_info,
            vehicle_public_key,
            ca_private_key,
            ca_public_key,
            mock_db_conn
        )
    
    def test_verify_valid_certificate(self, valid_certificate, ca_keypair):
        """测试验证有效证书"""
        from src.certificate_manager import verify_certificate
        from src.models.enums import ValidationResult
        
        ca_private_key, ca_public_key = ca_keypair
        crl_list = []  # 空的撤销列表
        
        result, message = verify_certificate(valid_certificate, ca_public_key, crl_list)
        
        assert result == ValidationResult.VALID
        assert message == "证书验证通过"
    
    def test_verify_certificate_expired(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试验证过期证书"""
        from src.certificate_manager import verify_certificate
        from src.models.enums import ValidationResult
        
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        # 创建已过期的证书
        cert = Certificate(
            version=3,
            serial_number="expired123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=VIN123,O=Test,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=400),
            valid_to=datetime.utcnow() - timedelta(days=35),  # 35 天前过期
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        crl_list = []
        result, message = verify_certificate(cert, ca_public_key, crl_list)
        
        assert result == ValidationResult.INVALID
        assert message == "证书已过期"
    
    def test_verify_certificate_not_yet_valid(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试验证尚未生效的证书"""
        from src.certificate_manager import verify_certificate
        from src.models.enums import ValidationResult
        
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        # 创建尚未生效的证书
        cert = Certificate(
            version=3,
            serial_number="future123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=VIN123,O=Test,C=CN",
            valid_from=datetime.utcnow() + timedelta(days=10),  # 10 天后生效
            valid_to=datetime.utcnow() + timedelta(days=375),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        crl_list = []
        result, message = verify_certificate(cert, ca_public_key, crl_list)
        
        assert result == ValidationResult.INVALID
        assert message == "证书尚未生效"
    
    def test_verify_revoked_certificate(self, valid_certificate, ca_keypair):
        """测试验证已撤销的证书"""
        from src.certificate_manager import verify_certificate
        from src.models.enums import ValidationResult
        
        ca_private_key, ca_public_key = ca_keypair
        
        # 将证书序列号添加到撤销列表
        crl_list = [valid_certificate.serial_number]
        
        result, message = verify_certificate(valid_certificate, ca_public_key, crl_list)
        
        assert result == ValidationResult.REVOKED
        assert message == "证书已被撤销"
    
    def test_verify_certificate_invalid_signature(self, subject_info, vehicle_keypair, ca_keypair, mock_db_conn):
        """测试验证签名无效的证书"""
        from src.certificate_manager import verify_certificate
        from src.models.enums import ValidationResult
        
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        # 创建证书但使用错误的签名
        cert = Certificate(
            version=3,
            serial_number="invalid_sig123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=VIN123,O=Test,C=CN",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,  # 无效签名
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        crl_list = []
        result, message = verify_certificate(cert, ca_public_key, crl_list)
        
        assert result == ValidationResult.INVALID
        assert message == "证书签名验证失败"
    
    def test_verify_certificate_invalid_format_empty_serial(self, vehicle_keypair, ca_keypair):
        """测试验证格式无效的证书（空序列号）"""
        from src.certificate_manager import verify_certificate
        from src.models.enums import ValidationResult
        
        ca_private_key, ca_public_key = ca_keypair
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
        
        crl_list = []
        result, message = verify_certificate(cert, ca_public_key, crl_list)
        
        assert result == ValidationResult.INVALID
        assert message == "证书格式错误"
    
    def test_verify_certificate_invalid_format_wrong_algorithm(self, vehicle_keypair, ca_keypair):
        """测试验证格式无效的证书（错误的签名算法）"""
        from src.certificate_manager import verify_certificate
        from src.models.enums import ValidationResult
        
        ca_private_key, ca_public_key = ca_keypair
        vehicle_private_key, vehicle_public_key = vehicle_keypair
        
        cert = Certificate(
            version=3,
            serial_number="test123",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="RSA",  # 错误的算法
            extensions=CertificateExtensions()
        )
        
        crl_list = []
        result, message = verify_certificate(cert, ca_public_key, crl_list)
        
        assert result == ValidationResult.INVALID
        assert message == "证书格式错误"
    
    def test_verify_certificate_invalid_format_wrong_public_key_length(self, ca_keypair):
        """测试验证格式无效的证书（错误的公钥长度）"""
        from src.certificate_manager import verify_certificate
        from src.models.enums import ValidationResult
        
        ca_private_key, ca_public_key = ca_keypair
        
        cert = Certificate(
            version=3,
            serial_number="test123",
            issuer="CN=CA",
            subject="CN=Test",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=b'\x00' * 32,  # 错误长度
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        crl_list = []
        result, message = verify_certificate(cert, ca_public_key, crl_list)
        
        assert result == ValidationResult.INVALID
        assert message == "证书格式错误"
    
    def test_verify_certificate_none_certificate(self, ca_keypair):
        """测试验证 None 证书"""
        from src.certificate_manager import verify_certificate
        
        ca_private_key, ca_public_key = ca_keypair
        crl_list = []
        
        with pytest.raises(ValueError, match="certificate 不能为 None"):
            verify_certificate(None, ca_public_key, crl_list)
    
    def test_verify_certificate_none_ca_public_key(self, valid_certificate):
        """测试验证时 CA 公钥为 None"""
        from src.certificate_manager import verify_certificate
        
        crl_list = []
        
        with pytest.raises(ValueError, match="ca_public_key 不能为 None"):
            verify_certificate(valid_certificate, None, crl_list)
    
    def test_verify_certificate_invalid_ca_public_key_length(self, valid_certificate):
        """测试验证时 CA 公钥长度无效"""
        from src.certificate_manager import verify_certificate
        
        crl_list = []
        invalid_ca_public_key = b'\x00' * 32  # 错误长度
        
        with pytest.raises(ValueError, match="ca_public_key 长度必须为 64 字节"):
            verify_certificate(valid_certificate, invalid_ca_public_key, crl_list)
    
    def test_verify_certificate_none_crl_list(self, valid_certificate, ca_keypair):
        """测试验证时 CRL 列表为 None"""
        from src.certificate_manager import verify_certificate
        
        ca_private_key, ca_public_key = ca_keypair
        
        with pytest.raises(ValueError, match="crl_list 不能为 None"):
            verify_certificate(valid_certificate, ca_public_key, None)
    
    def test_verify_certificate_with_multiple_revoked_certs(self, valid_certificate, ca_keypair):
        """测试验证时 CRL 包含多个撤销证书"""
        from src.certificate_manager import verify_certificate
        from src.models.enums import ValidationResult
        
        ca_private_key, ca_public_key = ca_keypair
        
        # CRL 包含多个撤销证书，包括当前证书
        crl_list = ["serial1", "serial2", valid_certificate.serial_number, "serial3"]
        
        result, message = verify_certificate(valid_certificate, ca_public_key, crl_list)
        
        assert result == ValidationResult.REVOKED
        assert message == "证书已被撤销"



class TestRevokeCertificate:
    """测试证书撤销功能"""
    
    @pytest.fixture
    def ca_keypair(self):
        """生成 CA 密钥对"""
        return generate_sm2_keypair()
    
    @pytest.fixture
    def vehicle_keypair(self):
        """生成车辆密钥对"""
        return generate_sm2_keypair()
    
    @pytest.fixture
    def subject_info(self):
        """创建测试用证书主体信息"""
        return SubjectInfo(
            vehicle_id="VIN123456789",
            organization="Test Vehicle Manufacturer",
            country="CN"
        )
    
    @pytest.fixture
    def mock_db_conn(self):
        """创建模拟数据库连接"""
        mock_conn = Mock()
        mock_conn.execute_update = Mock()
        mock_conn.execute_query = Mock()
        return mock_conn
    
    def test_revoke_certificate_success(self, mock_db_conn):
        """测试成功撤销证书"""
        from src.certificate_manager import revoke_certificate
        
        serial_number = "test_serial_123"
        
        # 模拟证书存在
        mock_db_conn.execute_query.side_effect = [
            [(serial_number,)],  # 证书存在
            [],  # 证书不在 CRL 中
            [(serial_number,)]  # 验证证书已添加到 CRL
        ]
        
        result = revoke_certificate(serial_number, "测试撤销", mock_db_conn)
        
        assert result is True
        # 验证数据库操作被调用
        assert mock_db_conn.execute_query.call_count == 3
        assert mock_db_conn.execute_update.call_count == 2  # 添加到 CRL + 审计日志
    
    def test_revoke_certificate_with_reason(self, mock_db_conn):
        """测试带原因的证书撤销"""
        from src.certificate_manager import revoke_certificate
        
        serial_number = "test_serial_456"
        reason = "密钥泄露"
        
        # 模拟证书存在
        mock_db_conn.execute_query.side_effect = [
            [(serial_number,)],  # 证书存在
            [],  # 证书不在 CRL 中
            [(serial_number,)]  # 验证证书已添加到 CRL
        ]
        
        result = revoke_certificate(serial_number, reason, mock_db_conn)
        
        assert result is True
        # 验证撤销原因被传递
        call_args = mock_db_conn.execute_update.call_args_list[0]
        assert reason in call_args[0][1]
    
    def test_revoke_certificate_without_reason(self, mock_db_conn):
        """测试不带原因的证书撤销"""
        from src.certificate_manager import revoke_certificate
        
        serial_number = "test_serial_789"
        
        # 模拟证书存在
        mock_db_conn.execute_query.side_effect = [
            [(serial_number,)],  # 证书存在
            [],  # 证书不在 CRL 中
            [(serial_number,)]  # 验证证书已添加到 CRL
        ]
        
        result = revoke_certificate(serial_number, None, mock_db_conn)
        
        assert result is True
        # 验证使用默认原因
        call_args = mock_db_conn.execute_update.call_args_list[0]
        assert "未指定原因" in call_args[0][1]
    
    def test_revoke_certificate_already_revoked(self, mock_db_conn):
        """测试撤销已撤销的证书"""
        from src.certificate_manager import revoke_certificate
        
        serial_number = "already_revoked_123"
        
        # 模拟证书存在且已在 CRL 中
        mock_db_conn.execute_query.side_effect = [
            [(serial_number,)],  # 证书存在
            [(serial_number,)]  # 证书已在 CRL 中
        ]
        
        result = revoke_certificate(serial_number, "测试", mock_db_conn)
        
        # 应该返回 True（幂等操作）
        assert result is True
        # 不应该再次添加到 CRL
        assert mock_db_conn.execute_update.call_count == 0
    
    def test_revoke_certificate_not_found(self, mock_db_conn):
        """测试撤销不存在的证书"""
        from src.certificate_manager import revoke_certificate
        
        serial_number = "nonexistent_serial"
        
        # 模拟证书不存在
        mock_db_conn.execute_query.return_value = []
        
        with pytest.raises(RuntimeError, match="证书不存在"):
            revoke_certificate(serial_number, "测试", mock_db_conn)
    
    def test_revoke_certificate_empty_serial_number(self, mock_db_conn):
        """测试撤销空序列号的证书"""
        from src.certificate_manager import revoke_certificate
        
        with pytest.raises(ValueError, match="serial_number 不能为空"):
            revoke_certificate("", "测试", mock_db_conn)
    
    def test_revoke_certificate_none_serial_number(self, mock_db_conn):
        """测试撤销 None 序列号的证书"""
        from src.certificate_manager import revoke_certificate
        
        with pytest.raises(ValueError, match="serial_number 不能为空"):
            revoke_certificate(None, "测试", mock_db_conn)
    
    def test_revoke_certificate_serial_number_too_long(self, mock_db_conn):
        """测试撤销序列号过长的证书"""
        from src.certificate_manager import revoke_certificate
        
        long_serial = "x" * 65  # 超过 64 字符
        
        with pytest.raises(ValueError, match="serial_number 长度不能超过 64 字符"):
            revoke_certificate(long_serial, "测试", mock_db_conn)
    
    def test_revoke_certificate_audit_log_recorded(self, mock_db_conn):
        """测试证书撤销时记录审计日志"""
        from src.certificate_manager import revoke_certificate
        
        serial_number = "audit_test_123"
        
        # 模拟证书存在
        mock_db_conn.execute_query.side_effect = [
            [(serial_number,)],  # 证书存在
            [],  # 证书不在 CRL 中
            [(serial_number,)]  # 验证证书已添加到 CRL
        ]
        
        result = revoke_certificate(serial_number, "审计测试", mock_db_conn)
        
        assert result is True
        # 验证审计日志被记录（第二次 execute_update 调用）
        assert mock_db_conn.execute_update.call_count == 2
        
        # 检查审计日志调用
        audit_call = mock_db_conn.execute_update.call_args_list[1]
        audit_params = audit_call[0][1]
        # 验证审计日志包含 CERTIFICATE_REVOKED 事件类型
        assert "CERTIFICATE_REVOKED" in str(audit_params)
    
    def test_revoke_certificate_verification_failure(self, mock_db_conn):
        """测试证书撤销后验证失败"""
        from src.certificate_manager import revoke_certificate
        
        serial_number = "verify_fail_123"
        
        # 模拟证书存在，但撤销后验证失败
        mock_db_conn.execute_query.side_effect = [
            [(serial_number,)],  # 证书存在
            [],  # 证书不在 CRL 中
            []  # 验证时证书未在 CRL 中（异常情况）
        ]
        
        with pytest.raises(RuntimeError, match="证书撤销失败：未能添加到 CRL"):
            revoke_certificate(serial_number, "测试", mock_db_conn)
