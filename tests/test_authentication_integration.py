"""身份认证模块集成测试

测试完整的认证流程，包括证书验证、双向认证和会话管理。
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.authentication import (
    mutual_authentication,
    establish_session,
    close_session,
    handle_session_conflict
)
from src.models.certificate import Certificate, CertificateExtensions
from src.models.enums import ValidationResult, SessionStatus
from src.crypto.sm2 import generate_sm2_keypair
from src.certificate_manager import issue_certificate
from src.models.certificate import SubjectInfo


class TestAuthenticationIntegration:
    """集成测试：完整的认证流程"""
    
    def test_complete_authentication_flow(self):
        """测试完整的认证流程：证书颁发 -> 双向认证 -> 会话建立"""
        # 步骤 1：生成密钥对
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        gateway_private_key, gateway_public_key = generate_sm2_keypair()
        ca_private_key, ca_public_key = generate_sm2_keypair()
        
        # 步骤 2：创建证书
        vehicle_cert = Certificate(
            version=3,
            serial_number="vehicle_integration_test",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=IntegrationVehicle,O=TestOrg,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b"0" * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature,keyEncipherment",
                extended_key_usage="clientAuth,serverAuth"
            )
        )
        
        gateway_cert = Certificate(
            version=3,
            serial_number="gateway_integration_test",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=IntegrationGateway,O=TestOrg,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=gateway_public_key,
            signature=b"0" * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature,keyEncipherment",
                extended_key_usage="clientAuth,serverAuth"
            )
        )
        
        # 步骤 3：执行双向认证
        with patch('src.authentication.PostgreSQLConnection'), \
             patch('src.authentication.get_crl') as mock_crl, \
             patch('src.authentication.verify_certificate') as mock_verify:
            
            mock_crl.return_value = []
            mock_verify.return_value = (ValidationResult.VALID, "证书验证通过")
            
            auth_result = mutual_authentication(
                vehicle_cert,
                gateway_cert,
                vehicle_private_key,
                gateway_private_key,
                ca_public_key
            )
            
            # 验证认证结果
            assert auth_result.success is True
            assert auth_result.token is not None
            assert auth_result.session_key is not None
            assert auth_result.token.vehicle_id == "IntegrationVehicle"
            
            # 步骤 4：建立会话
            mock_redis = Mock()
            mock_redis.connect = Mock()
            mock_redis.set = Mock(return_value=True)
            mock_redis.close = Mock()
            
            session_info = establish_session(
                auth_result.token.vehicle_id,
                auth_result.token,
                mock_redis
            )
            
            # 验证会话信息
            assert session_info.session_id is not None
            assert session_info.vehicle_id == "IntegrationVehicle"
            assert session_info.status == SessionStatus.ACTIVE
            assert len(session_info.sm4_session_key) in (16, 32)
            
            # 步骤 5：关闭会话
            import json
            mock_redis.get = Mock(return_value=json.dumps(session_info.to_dict()).encode('utf-8'))
            mock_redis.delete = Mock(return_value=1)
            
            close_result = close_session(session_info.session_id, mock_redis)
            assert close_result is True
    
    def test_authentication_with_expired_certificate(self):
        """测试使用过期证书的认证流程"""
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        gateway_private_key, gateway_public_key = generate_sm2_keypair()
        ca_private_key, ca_public_key = generate_sm2_keypair()
        
        # 创建过期的证书
        vehicle_cert = Certificate(
            version=3,
            serial_number="expired_vehicle",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=ExpiredVehicle,O=TestOrg,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=400),
            valid_to=datetime.utcnow() - timedelta(days=35),  # 已过期
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
            serial_number="gateway_test",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=Gateway,O=TestOrg,C=CN",
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
            # 模拟证书过期
            mock_verify.return_value = (ValidationResult.INVALID, "证书已过期")
            
            auth_result = mutual_authentication(
                vehicle_cert,
                gateway_cert,
                vehicle_private_key,
                gateway_private_key,
                ca_public_key
            )
            
            # 验证认证失败
            assert auth_result.success is False
            assert auth_result.error_code is not None
    
    def test_session_conflict_handling(self):
        """测试会话冲突处理流程"""
        vehicle_id = "ConflictVehicle"
        
        # 模拟已存在的会话
        mock_redis = Mock()
        mock_redis.connect = Mock()
        mock_redis.get = Mock(return_value=b"existing_session_id")
        mock_redis.close = Mock()
        
        # 测试拒绝新会话策略
        result, message = handle_session_conflict(vehicle_id, "reject_new", mock_redis)
        assert result is False
        assert "拒绝新会话" in message
        
        # 测试终止旧会话策略
        import json
        mock_redis.get = Mock(side_effect=[
            b"existing_session_id",
            json.dumps({
                "session_id": "existing_session_id",
                "vehicle_id": vehicle_id,
                "sm4_session_key": "0" * 32,
                "established_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "status": "ACTIVE",
                "last_activity_time": datetime.utcnow().isoformat()
            }).encode('utf-8')
        ])
        mock_redis.delete = Mock(return_value=1)
        
        result, message = handle_session_conflict(vehicle_id, "terminate_old", mock_redis)
        assert result is True
        assert "终止旧会话" in message
    
    def test_multiple_vehicles_authentication(self):
        """测试多个车辆同时认证"""
        ca_private_key, ca_public_key = generate_sm2_keypair()
        gateway_private_key, gateway_public_key = generate_sm2_keypair()
        
        gateway_cert = Certificate(
            version=3,
            serial_number="gateway_multi",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=Gateway,O=TestOrg,C=CN",
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
        
        # 创建多个车辆
        vehicles = []
        for i in range(3):
            vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
            vehicle_cert = Certificate(
                version=3,
                serial_number=f"vehicle_{i}",
                issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
                subject=f"CN=Vehicle{i},O=TestOrg,C=CN",
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
            vehicles.append((vehicle_cert, vehicle_private_key))
        
        # 对每个车辆执行认证
        with patch('src.authentication.PostgreSQLConnection'), \
             patch('src.authentication.get_crl') as mock_crl, \
             patch('src.authentication.verify_certificate') as mock_verify:
            
            mock_crl.return_value = []
            mock_verify.return_value = (ValidationResult.VALID, "证书验证通过")
            
            auth_results = []
            for vehicle_cert, vehicle_private_key in vehicles:
                auth_result = mutual_authentication(
                    vehicle_cert,
                    gateway_cert,
                    vehicle_private_key,
                    gateway_private_key,
                    ca_public_key
                )
                auth_results.append(auth_result)
            
            # 验证所有认证都成功
            assert all(result.success for result in auth_results)
            
            # 验证每个车辆都有唯一的会话密钥
            session_keys = [result.session_key for result in auth_results]
            assert len(set(session_keys)) == len(session_keys)  # 所有密钥都不同
    
    def test_authentication_with_revoked_certificate(self):
        """测试使用被撤销证书的认证流程"""
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        gateway_private_key, gateway_public_key = generate_sm2_keypair()
        ca_private_key, ca_public_key = generate_sm2_keypair()
        
        vehicle_cert = Certificate(
            version=3,
            serial_number="revoked_vehicle",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=RevokedVehicle,O=TestOrg,C=CN",
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
            serial_number="gateway_test",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=Gateway,O=TestOrg,C=CN",
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
            
            # 模拟证书在 CRL 中
            mock_crl.return_value = ["revoked_vehicle"]
            mock_verify.return_value = (ValidationResult.REVOKED, "证书已被撤销")
            
            auth_result = mutual_authentication(
                vehicle_cert,
                gateway_cert,
                vehicle_private_key,
                gateway_private_key,
                ca_public_key
            )
            
            # 验证认证失败
            assert auth_result.success is False
            assert auth_result.error_code is not None
