"""测试安全报文数据模型"""

import pytest
from datetime import datetime, timedelta
from src.models.message import MessageHeader, SecureMessage
from src.models.enums import MessageType


class TestMessageHeader:
    """测试 MessageHeader 类"""
    
    def test_create_message_header(self):
        """测试创建消息头"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        assert header.version == 1
        assert header.message_type == MessageType.DATA_TRANSFER
        assert header.sender_id == "vehicle_001"
        assert header.receiver_id == "gateway_001"
        assert header.session_id == "session_123"
    
    def test_message_header_to_dict(self):
        """测试消息头序列化"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.AUTH_REQUEST,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        data = header.to_dict()
        
        assert data["version"] == 1
        assert data["message_type"] == "AUTH_REQUEST"
        assert data["sender_id"] == "vehicle_001"
        assert data["receiver_id"] == "gateway_001"
        assert data["session_id"] == "session_123"
    
    def test_message_header_from_dict(self):
        """测试消息头反序列化"""
        data = {
            "version": 1,
            "message_type": "DATA_TRANSFER",
            "sender_id": "vehicle_001",
            "receiver_id": "gateway_001",
            "session_id": "session_123"
        }
        
        header = MessageHeader.from_dict(data)
        
        assert header.version == 1
        assert header.message_type == MessageType.DATA_TRANSFER
        assert header.sender_id == "vehicle_001"
        assert header.receiver_id == "gateway_001"
        assert header.session_id == "session_123"
    
    def test_message_header_from_dict_invalid_data(self):
        """测试反序列化无效数据"""
        # 缺少必需字段
        data = {
            "version": 1,
            "message_type": "DATA_TRANSFER"
        }
        
        with pytest.raises(ValueError, match="Invalid message header data"):
            MessageHeader.from_dict(data)
    
    def test_message_header_from_dict_invalid_message_type(self):
        """测试反序列化无效消息类型"""
        data = {
            "version": 1,
            "message_type": "INVALID_TYPE",
            "sender_id": "vehicle_001",
            "receiver_id": "gateway_001",
            "session_id": "session_123"
        }
        
        with pytest.raises(ValueError, match="Invalid message header data"):
            MessageHeader.from_dict(data)
    
    def test_message_header_validate_success(self):
        """测试消息头验证成功"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        # 不应抛出异常
        header.validate()
    
    def test_message_header_validate_invalid_version(self):
        """测试验证无效版本"""
        header = MessageHeader(
            version=0,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        with pytest.raises(ValueError, match="Invalid version"):
            header.validate()
    
    def test_message_header_validate_empty_sender_id(self):
        """测试验证空发送方 ID"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        with pytest.raises(ValueError, match="Invalid sender_id"):
            header.validate()
    
    def test_message_header_validate_empty_receiver_id(self):
        """测试验证空接收方 ID"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="",
            session_id="session_123"
        )
        
        with pytest.raises(ValueError, match="Invalid receiver_id"):
            header.validate()
    
    def test_message_header_validate_empty_session_id(self):
        """测试验证空会话 ID"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id=""
        )
        
        with pytest.raises(ValueError, match="Invalid session_id"):
            header.validate()


class TestSecureMessage:
    """测试 SecureMessage 类"""
    
    def test_create_secure_message(self):
        """测试创建安全报文"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        message = SecureMessage(
            header=header,
            encrypted_payload=b"encrypted_data",
            signature=b"signature_data" * 5,  # 64 bytes
            timestamp=datetime.now(),
            nonce=b"1234567890123456"  # 16 bytes
        )
        
        assert message.header == header
        assert message.encrypted_payload == b"encrypted_data"
        assert len(message.signature) == 70
        assert isinstance(message.timestamp, datetime)
        assert len(message.nonce) == 16
    
    def test_secure_message_to_dict(self):
        """测试安全报文序列化"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        nonce = b"1234567890123456"
        
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"sig",
            timestamp=timestamp,
            nonce=nonce
        )
        
        data = message.to_dict()
        
        assert "header" in data
        assert data["encrypted_payload"] == b"test".hex()
        assert data["signature"] == b"sig".hex()
        assert data["timestamp"] == timestamp.isoformat()
        assert data["nonce"] == nonce.hex()
    
    def test_secure_message_from_dict(self):
        """测试安全报文反序列化"""
        data = {
            "header": {
                "version": 1,
                "message_type": "DATA_TRANSFER",
                "sender_id": "vehicle_001",
                "receiver_id": "gateway_001",
                "session_id": "session_123"
            },
            "encrypted_payload": "74657374",  # "test" in hex
            "signature": "736967",  # "sig" in hex
            "timestamp": "2024-01-01T12:00:00",
            "nonce": "31323334353637383930313233343536"  # "1234567890123456" in hex
        }
        
        message = SecureMessage.from_dict(data)
        
        assert message.header.version == 1
        assert message.header.message_type == MessageType.DATA_TRANSFER
        assert message.encrypted_payload == b"test"
        assert message.signature == b"sig"
        assert message.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert message.nonce == b"1234567890123456"
    
    def test_secure_message_from_dict_invalid_data(self):
        """测试反序列化无效数据"""
        data = {
            "header": {
                "version": 1,
                "message_type": "DATA_TRANSFER",
                "sender_id": "vehicle_001",
                "receiver_id": "gateway_001",
                "session_id": "session_123"
            }
            # 缺少其他必需字段
        }
        
        with pytest.raises(ValueError, match="Invalid secure message data"):
            SecureMessage.from_dict(data)
    
    def test_is_timestamp_valid_within_tolerance(self):
        """测试时间戳在容差范围内"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        current_time = datetime.now()
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"sig",
            timestamp=current_time - timedelta(seconds=100),  # 100 秒前
            nonce=b"1234567890123456"
        )
        
        assert message.is_timestamp_valid(current_time, tolerance_seconds=300)
    
    def test_is_timestamp_valid_outside_tolerance(self):
        """测试时间戳超出容差范围"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        current_time = datetime.now()
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"sig",
            timestamp=current_time - timedelta(seconds=400),  # 400 秒前
            nonce=b"1234567890123456"
        )
        
        assert not message.is_timestamp_valid(current_time, tolerance_seconds=300)
    
    def test_is_nonce_valid_correct_length(self):
        """测试 nonce 长度正确"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"sig",
            timestamp=datetime.now(),
            nonce=b"1234567890123456"  # 16 bytes
        )
        
        assert message.is_nonce_valid()
    
    def test_is_nonce_valid_incorrect_length(self):
        """测试 nonce 长度不正确"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"sig",
            timestamp=datetime.now(),
            nonce=b"12345"  # 5 bytes, 不是 16
        )
        
        assert not message.is_nonce_valid()
    
    def test_validate_success(self):
        """测试验证成功"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        current_time = datetime.now()
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"sig",
            timestamp=current_time,
            nonce=b"1234567890123456"
        )
        
        # 不应抛出异常
        message.validate(current_time)
    
    def test_validate_invalid_nonce_length(self):
        """测试验证无效 nonce 长度"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"sig",
            timestamp=datetime.now(),
            nonce=b"12345"  # 无效长度
        )
        
        with pytest.raises(ValueError, match="Invalid nonce length"):
            message.validate()
    
    def test_validate_invalid_timestamp(self):
        """测试验证无效时间戳"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        current_time = datetime.now()
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"sig",
            timestamp=current_time - timedelta(seconds=400),  # 超出容差
            nonce=b"1234567890123456"
        )
        
        with pytest.raises(ValueError, match="Invalid timestamp"):
            message.validate(current_time)
    
    def test_validate_empty_encrypted_payload(self):
        """测试验证空加密载荷"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        message = SecureMessage(
            header=header,
            encrypted_payload=b"",  # 空载荷
            signature=b"sig",
            timestamp=datetime.now(),
            nonce=b"1234567890123456"
        )
        
        with pytest.raises(ValueError, match="Invalid encrypted_payload"):
            message.validate()
    
    def test_validate_empty_signature(self):
        """测试验证空签名"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"",  # 空签名
            timestamp=datetime.now(),
            nonce=b"1234567890123456"
        )
        
        with pytest.raises(ValueError, match="Invalid signature"):
            message.validate()
    
    def test_has_required_fields_all_present(self):
        """测试所有必需字段都存在"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        message = SecureMessage(
            header=header,
            encrypted_payload=b"test",
            signature=b"sig",
            timestamp=datetime.now(),
            nonce=b"1234567890123456"
        )
        
        assert message.has_required_fields()
    
    def test_roundtrip_serialization(self):
        """测试序列化和反序列化往返"""
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_123"
        )
        
        original = SecureMessage(
            header=header,
            encrypted_payload=b"test_data",
            signature=b"signature",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            nonce=b"1234567890123456"
        )
        
        # 序列化
        data = original.to_dict()
        
        # 反序列化
        restored = SecureMessage.from_dict(data)
        
        # 验证
        assert restored.header.version == original.header.version
        assert restored.header.message_type == original.header.message_type
        assert restored.header.sender_id == original.header.sender_id
        assert restored.header.receiver_id == original.header.receiver_id
        assert restored.header.session_id == original.header.session_id
        assert restored.encrypted_payload == original.encrypted_payload
        assert restored.signature == original.signature
        assert restored.timestamp == original.timestamp
        assert restored.nonce == original.nonce
