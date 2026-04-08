"""安全报文传输模块测试"""

import pytest
from datetime import datetime, timedelta
from src.secure_messaging import secure_data_transmission, verify_and_decrypt_message
from src.models.message import SecureMessage, MessageHeader
from src.models.enums import MessageType
from src.crypto.sm2 import generate_sm2_keypair
from src.crypto.sm4 import generate_sm4_key
from src.db.redis_client import RedisConnection


class TestSecureDataTransmission:
    """测试安全数据传输功能"""
    
    def test_secure_data_transmission_success(self):
        """测试成功的安全数据传输
        
        验证需求: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
        """
        # 准备测试数据
        plain_data = b"Test vehicle data payload"
        session_key = generate_sm4_key(16)
        sender_private_key, sender_public_key = generate_sm2_keypair()
        receiver_private_key, receiver_public_key = generate_sm2_keypair()
        
        sender_id = "vehicle_001"
        receiver_id = "gateway_001"
        session_id = "session_12345"
        
        # 执行安全数据传输
        secure_message = secure_data_transmission(
            plain_data=plain_data,
            session_key=session_key,
            sender_private_key=sender_private_key,
            receiver_public_key=receiver_public_key,
            sender_id=sender_id,
            receiver_id=receiver_id,
            session_id=session_id
        )
        
        # 验证返回的安全报文
        assert isinstance(secure_message, SecureMessage)
        assert secure_message.header.sender_id == sender_id
        assert secure_message.header.receiver_id == receiver_id
        assert secure_message.header.session_id == session_id
        assert secure_message.header.version == 1
        assert secure_message.header.message_type == MessageType.DATA_TRANSFER
        
        # 验证 nonce 长度为 16 字节（需求 8.1）
        assert len(secure_message.nonce) == 16
        
        # 验证时间戳已添加（需求 8.2）
        assert isinstance(secure_message.timestamp, datetime)
        assert abs((datetime.now() - secure_message.timestamp).total_seconds()) < 2
        
        # 验证加密载荷非空（需求 8.4）
        assert secure_message.encrypted_payload is not None
        assert len(secure_message.encrypted_payload) > 0
        assert secure_message.encrypted_payload != plain_data  # 确保已加密
        
        # 验证签名长度为 64 字节（需求 8.5）
        assert len(secure_message.signature) == 64
        
        # 验证消息头已创建（需求 8.3）
        assert secure_message.header is not None


class TestVerifyAndDecryptMessage:
    """测试安全报文验证与解密功能"""
    
    def test_verify_and_decrypt_success(self, redis_config):
        """测试成功的报文验证与解密"""
        # 准备测试数据
        plain_data = b"Test vehicle data for decryption"
        session_key = generate_sm4_key(16)
        sender_private_key, sender_public_key = generate_sm2_keypair()
        receiver_private_key, receiver_public_key = generate_sm2_keypair()
        
        # 创建安全报文
        secure_message = secure_data_transmission(
            plain_data=plain_data,
            session_key=session_key,
            sender_private_key=sender_private_key,
            receiver_public_key=receiver_public_key,
            sender_id="vehicle_010",
            receiver_id="gateway_010",
            session_id="session_vwx"
        )
        
        # 验证并解密
        decrypted_data = verify_and_decrypt_message(
            secure_message=secure_message,
            session_key=session_key,
            sender_public_key=sender_public_key,
            redis_config=redis_config
        )
        
        # 验证解密后的数据与原始数据一致
        assert decrypted_data == plain_data
    
    def test_verify_and_decrypt_replay_attack_detection(self, redis_config):
        """测试重放攻击检测
        
        验证需求: 9.3, 9.4
        """
        plain_data = b"Test data for replay attack"
        session_key = generate_sm4_key(16)
        sender_private_key, sender_public_key = generate_sm2_keypair()
        receiver_private_key, receiver_public_key = generate_sm2_keypair()
        
        # 创建安全报文
        secure_message = secure_data_transmission(
            plain_data=plain_data,
            session_key=session_key,
            sender_private_key=sender_private_key,
            receiver_public_key=receiver_public_key,
            sender_id="vehicle_replay",
            receiver_id="gateway_replay",
            session_id="session_replay"
        )
        
        # 第一次验证应该成功
        decrypted_data = verify_and_decrypt_message(
            secure_message=secure_message,
            session_key=session_key,
            sender_public_key=sender_public_key,
            redis_config=redis_config
        )
        assert decrypted_data == plain_data
        
        # 第二次使用相同的报文应该失败（检测到重放攻击）
        with pytest.raises(ValueError, match="Nonce 已使用：检测到重放攻击"):
            verify_and_decrypt_message(
                secure_message=secure_message,
                session_key=session_key,
                sender_public_key=sender_public_key,
                redis_config=redis_config
            )
    
    def test_verify_and_decrypt_nonce_marked_as_used(self, redis_config):
        """测试 nonce 被正确标记为已使用
        
        验证需求: 9.5
        """
        from src.db.redis_client import RedisConnection
        
        plain_data = b"Test nonce marking"
        session_key = generate_sm4_key(16)
        sender_private_key, sender_public_key = generate_sm2_keypair()
        receiver_private_key, receiver_public_key = generate_sm2_keypair()
        
        secure_message = secure_data_transmission(
            plain_data=plain_data,
            session_key=session_key,
            sender_private_key=sender_private_key,
            receiver_public_key=receiver_public_key,
            sender_id="vehicle_nonce_test",
            receiver_id="gateway_nonce_test",
            session_id="session_nonce_test"
        )
        
        # 验证前 nonce 不应该存在
        redis_conn = RedisConnection(redis_config)
        nonce_key = f"nonce:{secure_message.nonce.hex()}"
        assert not redis_conn.exists(nonce_key)
        
        # 验证并解密
        decrypted_data = verify_and_decrypt_message(
            secure_message=secure_message,
            session_key=session_key,
            sender_public_key=sender_public_key,
            redis_config=redis_config
        )
        assert decrypted_data == plain_data
        
        # 验证后 nonce 应该被标记为已使用
        assert redis_conn.exists(nonce_key)
        
        # 清理测试数据
        redis_conn.delete(nonce_key)
        redis_conn.close()
