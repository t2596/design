"""安全通信网关主服务类的单元测试"""

import pytest
from datetime import datetime, timedelta
from src.security_gateway import SecurityGateway
from src.models.certificate import Certificate, SubjectInfo, CertificateExtensions
from src.models.message import MessageType
from src.models.enums import ValidationResult, EventType
from src.crypto.sm2 import generate_sm2_keypair
from src.crypto.sm4 import generate_sm4_key
from src.certificate_manager import issue_certificate
from src.secure_messaging import secure_data_transmission, verify_and_decrypt_message
from config.database import PostgreSQLConfig, RedisConfig


@pytest.fixture
def ca_keypair():
    """生成 CA 密钥对"""
    return generate_sm2_keypair()


@pytest.fixture
def gateway_keypair():
    """生成网关密钥对"""
    return generate_sm2_keypair()


@pytest.fixture
def vehicle_keypair():
    """生成车辆密钥对"""
    return generate_sm2_keypair()


@pytest.fixture
def gateway_cert(ca_keypair, gateway_keypair):
    """生成网关证书"""
    from src.db.postgres import PostgreSQLConnection
    
    db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
    
    try:
        gateway_subject = SubjectInfo(
            vehicle_id="GATEWAY001",
            organization="Security Gateway",
            country="CN"
        )
        
        cert = issue_certificate(
            gateway_subject,
            gateway_keypair[1],  # 公钥
            ca_keypair[0],  # CA 私钥
            ca_keypair[1],  # CA 公钥
            db_conn
        )
        
        return cert
    finally:
        db_conn.close()


@pytest.fixture
def vehicle_cert(ca_keypair, vehicle_keypair):
    """生成车辆证书"""
    from src.db.postgres import PostgreSQLConnection
    
    db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
    
    try:
        vehicle_subject = SubjectInfo(
            vehicle_id="VIN123456789",
            organization="Test Vehicle Manufacturer",
            country="CN"
        )
        
        cert = issue_certificate(
            vehicle_subject,
            vehicle_keypair[1],  # 公钥
            ca_keypair[0],  # CA 私钥
            ca_keypair[1],  # CA 公钥
            db_conn
        )
        
        return cert
    finally:
        db_conn.close()


@pytest.fixture
def security_gateway(ca_keypair, gateway_keypair, gateway_cert):
    """创建安全通信网关实例"""
    gateway = SecurityGateway(
        ca_private_key=ca_keypair[0],
        ca_public_key=ca_keypair[1],
        gateway_private_key=gateway_keypair[0],
        gateway_public_key=gateway_keypair[1],
        gateway_cert=gateway_cert
    )
    
    yield gateway
    
    # 清理
    gateway.close()


class TestSecurityGatewayInitialization:
    """测试安全通信网关初始化"""
    
    def test_initialization_with_valid_keys(self, ca_keypair, gateway_keypair, gateway_cert):
        """测试使用有效密钥初始化"""
        gateway = SecurityGateway(
            ca_private_key=ca_keypair[0],
            ca_public_key=ca_keypair[1],
            gateway_private_key=gateway_keypair[0],
            gateway_public_key=gateway_keypair[1],
            gateway_cert=gateway_cert,
            use_secure_storage=False  # 禁用安全存储以便测试
        )
        
        assert gateway.ca_private_key == ca_keypair[0]
        assert gateway.ca_public_key == ca_keypair[1]
        assert gateway.gateway_private_key == gateway_keypair[0]
        assert gateway.gateway_public_key == gateway_keypair[1]
        assert gateway.gateway_cert == gateway_cert
        
        gateway.close()
    
    def test_initialization_with_invalid_ca_private_key_length(self, ca_keypair, gateway_keypair, gateway_cert):
        """测试使用无效 CA 私钥长度初始化"""
        with pytest.raises(ValueError, match="CA 私钥长度必须为 32 字节"):
            SecurityGateway(
                ca_private_key=b'invalid',
                ca_public_key=ca_keypair[1],
                gateway_private_key=gateway_keypair[0],
                gateway_public_key=gateway_keypair[1],
                gateway_cert=gateway_cert
            )
    
    def test_initialization_with_invalid_ca_public_key_length(self, ca_keypair, gateway_keypair, gateway_cert):
        """测试使用无效 CA 公钥长度初始化"""
        with pytest.raises(ValueError, match="CA 公钥长度必须为 64 字节"):
            SecurityGateway(
                ca_private_key=ca_keypair[0],
                ca_public_key=b'invalid',
                gateway_private_key=gateway_keypair[0],
                gateway_public_key=gateway_keypair[1],
                gateway_cert=gateway_cert
            )


class TestCertificateManagement:
    """测试证书管理功能"""
    
    def test_issue_vehicle_certificate(self, security_gateway, vehicle_keypair):
        """测试颁发车辆证书"""
        subject_info = SubjectInfo(
            vehicle_id="VIN987654321",
            organization="Test Vehicle",
            country="CN"
        )
        
        cert = security_gateway.issue_vehicle_certificate(
            subject_info,
            vehicle_keypair[1]  # 公钥
        )
        
        assert cert is not None
        assert cert.serial_number is not None
        assert len(cert.serial_number) > 0
        assert cert.signature is not None
        assert len(cert.signature) == 64
    
    def test_verify_vehicle_certificate(self, security_gateway, vehicle_cert):
        """测试验证车辆证书"""
        result, message = security_gateway.verify_vehicle_certificate(vehicle_cert)
        
        assert result == ValidationResult.VALID
        assert "验证通过" in message
    
    def test_revoke_vehicle_certificate(self, security_gateway, vehicle_cert):
        """测试撤销车辆证书"""
        success = security_gateway.revoke_vehicle_certificate(
            vehicle_cert.serial_number,
            reason="测试撤销"
        )
        
        assert success is True
        
        # 验证撤销后的证书
        result, message = security_gateway.verify_vehicle_certificate(vehicle_cert)
        assert result == ValidationResult.REVOKED
        assert "已被撤销" in message
    
    def test_check_certificate_status(self, security_gateway, vehicle_cert):
        """测试检查证书状态"""
        status = security_gateway.check_certificate_status(vehicle_cert)
        
        assert status is not None
        assert "status" in status
        assert status["status"] == "valid"
        assert "days_until_expiry" in status


class TestAuthentication:
    """测试身份认证功能"""
    
    def test_authenticate_vehicle_success(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试车辆认证成功"""
        auth_result = security_gateway.authenticate_vehicle(
            vehicle_cert,
            vehicle_keypair[0]  # 私钥
        )
        
        assert auth_result.success is True
        assert auth_result.token is not None
        assert auth_result.session_key is not None
        assert len(auth_result.session_key) in (16, 32)
    
    def test_authenticate_vehicle_with_expired_certificate(self, security_gateway, ca_keypair, vehicle_keypair):
        """测试使用过期证书认证"""
        from src.db.postgres import PostgreSQLConnection
        
        # 创建过期证书
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        try:
            expired_cert = Certificate(
                version=3,
                serial_number="EXPIRED123",
                issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
                subject="CN=EXPIRED_VEHICLE,O=Test,C=CN",
                valid_from=datetime.utcnow() - timedelta(days=400),
                valid_to=datetime.utcnow() - timedelta(days=35),
                public_key=vehicle_keypair[1],
                signature=b'\x00' * 64,
                signature_algorithm="SM2",
                extensions=CertificateExtensions()
            )
            
            auth_result = security_gateway.authenticate_vehicle(
                expired_cert,
                vehicle_keypair[0]
            )
            
            assert auth_result.success is False
            assert auth_result.error_code is not None
        finally:
            db_conn.close()


class TestSessionManagement:
    """测试会话管理功能"""
    
    def test_create_session(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试创建会话"""
        # 先认证
        auth_result = security_gateway.authenticate_vehicle(
            vehicle_cert,
            vehicle_keypair[0]
        )
        
        assert auth_result.success is True
        
        # 创建会话
        vehicle_id = "VIN123456789"
        session_info = security_gateway.create_session(vehicle_id, auth_result)
        
        assert session_info is not None
        assert session_info.session_id is not None
        assert len(session_info.session_id) > 0
        assert session_info.vehicle_id == vehicle_id
        assert len(session_info.sm4_session_key) in (16, 32)
    
    def test_create_session_with_failed_auth(self, security_gateway):
        """测试使用失败的认证结果创建会话"""
        from src.models.session import AuthResult
        from src.models.enums import ErrorCode
        
        failed_auth = AuthResult.create_failure(
            ErrorCode.INVALID_CERTIFICATE,
            "证书无效"
        )
        
        with pytest.raises(ValueError, match="认证结果必须是成功的"):
            security_gateway.create_session("VIN123", failed_auth)
    
    def test_terminate_session(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试终止会话"""
        # 先认证并创建会话
        auth_result = security_gateway.authenticate_vehicle(
            vehicle_cert,
            vehicle_keypair[0]
        )
        
        vehicle_id = "VIN123456789"
        session_info = security_gateway.create_session(vehicle_id, auth_result)
        
        # 终止会话
        success = security_gateway.terminate_session(
            session_info.session_id,
            vehicle_id
        )
        
        assert success is True
    
    def test_cleanup_sessions(self, security_gateway):
        """测试清理过期会话"""
        count = security_gateway.cleanup_sessions()
        
        # 清理数量应该是非负数
        assert count >= 0


class TestSecureMessaging:
    """测试安全报文传输功能"""
    
    def test_send_secure_message(self, security_gateway):
        """测试发送安全报文"""
        plain_data = b"Test message data"
        session_key = generate_sm4_key(16)
        sender_id = "GATEWAY001"
        receiver_id = "VIN123456789"
        session_id = "test_session_123"
        
        secure_msg = security_gateway.send_secure_message(
            plain_data,
            session_key,
            sender_id,
            receiver_id,
            session_id
        )
        
        assert secure_msg is not None
        assert secure_msg.header is not None
        assert secure_msg.header.sender_id == sender_id
        assert secure_msg.header.receiver_id == receiver_id
        assert secure_msg.encrypted_payload is not None
        assert secure_msg.signature is not None
        assert len(secure_msg.signature) == 64
        assert secure_msg.nonce is not None
        assert len(secure_msg.nonce) == 16
    
    def test_receive_secure_message(self, security_gateway, vehicle_keypair):
        """测试接收安全报文"""
        # 创建安全报文
        plain_data = b"Test message data"
        session_key = generate_sm4_key(16)
        sender_id = "VIN123456789"
        receiver_id = "GATEWAY001"
        session_id = "test_session_123"
        
        secure_msg = secure_data_transmission(
            plain_data,
            session_key,
            vehicle_keypair[0],  # 发送方私钥
            vehicle_keypair[1],  # 接收方公钥
            sender_id,
            receiver_id,
            session_id
        )
        
        # 接收并验证报文
        decrypted_data = security_gateway.receive_secure_message(
            secure_msg,
            session_key,
            vehicle_keypair[1],  # 发送方公钥
            sender_id
        )
        
        assert decrypted_data == plain_data
    
    def test_receive_tampered_message(self, security_gateway, vehicle_keypair):
        """测试接收被篡改的报文"""
        # 创建安全报文
        plain_data = b"Test message data"
        session_key = generate_sm4_key(16)
        sender_id = "VIN123456789"
        receiver_id = "GATEWAY001"
        session_id = "test_session_123"
        
        secure_msg = secure_data_transmission(
            plain_data,
            session_key,
            vehicle_keypair[0],
            vehicle_keypair[1],
            sender_id,
            receiver_id,
            session_id
        )
        
        # 篡改加密载荷
        tampered_payload = bytearray(secure_msg.encrypted_payload)
        tampered_payload[0] ^= 0xFF
        secure_msg.encrypted_payload = bytes(tampered_payload)
        
        # 尝试接收篡改的报文
        with pytest.raises(ValueError, match="签名验证失败"):
            security_gateway.receive_secure_message(
                secure_msg,
                session_key,
                vehicle_keypair[1],
                sender_id
            )


class TestContextManager:
    """测试上下文管理器"""
    
    def test_context_manager(self, ca_keypair, gateway_keypair, gateway_cert):
        """测试使用上下文管理器"""
        with SecurityGateway(
            ca_private_key=ca_keypair[0],
            ca_public_key=ca_keypair[1],
            gateway_private_key=gateway_keypair[0],
            gateway_public_key=gateway_keypair[1],
            gateway_cert=gateway_cert,
            use_secure_storage=False  # 禁用安全存储以便测试
        ) as gateway:
            assert gateway is not None
            assert gateway.ca_private_key == ca_keypair[0]
        
        # 上下文退出后，网关应该已关闭
        # 这里无法直接验证，但不应该抛出异常


class TestIntegration:
    """集成测试"""
    
    def test_complete_vehicle_authentication_flow(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试完整的车辆认证流程"""
        # 步骤 1：验证车辆证书
        result, message = security_gateway.verify_vehicle_certificate(vehicle_cert)
        assert result == ValidationResult.VALID
        
        # 步骤 2：认证车辆
        auth_result = security_gateway.authenticate_vehicle(
            vehicle_cert,
            vehicle_keypair[0]
        )
        assert auth_result.success is True
        
        # 步骤 3：创建会话
        vehicle_id = "VIN123456789"
        session_info = security_gateway.create_session(vehicle_id, auth_result)
        assert session_info is not None
        
        # 步骤 4：发送安全报文
        plain_data = b"Test vehicle data"
        secure_msg = security_gateway.send_secure_message(
            plain_data,
            session_info.sm4_session_key,
            "GATEWAY001",
            vehicle_id,
            session_info.session_id
        )
        assert secure_msg is not None
        
        # 步骤 5：终止会话
        success = security_gateway.terminate_session(
            session_info.session_id,
            vehicle_id
        )
        assert success is True


class TestSecureDataForwarding:
    """测试安全数据转发流程（任务 11.3）"""
    
    def test_forward_vehicle_data_to_cloud_success(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试成功转发车辆数据到云端"""
        # 步骤 1：建立会话
        success, session_info, _ = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0]
        )
        assert success is True
        
        # 步骤 2：创建车端安全报文
        plain_data = b"Vehicle sensor data: temperature=25C, speed=60km/h"
        secure_msg = secure_data_transmission(
            plain_data,
            session_info.sm4_session_key,
            vehicle_keypair[0],  # 车辆私钥
            vehicle_keypair[1],  # 车辆公钥
            "VIN123456789",
            "GATEWAY",
            session_info.session_id
        )
        
        # 步骤 3：转发数据到云端
        success, cloud_response, error_msg = security_gateway.forward_vehicle_data_to_cloud(
            "VIN123456789",
            session_info.session_id,
            secure_msg,
            vehicle_keypair[1]  # 车辆公钥
        )
        
        # 验证结果
        assert success is True
        assert cloud_response is not None
        assert error_msg is None
        assert b"Cloud processed:" in cloud_response
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, "VIN123456789")
    
    def test_forward_vehicle_data_with_invalid_session(self, security_gateway, vehicle_keypair):
        """测试使用无效会话转发数据"""
        # 创建安全报文（使用不存在的会话）
        plain_data = b"Test data"
        session_key = generate_sm4_key(16)
        secure_msg = secure_data_transmission(
            plain_data,
            session_key,
            vehicle_keypair[0],
            vehicle_keypair[1],
            "VIN123456789",
            "GATEWAY",
            "invalid_session_id"
        )
        
        # 尝试转发数据
        success, cloud_response, error_msg = security_gateway.forward_vehicle_data_to_cloud(
            "VIN123456789",
            "invalid_session_id",
            secure_msg,
            vehicle_keypair[1]
        )
        
        # 验证结果
        assert success is False
        assert cloud_response is None
        assert error_msg is not None
        assert "不存在或已过期" in error_msg
    
    def test_send_cloud_response_to_vehicle_success(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试成功发送云端响应到车辆"""
        # 步骤 1：建立会话
        success, session_info, _ = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0]
        )
        assert success is True
        
        # 步骤 2：模拟云端响应
        cloud_response = b"Cloud response: command executed successfully"
        
        # 步骤 3：发送响应到车辆
        success, secure_response, error_msg = security_gateway.send_cloud_response_to_vehicle(
            "VIN123456789",
            session_info.session_id,
            cloud_response,
            vehicle_keypair[1]
        )
        
        # 验证结果
        assert success is True, f"Failed with error: {error_msg}"
        assert secure_response is not None
        assert error_msg is None
        assert secure_response.header.message_type == MessageType.RESPONSE
        assert secure_response.header.sender_id == "GATEWAY"
        assert secure_response.header.receiver_id == "VIN123456789"
        
        # 验证车辆可以解密响应
        decrypted_response = verify_and_decrypt_message(
            secure_response,
            session_info.sm4_session_key,
            security_gateway.gateway_public_key,
            security_gateway.redis_config
        )
        assert decrypted_response == cloud_response
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, "VIN123456789")
    
    def test_send_cloud_response_with_invalid_session(self, security_gateway, vehicle_keypair):
        """测试使用无效会话发送云端响应"""
        cloud_response = b"Test response"
        
        # 尝试发送响应
        success, secure_response, error_msg = security_gateway.send_cloud_response_to_vehicle(
            "VIN123456789",
            "invalid_session_id",
            cloud_response,
            vehicle_keypair[1]
        )
        
        # 验证结果
        assert success is False
        assert secure_response is None
        assert error_msg is not None
        assert "不存在或已过期" in error_msg
    
    def test_handle_secure_data_forwarding_complete_flow(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试完整的安全数据转发流程"""
        # 步骤 1：建立会话
        success, session_info, _ = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0]
        )
        assert success is True
        
        # 步骤 2：创建车端安全报文
        plain_data = b"Vehicle telemetry data: GPS, speed, fuel level"
        secure_msg = secure_data_transmission(
            plain_data,
            session_info.sm4_session_key,
            vehicle_keypair[0],
            vehicle_keypair[1],
            "VIN123456789",
            "GATEWAY",
            session_info.session_id
        )
        
        # 步骤 3：执行完整的数据转发流程
        success, secure_response, error_msg = security_gateway.handle_secure_data_forwarding(
            "VIN123456789",
            session_info.session_id,
            secure_msg,
            vehicle_keypair[1]
        )
        
        # 验证结果
        assert success is True
        assert secure_response is not None
        assert error_msg is None
        
        # 验证响应报文
        assert secure_response.header.message_type == MessageType.RESPONSE
        assert secure_response.header.sender_id == "GATEWAY"
        assert secure_response.header.receiver_id == "VIN123456789"
        assert secure_response.header.session_id == session_info.session_id
        assert len(secure_response.signature) == 64
        assert len(secure_response.nonce) == 16
        
        # 验证车辆可以解密响应
        decrypted_response = verify_and_decrypt_message(
            secure_response,
            session_info.sm4_session_key,
            security_gateway.gateway_public_key,
            security_gateway.redis_config
        )
        assert decrypted_response is not None
        assert b"Cloud processed:" in decrypted_response
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, "VIN123456789")
    
    def test_handle_secure_data_forwarding_with_tampered_message(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试转发被篡改的消息"""
        # 步骤 1：建立会话
        success, session_info, _ = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0]
        )
        assert success is True
        
        # 步骤 2：创建车端安全报文
        plain_data = b"Original data"
        secure_msg = secure_data_transmission(
            plain_data,
            session_info.sm4_session_key,
            vehicle_keypair[0],
            vehicle_keypair[1],
            "VIN123456789",
            "GATEWAY",
            session_info.session_id
        )
        
        # 步骤 3：篡改报文
        tampered_payload = bytearray(secure_msg.encrypted_payload)
        tampered_payload[0] ^= 0xFF
        secure_msg.encrypted_payload = bytes(tampered_payload)
        
        # 步骤 4：尝试转发被篡改的报文
        success, secure_response, error_msg = security_gateway.handle_secure_data_forwarding(
            "VIN123456789",
            session_info.session_id,
            secure_msg,
            vehicle_keypair[1]
        )
        
        # 验证结果
        assert success is False
        assert secure_response is None
        assert error_msg is not None
        assert "签名验证失败" in error_msg or "篡改" in error_msg
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, "VIN123456789")
    
    def test_data_forwarding_audit_logging(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试数据转发流程的审计日志记录"""
        # 步骤 1：建立会话
        success, session_info, _ = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0]
        )
        assert success is True
        
        # 记录开始时间，用于过滤审计日志
        start_time = datetime.utcnow()
        
        # 步骤 2：创建并转发数据
        plain_data = b"Test audit logging data"
        secure_msg = secure_data_transmission(
            plain_data,
            session_info.sm4_session_key,
            vehicle_keypair[0],
            vehicle_keypair[1],
            "VIN123456789",
            "GATEWAY",
            session_info.session_id
        )
        
        success, secure_response, _ = security_gateway.handle_secure_data_forwarding(
            "VIN123456789",
            session_info.session_id,
            secure_msg,
            vehicle_keypair[1]
        )
        assert success is True
        
        # 步骤 3：查询审计日志
        logs = security_gateway.audit_logger.query_audit_logs(
            vehicle_id="VIN123456789",
            event_type=EventType.DATA_ENCRYPTED
        )
        
        # 验证审计日志
        assert len(logs) > 0
        
        # 过滤出本次测试产生的日志（时间戳在start_time之后）
        recent_logs = [log for log in logs if log.timestamp >= start_time]
        
        # 查找数据转发相关的日志
        forwarding_logs = [log for log in recent_logs if "转发" in log.details or "响应" in log.details]
        assert len(forwarding_logs) > 0
        
        # 验证至少有一个日志包含正确的session_id
        session_id_found = any(session_info.session_id in log.details for log in forwarding_logs)
        assert session_id_found, f"Expected session_id {session_info.session_id} not found in any forwarding log"
        
        # 验证所有日志的基本属性
        for log in forwarding_logs:
            assert log.vehicle_id == "VIN123456789"
            assert log.operation_result is True
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, "VIN123456789")
    
    def test_data_forwarding_with_large_payload(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试转发大数据载荷"""
        # 步骤 1：建立会话
        success, session_info, _ = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0]
        )
        assert success is True
        
        # 步骤 2：创建大数据载荷（10KB）
        plain_data = b"X" * 10240
        secure_msg = secure_data_transmission(
            plain_data,
            session_info.sm4_session_key,
            vehicle_keypair[0],
            vehicle_keypair[1],
            "VIN123456789",
            "GATEWAY",
            session_info.session_id
        )
        
        # 步骤 3：转发大数据
        success, secure_response, error_msg = security_gateway.handle_secure_data_forwarding(
            "VIN123456789",
            session_info.session_id,
            secure_msg,
            vehicle_keypair[1]
        )
        
        # 验证结果
        assert success is True
        assert secure_response is not None
        assert error_msg is None
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, "VIN123456789")
    
    def test_multiple_data_forwarding_in_same_session(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试在同一会话中多次转发数据"""
        # 步骤 1：建立会话
        success, session_info, _ = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0]
        )
        assert success is True
        
        # 步骤 2：多次转发数据
        for i in range(5):
            plain_data = f"Data packet {i}".encode('utf-8')
            secure_msg = secure_data_transmission(
                plain_data,
                session_info.sm4_session_key,
                vehicle_keypair[0],
                vehicle_keypair[1],
                "VIN123456789",
                "GATEWAY",
                session_info.session_id
            )
            
            success, secure_response, error_msg = security_gateway.handle_secure_data_forwarding(
                "VIN123456789",
                session_info.session_id,
                secure_msg,
                vehicle_keypair[1]
            )
            
            assert success is True
            assert secure_response is not None
            assert error_msg is None
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, "VIN123456789")
    
    def test_data_forwarding_sequence_diagram_flow(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试数据转发流程符合设计文档的序列图
        
        验证流程（数据加密传输流程）：
        1. 车端生成业务数据
        2. 车端 SM4 加密数据
        3. 车端 SM2 签名加密数据
        4. 车端发送安全报文到网关
        5. 网关验证 SM2 签名
        6. 网关 SM4 解密数据
        7. 网关转发业务数据到云端
        8. 云端响应数据
        9. 网关 SM4 加密响应
        10. 网关 SM2 签名响应
        11. 网关发送安全响应报文到车端
        """
        # 步骤 1-4：建立会话并创建安全报文
        success, session_info, _ = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0]
        )
        assert success is True
        
        plain_data = b"Business data from vehicle"
        secure_msg = secure_data_transmission(
            plain_data,
            session_info.sm4_session_key,
            vehicle_keypair[0],
            vehicle_keypair[1],
            "VIN123456789",
            "GATEWAY",
            session_info.session_id
        )
        
        # 验证安全报文已加密和签名
        assert secure_msg.encrypted_payload != plain_data
        assert len(secure_msg.signature) == 64
        
        # 步骤 5-11：执行完整的数据转发流程
        success, secure_response, error_msg = security_gateway.handle_secure_data_forwarding(
            "VIN123456789",
            session_info.session_id,
            secure_msg,
            vehicle_keypair[1]
        )
        
        # 验证流程成功
        assert success is True, f"数据转发失败: {error_msg}"
        assert secure_response is not None
        assert error_msg is None
        
        # 验证响应报文已加密和签名
        assert secure_response.encrypted_payload is not None
        assert len(secure_response.signature) == 64
        assert secure_response.header.message_type == MessageType.RESPONSE
        
        # 验证车辆可以解密响应（模拟步骤 12）
        decrypted_response = verify_and_decrypt_message(
            secure_response,
            session_info.sm4_session_key,
            security_gateway.gateway_public_key,
            security_gateway.redis_config
        )
        assert decrypted_response is not None
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, "VIN123456789")


class TestVehicleConnectionFlow:
    """测试车辆接入与认证流程（任务 11.2）"""
    
    def test_handle_vehicle_connection_success(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试成功的车辆接入流程"""
        # 执行完整的车辆接入流程
        success, session_info, error_msg = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0],
            ip_address="192.168.1.100"
        )
        
        # 验证结果
        assert success is True
        assert session_info is not None
        assert error_msg is None
        
        # 验证会话信息
        assert session_info.session_id is not None
        assert len(session_info.session_id) > 0
        assert session_info.vehicle_id == "VIN123456789"
        assert len(session_info.sm4_session_key) in (16, 32)
        assert session_info.status.value == "ACTIVE"
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, session_info.vehicle_id)
    
    def test_handle_vehicle_connection_with_invalid_certificate(self, security_gateway, vehicle_keypair):
        """测试使用无效证书的车辆接入"""
        from src.models.certificate import CertificateExtensions
        
        # 创建无效证书（签名错误）
        invalid_cert = Certificate(
            version=3,
            serial_number="INVALID123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=INVALID_VEHICLE,O=Test,C=CN",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_keypair[1],
            signature=b'\x00' * 64,  # 无效签名
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        # 尝试接入
        success, session_info, error_msg = security_gateway.handle_vehicle_connection(
            invalid_cert,
            vehicle_keypair[0],
            ip_address="192.168.1.101"
        )
        
        # 验证结果
        assert success is False
        assert session_info is None
        assert error_msg is not None
        assert "证书" in error_msg or "签名" in error_msg
    
    def test_handle_vehicle_connection_with_expired_certificate(self, security_gateway, vehicle_keypair):
        """测试使用过期证书的车辆接入"""
        from src.models.certificate import CertificateExtensions
        
        # 创建过期证书
        expired_cert = Certificate(
            version=3,
            serial_number="EXPIRED456",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=EXPIRED_VEHICLE,O=Test,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=400),
            valid_to=datetime.utcnow() - timedelta(days=35),
            public_key=vehicle_keypair[1],
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        # 尝试接入
        success, session_info, error_msg = security_gateway.handle_vehicle_connection(
            expired_cert,
            vehicle_keypair[0],
            ip_address="192.168.1.102"
        )
        
        # 验证结果
        assert success is False
        assert session_info is None
        assert error_msg is not None
        assert "过期" in error_msg or "证书" in error_msg
    
    def test_handle_vehicle_connection_with_revoked_certificate(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试使用已撤销证书的车辆接入"""
        # 先撤销证书
        security_gateway.revoke_vehicle_certificate(
            vehicle_cert.serial_number,
            reason="测试撤销"
        )
        
        # 尝试接入
        success, session_info, error_msg = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0],
            ip_address="192.168.1.103"
        )
        
        # 验证结果
        assert success is False
        assert session_info is None
        assert error_msg is not None
        assert "撤销" in error_msg or "证书" in error_msg
    
    def test_handle_vehicle_connection_without_ip_address(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试不提供 IP 地址的车辆接入"""
        # 执行车辆接入流程（不提供 IP 地址）
        success, session_info, error_msg = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0]
        )
        
        # 验证结果
        assert success is True
        assert session_info is not None
        assert error_msg is None
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, session_info.vehicle_id)
    
    def test_handle_vehicle_connection_audit_logging(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试车辆接入流程的审计日志记录"""
        from src.models.enums import EventType
        
        # 执行车辆接入流程
        success, session_info, error_msg = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0],
            ip_address="192.168.1.104"
        )
        
        assert success is True
        assert session_info is not None
        
        # 查询审计日志
        logs = security_gateway.audit_logger.query_audit_logs(
            vehicle_id="VIN123456789",
            event_type=EventType.AUTHENTICATION_SUCCESS
        )
        
        # 验证审计日志
        assert len(logs) > 0
        
        # 查找最新的认证成功日志
        latest_log = logs[0]
        assert latest_log.vehicle_id == "VIN123456789"
        assert latest_log.event_type == EventType.AUTHENTICATION_SUCCESS
        assert latest_log.operation_result is True
        assert session_info.session_id in latest_log.details
        assert latest_log.ip_address == "192.168.1.104"
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, session_info.vehicle_id)
    
    def test_handle_vehicle_connection_multiple_vehicles(self, security_gateway, ca_keypair):
        """测试多个车辆同时接入"""
        from src.db.postgres import PostgreSQLConnection
        from src.certificate_manager import issue_certificate
        from src.models.certificate import SubjectInfo
        from src.crypto.sm2 import generate_sm2_keypair
        
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        try:
            sessions = []
            
            # 创建并接入 3 个车辆
            for i in range(3):
                # 生成车辆密钥对
                vehicle_keypair = generate_sm2_keypair()
                
                # 颁发车辆证书
                vehicle_subject = SubjectInfo(
                    vehicle_id=f"VIN_TEST_{i:03d}",
                    organization="Test Vehicle Manufacturer",
                    country="CN"
                )
                
                vehicle_cert = issue_certificate(
                    vehicle_subject,
                    vehicle_keypair[1],
                    ca_keypair[0],
                    ca_keypair[1],
                    db_conn
                )
                
                # 执行车辆接入
                success, session_info, error_msg = security_gateway.handle_vehicle_connection(
                    vehicle_cert,
                    vehicle_keypair[0],
                    ip_address=f"192.168.1.{200 + i}"
                )
                
                assert success is True
                assert session_info is not None
                sessions.append(session_info)
            
            # 验证所有会话都已建立
            assert len(sessions) == 3
            
            # 验证会话 ID 唯一
            session_ids = [s.session_id for s in sessions]
            assert len(session_ids) == len(set(session_ids))
            
            # 清理所有会话
            for session in sessions:
                security_gateway.terminate_session(session.session_id, session.vehicle_id)
                
        finally:
            db_conn.close()
    
    def test_handle_vehicle_connection_sequence_diagram_flow(self, security_gateway, vehicle_cert, vehicle_keypair):
        """测试车辆接入流程符合设计文档的序列图
        
        验证流程：
        1. 车端发起连接请求（携带车端证书）
        2. 网关验证车端证书有效性
        3. 网关发送网关证书（隐式，在双向认证中）
        4. 车端验证网关证书（隐式，在双向认证中）
        5. 执行双向认证（SM2 签名）
        6. 建立安全会话
        7. 返回会话密钥
        """
        # 步骤 1-7：执行完整流程
        success, session_info, error_msg = security_gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0],
            ip_address="192.168.1.105"
        )
        
        # 验证流程成功
        assert success is True, f"车辆接入失败: {error_msg}"
        assert session_info is not None
        assert error_msg is None
        
        # 验证会话已建立
        assert session_info.session_id is not None
        assert session_info.vehicle_id == "VIN123456789"
        assert session_info.sm4_session_key is not None
        assert len(session_info.sm4_session_key) in (16, 32)
        
        # 验证会话状态
        assert session_info.status.value == "ACTIVE"
        assert session_info.established_at is not None
        assert session_info.expires_at > session_info.established_at
        
        # 验证审计日志已记录
        logs = security_gateway.audit_logger.query_audit_logs(
            vehicle_id="VIN123456789",
            event_type=EventType.AUTHENTICATION_SUCCESS
        )
        assert len(logs) > 0
        
        # 清理会话
        security_gateway.terminate_session(session_info.session_id, session_info.vehicle_id)
