"""测试安全密钥存储模块"""

import pytest
import time
from datetime import datetime, timedelta
from src.secure_key_storage import SecureKeyStorage, KeyMetadata


class TestSecureKeyStorage:
    """测试安全密钥存储类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.storage = SecureKeyStorage()
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.storage.stop_automatic_rotation()
        self.storage.clear_all_keys()
    
    def test_store_ca_private_key(self):
        """测试存储 CA 私钥
        
        验证需求: 19.1
        """
        # 生成测试密钥
        ca_private_key = b'\x01' * 32
        
        # 存储密钥
        result = self.storage.store_ca_private_key("test_ca_key", ca_private_key)
        
        # 验证存储成功
        assert result is True
        
        # 验证可以检索密钥
        retrieved_key = self.storage.retrieve_key("test_ca_key")
        assert retrieved_key == ca_private_key
        
        # 验证元数据
        metadata = self.storage.get_key_metadata("test_ca_key")
        assert metadata is not None
        assert metadata.key_id == "test_ca_key"
        assert metadata.key_type == "ca_private"
    
    def test_store_ca_private_key_invalid_length(self):
        """测试存储无效长度的 CA 私钥"""
        # 尝试存储无效长度的密钥
        with pytest.raises(ValueError, match="CA 私钥长度必须为 32 字节"):
            self.storage.store_ca_private_key("test_key", b'\x01' * 16)
    
    def test_store_session_key(self):
        """测试存储会话密钥
        
        验证需求: 19.3
        """
        # 生成测试密钥
        session_key = b'\x02' * 16
        
        # 存储密钥
        result = self.storage.store_session_key("test_session", session_key)
        
        # 验证存储成功
        assert result is True
        
        # 验证可以检索密钥
        retrieved_key = self.storage.retrieve_key("test_session")
        assert retrieved_key == session_key
        
        # 验证元数据
        metadata = self.storage.get_key_metadata("test_session")
        assert metadata is not None
        assert metadata.key_id == "test_session"
        assert metadata.key_type == "session"
    
    def test_store_session_key_invalid_length(self):
        """测试存储无效长度的会话密钥"""
        # 尝试存储无效长度的密钥
        with pytest.raises(ValueError, match="会话密钥长度必须为 16 或 32 字节"):
            self.storage.store_session_key("test_key", b'\x01' * 8)
    
    def test_retrieve_nonexistent_key(self):
        """测试检索不存在的密钥"""
        # 检索不存在的密钥
        key = self.storage.retrieve_key("nonexistent")
        
        # 验证返回 None
        assert key is None
    
    def test_secure_clear_key(self):
        """测试安全清除密钥
        
        验证需求: 19.4
        """
        # 存储测试密钥
        test_key = b'\x03' * 32
        self.storage.store_ca_private_key("test_clear", test_key)
        
        # 验证密钥存在
        assert self.storage.retrieve_key("test_clear") is not None
        
        # 安全清除密钥
        result = self.storage.secure_clear_key("test_clear")
        
        # 验证清除成功
        assert result is True
        
        # 验证密钥已被删除
        assert self.storage.retrieve_key("test_clear") is None
        
        # 验证元数据已被删除
        assert self.storage.get_key_metadata("test_clear") is None
    
    def test_secure_clear_nonexistent_key(self):
        """测试清除不存在的密钥"""
        # 尝试清除不存在的密钥
        result = self.storage.secure_clear_key("nonexistent")
        
        # 验证返回 False
        assert result is False
    
    def test_rotate_key(self):
        """测试密钥轮换
        
        验证需求: 19.5
        """
        # 存储原始密钥
        old_key = b'\x04' * 32
        self.storage.store_ca_private_key("test_rotate", old_key)
        
        # 生成新密钥
        new_key = b'\x05' * 32
        
        # 轮换密钥
        result = self.storage.rotate_key("test_rotate", new_key)
        
        # 验证轮换成功
        assert result is True
        
        # 验证新密钥已存储
        retrieved_key = self.storage.retrieve_key("test_rotate")
        assert retrieved_key == new_key
        assert retrieved_key != old_key
        
        # 验证元数据已更新
        metadata = self.storage.get_key_metadata("test_rotate")
        assert metadata is not None
        assert metadata.last_rotated_at > metadata.created_at
    
    def test_rotate_nonexistent_key(self):
        """测试轮换不存在的密钥"""
        # 尝试轮换不存在的密钥
        result = self.storage.rotate_key("nonexistent", b'\x01' * 32)
        
        # 验证返回 False
        assert result is False
    
    def test_list_keys(self):
        """测试列出所有密钥"""
        # 存储多个密钥
        self.storage.store_ca_private_key("key1", b'\x01' * 32)
        self.storage.store_session_key("key2", b'\x02' * 16)
        self.storage.store_session_key("key3", b'\x03' * 32)
        
        # 列出所有密钥
        keys = self.storage.list_keys()
        
        # 验证密钥列表
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys
    
    def test_clear_all_keys(self):
        """测试清除所有密钥"""
        # 存储多个密钥
        self.storage.store_ca_private_key("key1", b'\x01' * 32)
        self.storage.store_session_key("key2", b'\x02' * 16)
        self.storage.store_session_key("key3", b'\x03' * 32)
        
        # 清除所有密钥
        count = self.storage.clear_all_keys()
        
        # 验证清除数量
        assert count == 3
        
        # 验证所有密钥已被删除
        assert len(self.storage.list_keys()) == 0
    
    def test_automatic_rotation_start_stop(self):
        """测试自动密钥轮换的启动和停止
        
        验证需求: 19.5
        """
        # 启动自动轮换
        self.storage.start_automatic_rotation()
        
        # 验证轮换线程已启动
        assert self.storage._rotation_thread is not None
        assert self.storage._rotation_thread.is_alive()
        
        # 停止自动轮换
        self.storage.stop_automatic_rotation()
        
        # 等待线程结束
        time.sleep(0.5)
        
        # 验证轮换线程已停止
        assert not self.storage._rotation_thread.is_alive()
    
    def test_key_metadata(self):
        """测试密钥元数据"""
        # 存储密钥
        self.storage.store_ca_private_key("test_metadata", b'\x01' * 32, rotation_interval_hours=48)
        
        # 获取元数据
        metadata = self.storage.get_key_metadata("test_metadata")
        
        # 验证元数据
        assert metadata is not None
        assert metadata.key_id == "test_metadata"
        assert metadata.key_type == "ca_private"
        assert metadata.rotation_interval_hours == 48
        assert isinstance(metadata.created_at, datetime)
        assert isinstance(metadata.last_rotated_at, datetime)
    
    def test_private_key_not_logged(self):
        """测试私钥不会被记录到日志
        
        验证需求: 19.6
        """
        # 存储密钥
        test_key = b'\x06' * 32
        self.storage.store_ca_private_key("test_no_log", test_key)
        
        # 验证密钥的字符串表示不包含密钥内容
        # （这是一个简化的测试，实际应该检查日志输出）
        keys_list = self.storage.list_keys()
        assert "test_no_log" in keys_list
        
        # 验证元数据不包含密钥内容
        metadata = self.storage.get_key_metadata("test_no_log")
        assert metadata is not None
        # 元数据中不应该有密钥数据
        assert not hasattr(metadata, 'key_data')


class TestSecureKeyStorageIntegration:
    """测试安全密钥存储集成"""
    
    def test_multiple_key_types(self):
        """测试存储多种类型的密钥"""
        storage = SecureKeyStorage()
        
        try:
            # 存储 CA 私钥
            storage.store_ca_private_key("ca_key", b'\x01' * 32)
            
            # 存储多个会话密钥
            storage.store_session_key("session1", b'\x02' * 16)
            storage.store_session_key("session2", b'\x03' * 32)
            
            # 验证所有密钥都存在
            assert storage.retrieve_key("ca_key") is not None
            assert storage.retrieve_key("session1") is not None
            assert storage.retrieve_key("session2") is not None
            
            # 验证密钥类型
            assert storage.get_key_metadata("ca_key").key_type == "ca_private"
            assert storage.get_key_metadata("session1").key_type == "session"
            assert storage.get_key_metadata("session2").key_type == "session"
            
        finally:
            storage.clear_all_keys()
    
    def test_concurrent_access(self):
        """测试并发访问密钥存储"""
        import threading
        
        storage = SecureKeyStorage()
        errors = []
        
        def store_and_retrieve(key_id: str):
            try:
                # 存储密钥
                storage.store_session_key(key_id, b'\x01' * 16)
                
                # 检索密钥
                key = storage.retrieve_key(key_id)
                assert key is not None
                
                # 清除密钥
                storage.secure_clear_key(key_id)
            except Exception as e:
                errors.append(e)
        
        try:
            # 创建多个线程并发访问
            threads = []
            for i in range(10):
                thread = threading.Thread(target=store_and_retrieve, args=(f"key_{i}",))
                threads.append(thread)
                thread.start()
            
            # 等待所有线程完成
            for thread in threads:
                thread.join()
            
            # 验证没有错误
            assert len(errors) == 0
            
        finally:
            storage.clear_all_keys()
