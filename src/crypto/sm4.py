"""SM4 对称加密模块

提供 SM4 加密、解密和密钥生成功能，符合 GM/T 0002-2012 标准。
"""

import os
from typing import Union
from gmssl import sm4


def generate_sm4_key(key_length: int = 16) -> bytes:
    """生成 SM4 密钥
    
    使用密码学安全随机数生成器（CSRNG）生成 SM4 密钥。
    
    前置条件:
    - key_length 必须为 16 或 32
    - 系统必须有可用的密码学安全随机数生成器
    
    后置条件:
    - 返回的密钥长度为 16 字节（128 位）或 32 字节（256 位）
    - 密钥具有足够的熵（至少 128 位安全强度）
    - 每次调用生成的密钥都是唯一的（概率上）
    
    参数:
        key_length: 密钥长度，16 字节（128 位）或 32 字节（256 位），默认 16
        
    返回:
        bytes: SM4 密钥
        
    异常:
        ValueError: 如果 key_length 不是 16 或 32
        
    验证需求: 10.1, 10.2
    """
    if key_length not in (16, 32):
        raise ValueError(f"SM4 密钥长度必须为 16 或 32 字节，当前为 {key_length}")
    
    # 使用 os.urandom 生成密码学安全的随机密钥
    # os.urandom 在所有平台上都使用 CSRNG
    key = os.urandom(key_length)
    
    # 后置条件验证
    assert len(key) == key_length, f"生成的密钥长度不正确: {len(key)} != {key_length}"
    
    return key


def sm4_encrypt(plaintext: Union[bytes, str], key: bytes) -> bytes:
    """使用 SM4 算法加密数据
    
    使用 SM4 分组密码算法（ECB 模式）加密明文数据。
    
    前置条件:
    - plaintext 非空且长度大于 0
    - key 长度为 16 字节（128位）或 32 字节（256位）
    - key 必须是通过安全随机数生成器生成的
    
    后置条件:
    - 返回的 ciphertext 非空
    - ciphertext 长度为 plaintext 长度向上取整到 16 字节的倍数
    - 使用相同的 key 调用 sm4_decrypt(ciphertext, key) 可恢复原始 plaintext
    - plaintext 参数未被修改
    
    参数:
        plaintext: 明文数据（bytes 或 str）
        key: SM4 密钥（16 或 32 字节）
        
    返回:
        bytes: 加密后的密文数据
        
    异常:
        ValueError: 如果 plaintext 为空或 key 长度不正确
        
    验证需求: 6.1, 6.2, 6.3
    """
    # 前置条件验证
    if not plaintext:
        raise ValueError("明文数据不能为空")
    
    if len(key) not in (16, 32):
        raise ValueError(f"SM4 密钥长度必须为 16 或 32 字节，当前为 {len(key)}")
    
    # 如果是字符串，转换为字节
    if isinstance(plaintext, str):
        plaintext_bytes = plaintext.encode('utf-8')
    else:
        plaintext_bytes = plaintext
    
    # 对于 32 字节密钥，只使用前 16 字节（SM4 标准密钥长度为 128 位）
    sm4_key = key[:16]
    
    # 创建 SM4 加密器（ECB 模式）
    cipher = sm4.CryptSM4()
    cipher.set_key(sm4_key, sm4.SM4_ENCRYPT)
    
    # PKCS#7 填充到 16 字节的倍数
    padding_length = 16 - (len(plaintext_bytes) % 16)
    padded_plaintext = plaintext_bytes + bytes([padding_length] * padding_length)
    
    # 加密数据
    ciphertext = cipher.crypt_ecb(padded_plaintext)
    
    # 后置条件验证
    assert ciphertext is not None and len(ciphertext) > 0, "加密失败：密文为空"
    assert len(ciphertext) % 16 == 0, f"密文长度不是 16 的倍数: {len(ciphertext)}"
    
    return ciphertext


def sm4_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """使用 SM4 算法解密数据
    
    使用 SM4 分组密码算法（ECB 模式）解密密文数据。
    
    前置条件:
    - ciphertext 非空且长度为 16 字节的倍数
    - key 长度为 16 字节（128位）或 32 字节（256位）
    - key 必须与加密时使用的密钥相同
    - ciphertext 必须是通过 sm4_encrypt 生成的有效密文
    
    后置条件:
    - 如果 key 正确，返回原始明文数据
    - 如果 key 错误，返回无效数据或抛出异常
    - ciphertext 参数未被修改
    - 解密操作是加密操作的逆运算
    
    参数:
        ciphertext: 密文数据
        key: SM4 密钥（16 或 32 字节）
        
    返回:
        bytes: 解密后的明文数据
        
    异常:
        ValueError: 如果 ciphertext 为空、长度不正确或 key 长度不正确
        RuntimeError: 如果解密失败
        
    验证需求: 6.4, 6.5
    """
    # 前置条件验证
    if not ciphertext:
        raise ValueError("密文数据不能为空")
    
    if len(ciphertext) % 16 != 0:
        raise ValueError(f"密文长度必须是 16 的倍数，当前为 {len(ciphertext)}")
    
    if len(key) not in (16, 32):
        raise ValueError(f"SM4 密钥长度必须为 16 或 32 字节，当前为 {len(key)}")
    
    # 对于 32 字节密钥，只使用前 16 字节
    sm4_key = key[:16]
    
    try:
        # 创建 SM4 解密器（ECB 模式）
        cipher = sm4.CryptSM4()
        cipher.set_key(sm4_key, sm4.SM4_DECRYPT)
        
        # 解密数据
        padded_plaintext = cipher.crypt_ecb(ciphertext)
        
        if not padded_plaintext:
            raise RuntimeError("解密失败：返回空数据")
        
        # 移除 PKCS#7 填充
        padding_length = padded_plaintext[-1]
        
        # 验证填充的有效性
        if padding_length < 1 or padding_length > 16:
            raise RuntimeError(f"解密失败：无效的填充长度 {padding_length}")
        
        # 检查填充字节是否一致
        for i in range(padding_length):
            if padded_plaintext[-(i + 1)] != padding_length:
                raise RuntimeError("解密失败：填充验证失败")
        
        plaintext = padded_plaintext[:-padding_length]
        
        # 后置条件验证
        assert plaintext is not None, "解密失败：明文为空"
        
        return plaintext
        
    except Exception as e:
        # 将所有异常转换为 RuntimeError，避免泄露密钥信息
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        raise RuntimeError(f"解密失败: {str(e)}")
