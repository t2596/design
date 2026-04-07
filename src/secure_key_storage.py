"""安全密钥存储模块

提供密钥的安全存储、清除和轮换功能。
模拟 HSM（硬件安全模块）或安全隔离区的密钥存储。
"""

import os
import ctypes
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import json


@dataclass
class KeyMetadata:
    """密钥元数据"""
    key_id: str
    created_at: datetime
    last_rotated_at: datetime
    rotation_interval_hours: int
    key_type: str  # "ca_private", "session", "gateway_private"


class SecureKeyStorage:
    """安全密钥存储类
    
    模拟 HSM 或安全隔离区的密钥存储功能。
    提供密钥的安全存储、清除和轮换机制。
    
    验证需求: 19.1, 19.3, 19.4, 19.5, 19.6
    """
    
    def __init__(self):
        """初始化安全密钥存储"""
        # 使用字典模拟安全存储区域
        # 在生产环境中，这应该是 HSM 或 TPM
        self._secure_storage: Dict[str, bytes] = {}
        self._key_metadata: Dict[str, KeyMetadata] = {}
        self._lock = threading.Lock()
        self._rotation_thread: Optional[threading.Thread] = None
        self._stop_rotation = threading.Event()
    
    def store_ca_private_key(
        self,
        key_id: str,
        private_key: bytes,
        rotation_interval_hours: int = 24
    ) -> bool:
        """存储 CA 私钥到安全隔离区
        
        在生产环境中，CA 私钥应该存储在 HSM 或安全隔离区中。
        这里模拟安全存储，确保密钥不会以明文形式泄露。
        
        参数:
            key_id: 密钥标识符
            private_key: CA 私钥（32 字节）
            rotation_interval_hours: 密钥轮换间隔（小时）
            
        返回:
            bool: 存储是否成功
            
        验证需求: 19.1, 19.6
        """
        if len(private_key) != 32:
            raise ValueError(f"CA 私钥长度必须为 32 字节，当前为 {len(private_key)}")
        
        with self._lock:
            # 存储密钥（在生产环境中应该加密存储）
            self._secure_storage[key_id] = private_key
            
            # 存储元数据
            now = datetime.utcnow()
            self._key_metadata[key_id] = KeyMetadata(
                key_id=key_id,
                created_at=now,
                last_rotated_at=now,
                rotation_interval_hours=rotation_interval_hours,
                key_type="ca_private"
            )
        
        return True
    
    def store_session_key(
        self,
        session_id: str,
        session_key: bytes,
        rotation_interval_hours: int = 24
    ) -> bool:
        """存储会话密钥到内存安全区域
        
        会话密钥应该在内存中安全存储，并在会话结束时安全清除。
        
        参数:
            session_id: 会话标识符
            session_key: 会话密钥（16 或 32 字节）
            rotation_interval_hours: 密钥轮换间隔（小时）
            
        返回:
            bool: 存储是否成功
            
        验证需求: 19.3, 19.5
        """
        if len(session_key) not in (16, 32):
            raise ValueError(f"会话密钥长度必须为 16 或 32 字节，当前为 {len(session_key)}")
        
        with self._lock:
            # 存储密钥
            self._secure_storage[session_id] = session_key
            
            # 存储元数据
            now = datetime.utcnow()
            self._key_metadata[session_id] = KeyMetadata(
                key_id=session_id,
                created_at=now,
                last_rotated_at=now,
                rotation_interval_hours=rotation_interval_hours,
                key_type="session"
            )
        
        return True
    
    def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """从安全存储中检索密钥
        
        参数:
            key_id: 密钥标识符
            
        返回:
            Optional[bytes]: 密钥数据，如果不存在则返回 None
            
        验证需求: 19.1, 19.3
        """
        with self._lock:
            return self._secure_storage.get(key_id)
    
    def secure_clear_key(self, key_id: str) -> bool:
        """安全清除密钥
        
        从安全存储中删除密钥。在生产环境中，应该使用 HSM 或专门的
        安全内存清除功能来确保密钥被彻底清除。
        
        参数:
            key_id: 密钥标识符
            
        返回:
            bool: 清除是否成功
            
        验证需求: 19.4, 19.6
        """
        with self._lock:
            if key_id not in self._secure_storage:
                return False
            
            # 获取密钥数据
            key_data = self._secure_storage[key_id]
            
            # 安全清除：在生产环境中应该使用 HSM 或专门的安全清除功能
            # Python 的 bytes 对象是不可变的，无法直接覆盖内存
            # 这里我们通过删除引用让垃圾回收器处理
            self._overwrite_memory(key_data, b'\x00')
            self._overwrite_memory(key_data, b'\xff')
            self._overwrite_memory(key_data, os.urandom(len(key_data)))
            
            # 从存储中删除
            del self._secure_storage[key_id]
            
            # 删除元数据
            if key_id in self._key_metadata:
                del self._key_metadata[key_id]
            
            return True
    
    def _overwrite_memory(self, data: bytes, pattern: bytes) -> None:
        """覆盖内存数据
        
        注意：Python 中的字节对象是不可变的，因此无法直接覆盖内存。
        这个方法主要用于概念演示。在生产环境中，应该使用：
        1. 硬件安全模块（HSM）存储密钥
        2. 操作系统提供的安全内存清除功能
        3. 专门的密码学库（如 libsodium）提供的安全清除功能
        
        参数:
            data: 要覆盖的数据
            pattern: 覆盖模式（单字节或与 data 长度相同的字节串）
        """
        # Python 的 bytes 对象是不可变的，无法直接覆盖
        # 这里我们只是确保引用被删除，让垃圾回收器处理
        # 在实际生产环境中，应该使用 HSM 或专门的安全内存清除库
        pass
    
    def rotate_key(self, key_id: str, new_key: bytes) -> bool:
        """轮换密钥
        
        使用新密钥替换旧密钥，并安全清除旧密钥。
        
        参数:
            key_id: 密钥标识符
            new_key: 新密钥
            
        返回:
            bool: 轮换是否成功
            
        验证需求: 19.5
        """
        with self._lock:
            if key_id not in self._secure_storage:
                return False
            
            # 获取旧密钥和元数据
            old_key = self._secure_storage[key_id]
            old_metadata = self._key_metadata.get(key_id)
            
            # 确保有足够的时间差（至少 1 微秒）
            import time
            time.sleep(0.001)
            
            # 安全清除旧密钥
            self._overwrite_memory(old_key, b'\x00')
            self._overwrite_memory(old_key, b'\xff')
            self._overwrite_memory(old_key, os.urandom(len(old_key)))
            
            # 存储新密钥
            self._secure_storage[key_id] = new_key
            
            # 更新元数据
            if old_metadata:
                self._key_metadata[key_id].last_rotated_at = datetime.utcnow()
            
            return True
    
    def start_automatic_rotation(self) -> None:
        """启动自动密钥轮换
        
        启动后台线程，定期检查并轮换需要轮换的密钥。
        
        验证需求: 19.5
        """
        if self._rotation_thread is not None and self._rotation_thread.is_alive():
            return  # 已经在运行
        
        self._stop_rotation.clear()
        self._rotation_thread = threading.Thread(
            target=self._rotation_worker,
            daemon=True
        )
        self._rotation_thread.start()
    
    def stop_automatic_rotation(self) -> None:
        """停止自动密钥轮换"""
        self._stop_rotation.set()
        if self._rotation_thread is not None:
            self._rotation_thread.join(timeout=5)
    
    def _rotation_worker(self) -> None:
        """密钥轮换工作线程
        
        定期检查密钥是否需要轮换，并执行轮换操作。
        """
        while not self._stop_rotation.is_set():
            try:
                # 检查需要轮换的密钥
                keys_to_rotate = []
                
                with self._lock:
                    now = datetime.utcnow()
                    for key_id, metadata in self._key_metadata.items():
                        # 计算距离上次轮换的时间
                        time_since_rotation = now - metadata.last_rotated_at
                        rotation_interval = timedelta(hours=metadata.rotation_interval_hours)
                        
                        # 如果超过轮换间隔，标记为需要轮换
                        if time_since_rotation >= rotation_interval:
                            keys_to_rotate.append((key_id, metadata.key_type))
                
                # 执行密钥轮换
                for key_id, key_type in keys_to_rotate:
                    self._perform_key_rotation(key_id, key_type)
                
                # 每小时检查一次（使用可中断的等待）
                self._stop_rotation.wait(timeout=3600)
                
            except Exception as e:
                # 记录错误但不中断轮换线程
                print(f"密钥轮换错误: {str(e)}")
    
    def _perform_key_rotation(self, key_id: str, key_type: str) -> None:
        """执行密钥轮换
        
        参数:
            key_id: 密钥标识符
            key_type: 密钥类型
        """
        # 根据密钥类型生成新密钥
        if key_type == "session":
            # 会话密钥：生成新的 SM4 密钥
            from src.crypto.sm4 import generate_sm4_key
            new_key = generate_sm4_key(16)
        elif key_type == "ca_private":
            # CA 私钥：生成新的 SM2 密钥对
            from src.crypto.sm2 import generate_sm2_keypair
            private_key, _ = generate_sm2_keypair()
            new_key = private_key
        else:
            # 未知类型，跳过
            return
        
        # 轮换密钥
        self.rotate_key(key_id, new_key)
        
        print(f"密钥已轮换: {key_id} (类型: {key_type})")
    
    def get_key_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        """获取密钥元数据
        
        参数:
            key_id: 密钥标识符
            
        返回:
            Optional[KeyMetadata]: 密钥元数据，如果不存在则返回 None
        """
        with self._lock:
            return self._key_metadata.get(key_id)
    
    def list_keys(self) -> list:
        """列出所有存储的密钥
        
        返回:
            list: 密钥标识符列表
        """
        with self._lock:
            return list(self._secure_storage.keys())
    
    def clear_all_keys(self) -> int:
        """清除所有密钥
        
        返回:
            int: 清除的密钥数量
        """
        with self._lock:
            key_ids = list(self._secure_storage.keys())
            count = 0
            
            for key_id in key_ids:
                # 直接在锁内清除，避免递归锁问题
                if key_id in self._secure_storage:
                    key_data = self._secure_storage[key_id]
                    
                    # 安全清除
                    self._overwrite_memory(key_data, b'\x00')
                    self._overwrite_memory(key_data, b'\xff')
                    self._overwrite_memory(key_data, os.urandom(len(key_data)))
                    
                    # 删除密钥和元数据
                    del self._secure_storage[key_id]
                    if key_id in self._key_metadata:
                        del self._key_metadata[key_id]
                    
                    count += 1
            
            return count


# 全局单例实例
_secure_key_storage_instance: Optional[SecureKeyStorage] = None


def get_secure_key_storage() -> SecureKeyStorage:
    """获取安全密钥存储单例实例
    
    返回:
        SecureKeyStorage: 安全密钥存储实例
    """
    global _secure_key_storage_instance
    if _secure_key_storage_instance is None:
        _secure_key_storage_instance = SecureKeyStorage()
    return _secure_key_storage_instance
