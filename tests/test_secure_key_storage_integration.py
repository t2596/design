"""集成测试：安全密钥存储与系统集成

测试 SecureKeyStorage 与 certificate_manager 和 authentication 模块的集成。
验证需求: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6
"""

import pytest
import time
from datetime import datetime, timedelta
from src.secure_key_storage import SecureKeyStorage, get_secure_key_storage
from src.certificate_manager import issue_certificate
from src.authentication import establish_session, close_session
from src.models.certificate import SubjectInfo
from src.models.session import AuthToken
from src.crypto.sm2 import generate_sm2_keypair
from src.crypto.sm4 import generate_sm4_key


class TestSecureKeyStorageIntegration:
    """测试安全密钥存储集成"""
    
    def test_ca_private_key_storage_in_certificate_issuance(self):
        """测试证书颁发时 CA 私钥的安全存储
        
        验证需求: 19.1, 19.6
        """
        # 生成 CA 密钥对
        ca_private_key, ca_public_key = generate_sm2_keypair()
        
        # 生成车辆密钥对
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        
        # 创建证书主体信息
        subject_info = SubjectInfo(
            vehicle_id="TEST_VEHICLE_001",
            organization="Test Org",
            country="CN"
        )
        
        # 清空安全存储
        secure_storage = get_secure_key_storage()
        secure_storage.clear_all_keys()
        
        # 颁发证书（启用安全存储）
        certificate = issue_certificate(
            subject_info=subject_info,
            public_key=vehicle_public_key,
            ca_private_key=ca_private_key,
            ca_public_key=ca_public_key,
            db_conn=None,
            use_secure_storage=True
        )
        
        # 验证证书颁发成功
        assert certificate is not None
        assert certificate.serial_number is not None
        
        # 验证 CA 私钥已存储到安全存储区
        stored_key = secure_storage.retrieve_key("ca_private_key")
        assert stored_key is not None
        assert stored_key == ca_private_key
        
        # 验证密钥元数据
        metadata = secure_storage.get_key_metadata("ca_private_key")
        assert metadata is not None
        assert metadata.key_type == "ca_private"
        assert metadata.rotation_interval_hours == 24
        
        # 清理
        secure_storage.clear_all_keys()
    
    def test_session_key_storage_in_session_establishment(self):
        """测试会话建立时会话密钥的安全存储
        
        验证需求: 19.3, 19.5
        """
        # 创建认证令牌
        vehicle_id = "TEST_VEHICLE_002"
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(hours=24)
        
        auth_token = AuthToken(
            vehicle_id=vehicle_id,
            issued_at=issued_at,
            expires_at=expires_at,
            permissions={"data_transfer", "heartbeat"},
            signature=b"0" * 64
        )
        
        # 清空安全存储
        secure_storage = get_secure_key_storage()
        secure_storage.clear_all_keys()
        
        # 建立会话（启用安全存储）
        session_info = establish_session(
            vehicle_id=vehicle_id,
            auth_token=auth_token,
            redis_conn=None,
            use_secure_storage=True
        )
        
        # 验证会话建立成功
        assert session_info is not None
        assert session_info.session_id is not None
        assert len(session_info.sm4_session_key) in (16, 32)
        
        # 验证会话密钥已存储到安全存储区
        stored_key = secure_storage.retrieve_key(session_info.session_id)
        assert stored_key is not None
        assert stored_key == session_info.sm4_session_key
        
        # 验证密钥元数据
        metadata = secure_storage.get_key_metadata(session_info.session_id)
        assert metadata is not None
        assert metadata.key_type == "session"
        assert metadata.rotation_interval_hours == 24
        
        # 清理
        close_session(session_info.session_id, use_secure_storage=True)
        secure_storage.clear_all_keys()
    
    def test_session_key_secure_clearing_on_close(self):
        """测试会话关闭时会话密钥的安全清除
        
        验证需求: 19.4, 19.6
        """
        # 创建认证令牌
        vehicle_id = "TEST_VEHICLE_003"
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(hours=24)
        
        auth_token = AuthToken(
            vehicle_id=vehicle_id,
            issued_at=issued_at,
            expires_at=expires_at,
            permissions={"data_transfer", "heartbeat"},
            signature=b"0" * 64
        )
        
        # 清空安全存储
        secure_storage = get_secure_key_storage()
        secure_storage.clear_all_keys()
        
        # 建立会话
        session_info = establish_session(
            vehicle_id=vehicle_id,
            auth_token=auth_token,
            redis_conn=None,
            use_secure_storage=True
        )
        
        session_id = session_info.session_id
        
        # 验证密钥已存储
        stored_key = secure_storage.retrieve_key(session_id)
        assert stored_key is not None
        
        # 关闭会话（启用安全清除）
        result = close_session(session_id, use_secure_storage=True)
        assert result is True
        
        # 验证密钥已被安全清除
        cleared_key = secure_storage.retrieve_key(session_id)
        assert cleared_key is None
        
        # 验证元数据也已删除
        metadata = secure_storage.get_key_metadata(session_id)
        assert metadata is None
        
        # 清理
        secure_storage.clear_all_keys()
    
    def test_automatic_key_rotation_mechanism(self):
        """测试自动密钥轮换机制
        
        验证需求: 19.5
        """
        # 创建安全存储实例
        secure_storage = SecureKeyStorage()
        
        # 生成测试密钥
        test_key = generate_sm4_key(16)
        key_id = "test_rotation_key"
        
        # 存储密钥（设置短轮换间隔用于测试）
        secure_storage.store_session_key(
            session_id=key_id,
            session_key=test_key,
            rotation_interval_hours=0  # 立即需要轮换
        )
        
        # 获取初始密钥
        initial_key = secure_storage.retrieve_key(key_id)
        assert initial_key == test_key
        
        # 启动自动轮换
        secure_storage.start_automatic_rotation()
        
        # 等待轮换线程执行（轮换检查间隔为 1 小时，但我们设置了 0 小时轮换间隔）
        # 由于轮换间隔为 0，密钥应该在下次检查时被轮换
        # 注意：实际测试中，轮换线程每小时检查一次，所以这里只验证机制存在
        
        # 验证轮换线程已启动
        assert secure_storage._rotation_thread is not None
        assert secure_storage._rotation_thread.is_alive()
        
        # 停止自动轮换
        secure_storage.stop_automatic_rotation()
        
        # 验证轮换线程已停止
        assert not secure_storage._rotation_thread.is_alive()
        
        # 清理
        secure_storage.clear_all_keys()
    
    def test_key_rotation_preserves_key_id(self):
        """测试密钥轮换保持密钥 ID 不变
        
        验证需求: 19.5
        """
        # 创建安全存储实例
        secure_storage = SecureKeyStorage()
        
        # 生成测试密钥
        old_key = generate_sm4_key(16)
        new_key = generate_sm4_key(16)
        key_id = "test_key_rotation"
        
        # 存储初始密钥
        secure_storage.store_session_key(
            session_id=key_id,
            session_key=old_key,
            rotation_interval_hours=24
        )
        
        # 验证初始密钥
        stored_key = secure_storage.retrieve_key(key_id)
        assert stored_key == old_key
        
        # 获取初始元数据
        initial_metadata = secure_storage.get_key_metadata(key_id)
        assert initial_metadata is not None
        
        # 等待一小段时间确保时间戳不同
        time.sleep(0.01)
        
        # 执行密钥轮换
        result = secure_storage.rotate_key(key_id, new_key)
        assert result is True
        
        # 验证密钥已更新
        rotated_key = secure_storage.retrieve_key(key_id)
        assert rotated_key == new_key
        assert rotated_key != old_key
        
        # 验证密钥 ID 保持不变
        metadata = secure_storage.get_key_metadata(key_id)
        assert metadata is not None
        assert metadata.key_id == key_id
        
        # 验证轮换时间已更新（应该晚于创建时间）
        assert metadata.last_rotated_at >= initial_metadata.created_at
        
        # 清理
        secure_storage.clear_all_keys()
    
    def test_multiple_session_keys_independent_storage(self):
        """测试多个会话密钥的独立存储
        
        验证需求: 19.3
        """
        # 清空安全存储
        secure_storage = get_secure_key_storage()
        secure_storage.clear_all_keys()
        
        # 创建多个会话
        sessions = []
        for i in range(5):
            vehicle_id = f"TEST_VEHICLE_{i:03d}"
            issued_at = datetime.utcnow()
            expires_at = issued_at + timedelta(hours=24)
            
            auth_token = AuthToken(
                vehicle_id=vehicle_id,
                issued_at=issued_at,
                expires_at=expires_at,
                permissions={"data_transfer", "heartbeat"},
                signature=b"0" * 64
            )
            
            session_info = establish_session(
                vehicle_id=vehicle_id,
                auth_token=auth_token,
                redis_conn=None,
                use_secure_storage=True
            )
            
            sessions.append(session_info)
        
        # 验证所有会话密钥都已独立存储
        for session in sessions:
            stored_key = secure_storage.retrieve_key(session.session_id)
            assert stored_key is not None
            assert stored_key == session.sm4_session_key
        
        # 验证所有会话密钥互不相同
        keys = [secure_storage.retrieve_key(s.session_id) for s in sessions]
        assert len(set(keys)) == len(keys)  # 所有密钥唯一
        
        # 清理所有会话
        for session in sessions:
            close_session(session.session_id, use_secure_storage=True)
        
        # 验证所有密钥已清除
        for session in sessions:
            cleared_key = secure_storage.retrieve_key(session.session_id)
            assert cleared_key is None
        
        secure_storage.clear_all_keys()
    
    def test_key_never_transmitted_in_plaintext(self):
        """测试密钥永不以明文形式传输或记录
        
        验证需求: 19.6
        """
        # 这是一个概念性测试，验证密钥不会被记录到日志
        # 实际实现中，应该确保：
        # 1. 密钥不会被打印到控制台
        # 2. 密钥不会被记录到日志文件
        # 3. 密钥不会在异常消息中暴露
        
        secure_storage = SecureKeyStorage()
        
        # 生成测试密钥
        test_key = generate_sm4_key(16)
        key_id = "test_no_plaintext"
        
        # 存储密钥
        secure_storage.store_session_key(
            session_id=key_id,
            session_key=test_key,
            rotation_interval_hours=24
        )
        
        # 获取密钥元数据（不包含密钥本身）
        metadata = secure_storage.get_key_metadata(key_id)
        
        # 验证元数据不包含密钥
        assert metadata is not None
        assert not hasattr(metadata, 'key_data')
        assert not hasattr(metadata, 'session_key')
        
        # 验证 __str__ 和 __repr__ 不暴露密钥
        metadata_str = str(metadata)
        assert test_key.hex() not in metadata_str
        
        # 清理
        secure_storage.clear_all_keys()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
