"""身份认证模块测试"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.authentication import (
    generate_challenge,
    verify_challenge,
    authenticate_vehicle,
    authenticate_gateway,
    mutual_authentication,
    establish_session,
    close_session,
    cleanup_expired_sessions,
    handle_session_conflict
)
from src.models.certificate import Certificate, SubjectInfo, CertificateExtensions
from src.models.session import SessionInfo, AuthResult, AuthToken
from src.models.enums import SessionStatus, ErrorCode, ValidationResult
from src.crypto.sm2 import generate_sm2_keypair, sm2_sign
from src.crypto.sm4 import generate_sm4_key


class TestGenerateChallenge:
    """测试挑战值生成"""
    
    def test_challenge_length(self):
        """测试挑战值长度为 32 字节"""
        challenge = generate_challenge()
        assert len(challenge) == 32
    
    def test_challenge_uniqueness(self):
        """测试挑战值唯一性"""
        challenges = [generate_challenge() for _ in range(100)]
        # 所有挑战值应该互不相同
        assert len(set(challenges)) == 100
    
    def test_challenge_type(self):
        """测试挑战值类型为 bytes"""
        challenge = generate_challenge()
        assert isinstance(challenge, bytes)


class TestVerifyChallenge:
    """测试挑战响应验证"""
    
    def test_valid_challenge_response(self):
        """测试有效的挑战响应"""
        # 生成密钥对
        private_key, public_key = generate_sm2_keypair()
        
        # 生成挑战值
        challenge = generate_challenge()
        
        # 签名挑战值
        response = sm2_sign(challenge, private_key)
        
        # 验证响应
        result = verify_challenge(response, challenge, public_key)
        assert result is True
    
    def test_invalid_challenge_response(self):
        """测试无效的挑战响应（使用错误的公钥）"""
        # 生成两个密钥对
        private_key1, _ = generate_sm2_keypair()
        _, public_key2 = generate_sm2_keypair()
        
        # 生成挑战值
        challenge = generate_challenge()
        
        # 使用第一个私钥签名
        response = sm2_sign(challenge, private_key1)
        
        # 使用第二个公钥验证（应该失败）
        result = verify_challenge(response, challenge, public_key2)
        assert result is False
    
    def test_invalid_response_length(self):
        """测试无效的响应长度"""
        _, public_key = generate_sm2_keypair()
        challenge = generate_challenge()
        
        with pytest.raises(ValueError, match="签名响应长度必须为 64 字节"):
            verify_challenge(b"invalid", challenge, public_key)
    
    def test_invalid_challenge_length(self):
        """测试无效的挑战值长度"""
        _, public_key = generate_sm2_keypair()
        response = b"0" * 64
        
        with pytest.raises(ValueError, match="挑战值长度必须为 32 字节"):
            verify_challenge(response, b"short", public_key)
    
    def test_invalid_public_key_length(self):
        """测试无效的公钥长度"""
        challenge = generate_challenge()
        response = b"0" * 64
        
        with pytest.raises(ValueError, match="公钥长度必须为 64 字节"):
            verify_challenge(response, challenge, b"invalid")


class TestAuthenticateVehicle:
    """测试车端认证"""
    
    def test_valid_vehicle_authentication(self):
        """测试有效的车端认证"""
        # 创建模拟证书
        private_key, public_key = generate_sm2_keypair()
        cert = Certificate(
            version=3,
            serial_number="test123",
            issuer="CN=CA",
            subject="CN=Vehicle1,O=Test,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=public_key,
            signature=b"0" * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature",
                extended_key_usage="clientAuth"
            )
        )
        
        challenge = generate_challenge()
        ca_public_key = b"0" * 64
        crl_list = []
        
        # Mock verify_certificate
        with patch('src.authentication.verify_certificate') as mock_verify:
            mock_verify.return_value = (ValidationResult.VALID, "证书验证通过")
            
            result, message = authenticate_vehicle(cert, challenge, ca_public_key, crl_list)
            
            assert result is True
            assert "成功" in message
    
    def test_invalid_vehicle_certificate(self):
        """测试无效的车端证书"""
        private_key, public_key = generate_sm2_keypair()
        cert = Certificate(
            version=3,
            serial_number="test123",
            issuer="CN=CA",
            subject="CN=Vehicle1,O=Test,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=public_key,
            signature=b"0" * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature",
                extended_key_usage="clientAuth"
            )
        )
        
        challenge = generate_challenge()
        ca_public_key = b"0" * 64
        crl_list = []
        
        # Mock verify_certificate to return invalid
        with patch('src.authentication.verify_certificate') as mock_verify:
            mock_verify.return_value = (ValidationResult.INVALID, "证书已过期")
            
            result, message = authenticate_vehicle(cert, challenge, ca_public_key, crl_list)
            
            assert result is False
            assert "失败" in message


class TestAuthenticateGateway:
    """测试网关认证"""
    
    def test_valid_gateway_authentication(self):
        """测试有效的网关认证"""
        private_key, public_key = generate_sm2_keypair()
        cert = Certificate(
            version=3,
            serial_number="gateway123",
            issuer="CN=CA",
            subject="CN=Gateway1,O=Test,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=public_key,
            signature=b"0" * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature",
                extended_key_usage="serverAuth"
            )
        )
        
        ca_public_key = b"0" * 64
        crl_list = []
        
        with patch('src.authentication.verify_certificate') as mock_verify:
            mock_verify.return_value = (ValidationResult.VALID, "证书验证通过")
            
            result, message = authenticate_gateway(cert, ca_public_key, crl_list)
            
            assert result is True
            assert "成功" in message


class TestMutualAuthentication:
    """测试双向身份认证"""
    
    def test_successful_mutual_authentication(self):
        """测试成功的双向认证"""
        # 生成密钥对
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        gateway_private_key, gateway_public_key = generate_sm2_keypair()
        ca_private_key, ca_public_key = generate_sm2_keypair()
        
        # 创建证书
        vehicle_cert = Certificate(
            version=3,
            serial_number="vehicle123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=Vehicle1,O=Test,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b"0" * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature",
                extended_key_usage="clientAuth"
            )
        )
        
        gateway_cert = Certificate(
            version=3,
            serial_number="gateway123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=Gateway1,O=Test,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=gateway_public_key,
            signature=b"0" * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature",
                extended_key_usage="serverAuth"
            )
        )
        
        # Mock database and verification
        with patch('src.authentication.PostgreSQLConnection'), \
             patch('src.authentication.get_crl') as mock_crl, \
             patch('src.authentication.verify_certificate') as mock_verify:
            
            mock_crl.return_value = []
            mock_verify.return_value = (ValidationResult.VALID, "证书验证通过")
            
            result = mutual_authentication(
                vehicle_cert,
                gateway_cert,
                vehicle_private_key,
                gateway_private_key,
                ca_public_key
            )
            
            assert result.success is True
            assert result.token is not None
            assert result.session_key is not None
            assert len(result.session_key) in (16, 32)
            assert result.token.vehicle_id == "Vehicle1"
    
    def test_failed_vehicle_certificate_verification(self):
        """测试车端证书验证失败"""
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        gateway_private_key, gateway_public_key = generate_sm2_keypair()
        ca_private_key, ca_public_key = generate_sm2_keypair()
        
        vehicle_cert = Certificate(
            version=3,
            serial_number="vehicle123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=Vehicle1,O=Test,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b"0" * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature",
                extended_key_usage="clientAuth"
            )
        )
        
        gateway_cert = Certificate(
            version=3,
            serial_number="gateway123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=Gateway1,O=Test,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=gateway_public_key,
            signature=b"0" * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature",
                extended_key_usage="serverAuth"
            )
        )
        
        with patch('src.authentication.PostgreSQLConnection'), \
             patch('src.authentication.get_crl') as mock_crl, \
             patch('src.authentication.verify_certificate') as mock_verify:
            
            mock_crl.return_value = []
            # 第一次调用返回失败（车端证书）
            mock_verify.return_value = (ValidationResult.INVALID, "证书已过期")
            
            result = mutual_authentication(
                vehicle_cert,
                gateway_cert,
                vehicle_private_key,
                gateway_private_key,
                ca_public_key
            )
            
            assert result.success is False
            assert result.error_code == ErrorCode.INVALID_CERTIFICATE


class TestEstablishSession:
    """测试会话建立"""
    
    def test_successful_session_establishment(self):
        """测试成功建立会话"""
        vehicle_id = "Vehicle1"
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(hours=24)
        
        auth_token = AuthToken(
            vehicle_id=vehicle_id,
            issued_at=issued_at,
            expires_at=expires_at,
            permissions={"data_transfer", "heartbeat"},
            signature=b"0" * 64
        )
        
        # Mock Redis connection
        mock_redis = Mock()
        mock_redis.connect = Mock()
        mock_redis.set = Mock(return_value=True)
        mock_redis.close = Mock()
        
        session_info = establish_session(vehicle_id, auth_token, mock_redis)
        
        assert session_info.session_id is not None
        assert len(session_info.session_id) == 64  # 32 bytes hex = 64 chars
        assert session_info.vehicle_id == vehicle_id
        assert len(session_info.sm4_session_key) in (16, 32)
        assert session_info.status == SessionStatus.ACTIVE
        assert session_info.expires_at > session_info.established_at
        
        # Verify Redis was called
        assert mock_redis.set.called
    
    def test_expired_token(self):
        """测试过期的令牌"""
        vehicle_id = "Vehicle1"
        issued_at = datetime.utcnow() - timedelta(hours=25)
        expires_at = issued_at + timedelta(hours=24)
        
        auth_token = AuthToken(
            vehicle_id=vehicle_id,
            issued_at=issued_at,
            expires_at=expires_at,
            permissions={"data_transfer"},
            signature=b"0" * 64
        )
        
        with pytest.raises(ValueError, match="认证令牌已过期"):
            establish_session(vehicle_id, auth_token)
    
    def test_mismatched_vehicle_id(self):
        """测试不匹配的车辆 ID"""
        vehicle_id = "Vehicle1"
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(hours=24)
        
        auth_token = AuthToken(
            vehicle_id="Vehicle2",  # 不同的 vehicle_id
            issued_at=issued_at,
            expires_at=expires_at,
            permissions={"data_transfer"},
            signature=b"0" * 64
        )
        
        with pytest.raises(ValueError, match="vehicle_id 不匹配"):
            establish_session(vehicle_id, auth_token)


class TestCloseSession:
    """测试会话关闭"""
    
    def test_successful_session_close(self):
        """测试成功关闭会话"""
        session_id = "test_session_123"
        
        # Mock Redis connection
        mock_redis = Mock()
        mock_redis.connect = Mock()
        mock_redis.get = Mock(return_value=json.dumps({
            "session_id": session_id,
            "vehicle_id": "Vehicle1",
            "sm4_session_key": "0" * 32,
            "established_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "status": "ACTIVE",
            "last_activity_time": datetime.utcnow().isoformat()
        }).encode('utf-8'))
        mock_redis.delete = Mock(return_value=1)
        mock_redis.close = Mock()
        
        result = close_session(session_id, mock_redis)
        
        assert result is True
        assert mock_redis.delete.call_count == 2  # session key and vehicle key
    
    def test_close_nonexistent_session(self):
        """测试关闭不存在的会话"""
        session_id = "nonexistent_session"
        
        mock_redis = Mock()
        mock_redis.connect = Mock()
        mock_redis.get = Mock(return_value=None)
        mock_redis.close = Mock()
        
        result = close_session(session_id, mock_redis)
        
        assert result is False


class TestHandleSessionConflict:
    """测试会话冲突处理"""
    
    def test_no_conflict(self):
        """测试没有会话冲突"""
        vehicle_id = "Vehicle1"
        
        mock_redis = Mock()
        mock_redis.connect = Mock()
        mock_redis.get = Mock(return_value=None)
        mock_redis.close = Mock()
        
        result, message = handle_session_conflict(vehicle_id, "reject_new", mock_redis)
        
        assert result is True
        assert "没有会话冲突" in message
    
    def test_reject_new_strategy(self):
        """测试拒绝新会话策略"""
        vehicle_id = "Vehicle1"
        
        mock_redis = Mock()
        mock_redis.connect = Mock()
        mock_redis.get = Mock(return_value=b"existing_session_id")
        mock_redis.close = Mock()
        
        result, message = handle_session_conflict(vehicle_id, "reject_new", mock_redis)
        
        assert result is False
        assert "拒绝新会话" in message
    
    def test_terminate_old_strategy(self):
        """测试终止旧会话策略"""
        vehicle_id = "Vehicle1"
        
        mock_redis = Mock()
        mock_redis.connect = Mock()
        mock_redis.get = Mock(side_effect=[
            b"existing_session_id",  # First call for conflict check
            json.dumps({
                "session_id": "existing_session_id",
                "vehicle_id": vehicle_id,
                "sm4_session_key": "0" * 32,
                "established_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "status": "ACTIVE",
                "last_activity_time": datetime.utcnow().isoformat()
            }).encode('utf-8')  # Second call for close_session
        ])
        mock_redis.delete = Mock(return_value=1)
        mock_redis.close = Mock()
        
        result, message = handle_session_conflict(vehicle_id, "terminate_old", mock_redis)
        
        assert result is True
        assert "终止旧会话" in message
    
    def test_invalid_strategy(self):
        """测试无效的策略"""
        vehicle_id = "Vehicle1"
        
        with pytest.raises(ValueError, match="无效的策略"):
            handle_session_conflict(vehicle_id, "invalid_strategy")


class TestCleanupExpiredSessions:
    """测试过期会话清理"""
    
    def test_cleanup_expired_sessions(self):
        """测试清理过期会话"""
        mock_redis = Mock()
        mock_redis.connect = Mock()
        mock_redis.close = Mock()
        
        # 由于 Redis 自动清理过期键，这个函数应该返回 0
        count = cleanup_expired_sessions(mock_redis)
        
        assert count == 0
        assert mock_redis.connect.called
