"""安全报文传输模块

提供安全数据传输和报文验证功能。
"""

import os
from datetime import datetime
from typing import Union
from src.models.message import SecureMessage, MessageHeader
from src.models.enums import MessageType
from src.crypto.sm4 import sm4_encrypt, sm4_decrypt
from src.crypto.sm2 import sm2_sign, sm2_verify
from src.db.redis_client import RedisConnection
from config.database import RedisConfig


def secure_data_transmission(
    plain_data: Union[bytes, str],
    session_key: bytes,
    sender_private_key: bytes,
    receiver_public_key: bytes,
    sender_id: str,
    receiver_id: str,
    session_id: str,
    message_type: MessageType = MessageType.DATA_TRANSFER
) -> SecureMessage:
    """安全数据传输
    
    实现 Algorithm 2 (secureDataTransmission) 的完整流程：
    1. 生成 16 字节随机 nonce
    2. 添加当前时间戳
    3. 使用 SM4 加密业务数据
    4. 创建 MessageHeader
    5. 使用 SM2 签名完整消息
    6. 返回 SecureMessage 对象
    
    前置条件:
    - plain_data 非空且长度大于 0
    - session_key 长度为 16 字节（SM4-128）或 32 字节（SM4-256）
    - sender_private_key 必须有效且与发送方证书匹配（32 字节）
    - receiver_public_key 必须有效（64 字节）
    
    后置条件:
    - 返回的 secureMessage 包含加密的 payload
    - signature 可通过发送方公钥验证
    - nonce 长度为 16 字节且唯一
    - timestamp 在合理时间范围内
    - 原始 plain_data 未被修改
    
    参数:
        plain_data: 明文业务数据（bytes 或 str）
        session_key: SM4 会话密钥（16 或 32 字节）
        sender_private_key: 发送方 SM2 私钥（32 字节）
        receiver_public_key: 接收方 SM2 公钥（64 字节）
        sender_id: 发送方标识
        receiver_id: 接收方标识
        session_id: 会话标识
        message_type: 消息类型，默认为 DATA
        
    返回:
        SecureMessage: 安全报文对象
        
    异常:
        ValueError: 如果输入参数无效
        RuntimeError: 如果加密或签名失败
        
    验证需求: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
    """
    # 前置条件验证
    if not plain_data:
        raise ValueError("明文数据不能为空")
    
    if len(session_key) not in (16, 32):
        raise ValueError(f"会话密钥长度必须为 16 或 32 字节，当前为 {len(session_key)}")
    
    if len(sender_private_key) != 32:
        raise ValueError(f"发送方私钥长度必须为 32 字节，当前为 {len(sender_private_key)}")
    
    if len(receiver_public_key) != 64:
        raise ValueError(f"接收方公钥长度必须为 64 字节，当前为 {len(receiver_public_key)}")
    
    if not sender_id or not isinstance(sender_id, str):
        raise ValueError("发送方标识必须为非空字符串")
    
    if not receiver_id or not isinstance(receiver_id, str):
        raise ValueError("接收方标识必须为非空字符串")
    
    if not session_id or not isinstance(session_id, str):
        raise ValueError("会话标识必须为非空字符串")
    
    try:
        # 步骤 1：生成消息头
        header = MessageHeader(
            version=1,
            message_type=message_type,
            sender_id=sender_id,
            receiver_id=receiver_id,
            session_id=session_id
        )
        
        # 步骤 2：生成随机数（防重放攻击）和时间戳
        nonce = os.urandom(16)  # 生成 16 字节唯一 nonce
        timestamp = datetime.now()
        
        # 步骤 3：使用 SM4 加密业务数据
        encrypted_payload = sm4_encrypt(plain_data, session_key)
        
        # 步骤 4：构造待签名数据
        # 将消息头序列化为字节
        header_bytes = str(header.to_dict()).encode('utf-8')
        timestamp_bytes = timestamp.isoformat().encode('utf-8')
        
        # 拼接所有数据：header + encrypted_payload + timestamp + nonce
        data_to_sign = header_bytes + encrypted_payload + timestamp_bytes + nonce
        
        # 步骤 5：使用 SM2 签名
        signature = sm2_sign(data_to_sign, sender_private_key)
        
        # 步骤 6：构造安全报文
        secure_message = SecureMessage(
            header=header,
            encrypted_payload=encrypted_payload,
            signature=signature,
            timestamp=timestamp,
            nonce=nonce
        )
        
        # 后置条件验证
        assert secure_message.encrypted_payload is not None and len(secure_message.encrypted_payload) > 0, \
            "加密载荷不能为空"
        assert secure_message.signature is not None and len(secure_message.signature) == 64, \
            f"签名长度必须为 64 字节，当前为 {len(secure_message.signature)}"
        assert len(secure_message.nonce) == 16, \
            f"Nonce 长度必须为 16 字节，当前为 {len(secure_message.nonce)}"
        
        return secure_message
        
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"安全数据传输失败: {str(e)}")


def verify_and_decrypt_message(
    secure_message: SecureMessage,
    session_key: bytes,
    sender_public_key: bytes,
    redis_config: RedisConfig = None
) -> bytes:
    """验证并解密安全报文
    
    实现 Algorithm 3 (verifyAndDecryptMessage) 的完整流程：
    1. 验证时间戳（防重放攻击）
    2. 检查 nonce 是否已使用（防重放攻击）
    3. 验证 nonce 长度
    4. 重构待签名数据
    5. 使用发送方公钥验证签名
    6. 使用会话密钥解密数据
    7. 标记 nonce 已使用
    
    前置条件:
    - secure_message 必须是有效的 SecureMessage 对象
    - session_key 长度为 16 或 32 字节
    - sender_public_key 必须有效（64 字节）
    
    后置条件:
    - 如果验证成功，返回解密后的明文数据
    - 如果验证失败，抛出异常
    - secure_message 参数未被修改
    - 使用过的 nonce 被标记在 Redis 中
    
    参数:
        secure_message: 安全报文对象
        session_key: SM4 会话密钥（16 或 32 字节）
        sender_public_key: 发送方 SM2 公钥（64 字节）
        redis_config: Redis 配置（可选，默认从环境变量加载）
        
    返回:
        bytes: 解密后的明文数据
        
    异常:
        ValueError: 如果输入参数无效或验证失败
        RuntimeError: 如果解密失败
        
    验证需求: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    # 前置条件验证
    if not isinstance(secure_message, SecureMessage):
        raise ValueError("secure_message 必须是 SecureMessage 对象")
    
    if len(session_key) not in (16, 32):
        raise ValueError(f"会话密钥长度必须为 16 或 32 字节，当前为 {len(session_key)}")
    
    if len(sender_public_key) != 64:
        raise ValueError(f"发送方公钥长度必须为 64 字节，当前为 {len(sender_public_key)}")
    
    # 加载 Redis 配置
    if redis_config is None:
        redis_config = RedisConfig.from_env()
    
    try:
        # 步骤 1：验证安全报文基本字段
        secure_message.validate()
        
        # 步骤 2：检查 nonce 是否已使用（防重放攻击）
        # 验证需求: 9.3, 9.4
        nonce_key = f"nonce:{secure_message.nonce.hex()}"
        redis_conn = RedisConnection(redis_config)
        
        if redis_conn.exists(nonce_key):
            raise ValueError("Nonce 已使用：检测到重放攻击")
        
        # 步骤 3：重构待签名数据（必须与发送时的顺序一致）
        header_bytes = str(secure_message.header.to_dict()).encode('utf-8')
        timestamp_bytes = secure_message.timestamp.isoformat().encode('utf-8')
        
        data_to_verify = (
            header_bytes + 
            secure_message.encrypted_payload + 
            timestamp_bytes + 
            secure_message.nonce
        )
        
        # 步骤 4：验证签名
        signature_valid = sm2_verify(
            data_to_verify,
            secure_message.signature,
            sender_public_key
        )
        
        if not signature_valid:
            raise ValueError("签名验证失败：消息可能被篡改")
        
        # 步骤 5：解密数据
        plain_data = sm4_decrypt(secure_message.encrypted_payload, session_key)
        
        # 步骤 6：标记 nonce 已使用
        # 验证需求: 9.5
        # TTL 设置为 10 分钟（600 秒），覆盖 ±5 分钟的时间戳容差
        redis_conn.set(nonce_key, b"used", ex=600)
        redis_conn.close()
        
        return plain_data
        
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"报文验证与解密失败: {str(e)}")
