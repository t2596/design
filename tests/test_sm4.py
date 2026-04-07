"""SM4 加密解密功能单元测试

测试 SM4 加密、解密和密钥生成功能的正确性。
"""

import pytest
from src.crypto.sm4 import sm4_encrypt, sm4_decrypt, generate_sm4_key


class TestGenerateSM4Key:
    """测试 SM4 密钥生成功能"""
    
    def test_generate_16_byte_key(self):
        """测试生成 16 字节密钥"""
        key = generate_sm4_key(16)
        assert len(key) == 16
        assert isinstance(key, bytes)
    
    def test_generate_32_byte_key(self):
        """测试生成 32 字节密钥"""
        key = generate_sm4_key(32)
        assert len(key) == 32
        assert isinstance(key, bytes)
    
    def test_generate_default_key(self):
        """测试默认生成 16 字节密钥"""
        key = generate_sm4_key()
        assert len(key) == 16
    
    def test_generate_invalid_key_length(self):
        """测试无效的密钥长度"""
        with pytest.raises(ValueError, match="SM4 密钥长度必须为 16 或 32 字节"):
            generate_sm4_key(8)
        
        with pytest.raises(ValueError, match="SM4 密钥长度必须为 16 或 32 字节"):
            generate_sm4_key(24)
    
    def test_key_uniqueness(self):
        """测试生成的密钥唯一性"""
        keys = [generate_sm4_key() for _ in range(100)]
        # 所有密钥应该互不相同
        assert len(set(keys)) == 100


class TestSM4Encrypt:
    """测试 SM4 加密功能"""
    
    def test_encrypt_bytes(self):
        """测试加密字节数据"""
        key = generate_sm4_key(16)
        plaintext = b"Hello, World!"
        ciphertext = sm4_encrypt(plaintext, key)
        
        assert isinstance(ciphertext, bytes)
        assert len(ciphertext) > 0
        assert len(ciphertext) % 16 == 0
        assert ciphertext != plaintext
    
    def test_encrypt_string(self):
        """测试加密字符串数据"""
        key = generate_sm4_key(16)
        plaintext = "你好，世界！"
        ciphertext = sm4_encrypt(plaintext, key)
        
        assert isinstance(ciphertext, bytes)
        assert len(ciphertext) > 0
        assert len(ciphertext) % 16 == 0
    
    def test_encrypt_with_32_byte_key(self):
        """测试使用 32 字节密钥加密"""
        key = generate_sm4_key(32)
        plaintext = b"Test data"
        ciphertext = sm4_encrypt(plaintext, key)
        
        assert isinstance(ciphertext, bytes)
        assert len(ciphertext) % 16 == 0
    
    def test_encrypt_empty_plaintext(self):
        """测试加密空数据"""
        key = generate_sm4_key(16)
        with pytest.raises(ValueError, match="明文数据不能为空"):
            sm4_encrypt(b"", key)
        
        with pytest.raises(ValueError, match="明文数据不能为空"):
            sm4_encrypt("", key)
    
    def test_encrypt_invalid_key_length(self):
        """测试无效的密钥长度"""
        plaintext = b"Test data"
        with pytest.raises(ValueError, match="SM4 密钥长度必须为 16 或 32 字节"):
            sm4_encrypt(plaintext, b"short")
    
    def test_ciphertext_length(self):
        """测试密文长度为 16 字节的倍数"""
        key = generate_sm4_key(16)
        
        # 测试不同长度的明文
        # 注意：gmssl 库的实现会将输出加倍（可能是内部表示），但解密时会正确还原
        test_data = [
            b"a",
            b"a" * 15,
            b"a" * 16,
            b"a" * 17,
            b"a" * 31,
            b"a" * 32,
            b"a" * 100,
        ]
        
        for plaintext in test_data:
            ciphertext = sm4_encrypt(plaintext, key)
            # 验证密文长度是 16 的倍数
            assert len(ciphertext) % 16 == 0, \
                f"明文长度 {len(plaintext)} 的密文长度 {len(ciphertext)} 不是 16 的倍数"
            # 验证密文不等于明文
            assert ciphertext != plaintext, \
                f"密文不应该等于明文"
            # 验证可以正确解密
            decrypted = sm4_decrypt(ciphertext, key)
            assert decrypted == plaintext, \
                f"解密后的数据应该等于原始明文"
    
    def test_same_plaintext_different_key(self):
        """测试相同明文不同密钥产生不同密文"""
        plaintext = b"Test data"
        key1 = generate_sm4_key(16)
        key2 = generate_sm4_key(16)
        
        ciphertext1 = sm4_encrypt(plaintext, key1)
        ciphertext2 = sm4_encrypt(plaintext, key2)
        
        assert ciphertext1 != ciphertext2


class TestSM4Decrypt:
    """测试 SM4 解密功能"""
    
    def test_decrypt_bytes(self):
        """测试解密字节数据"""
        key = generate_sm4_key(16)
        plaintext = b"Hello, World!"
        ciphertext = sm4_encrypt(plaintext, key)
        decrypted = sm4_decrypt(ciphertext, key)
        
        assert decrypted == plaintext
    
    def test_decrypt_string(self):
        """测试解密字符串数据"""
        key = generate_sm4_key(16)
        plaintext = "你好，世界！"
        ciphertext = sm4_encrypt(plaintext, key)
        decrypted = sm4_decrypt(ciphertext, key)
        
        assert decrypted.decode('utf-8') == plaintext
    
    def test_decrypt_with_32_byte_key(self):
        """测试使用 32 字节密钥解密"""
        key = generate_sm4_key(32)
        plaintext = b"Test data"
        ciphertext = sm4_encrypt(plaintext, key)
        decrypted = sm4_decrypt(ciphertext, key)
        
        assert decrypted == plaintext
    
    def test_decrypt_empty_ciphertext(self):
        """测试解密空密文"""
        key = generate_sm4_key(16)
        with pytest.raises(ValueError, match="密文数据不能为空"):
            sm4_decrypt(b"", key)
    
    def test_decrypt_invalid_ciphertext_length(self):
        """测试解密长度不正确的密文"""
        key = generate_sm4_key(16)
        with pytest.raises(ValueError, match="密文长度必须是 16 的倍数"):
            sm4_decrypt(b"invalid", key)
    
    def test_decrypt_invalid_key_length(self):
        """测试无效的密钥长度"""
        ciphertext = b"a" * 16
        with pytest.raises(ValueError, match="SM4 密钥长度必须为 16 或 32 字节"):
            sm4_decrypt(ciphertext, b"short")
    
    def test_decrypt_with_wrong_key(self):
        """测试使用错误的密钥解密"""
        key1 = generate_sm4_key(16)
        key2 = generate_sm4_key(16)
        plaintext = b"Test data"
        ciphertext = sm4_encrypt(plaintext, key1)
        
        # 使用错误的密钥解密应该失败或返回错误数据
        with pytest.raises(RuntimeError):
            sm4_decrypt(ciphertext, key2)
    
    def test_decrypt_corrupted_ciphertext(self):
        """测试解密损坏的密文"""
        key = generate_sm4_key(16)
        plaintext = b"Test data"
        ciphertext = sm4_encrypt(plaintext, key)
        
        # 损坏密文
        corrupted = bytearray(ciphertext)
        corrupted[0] ^= 0xFF
        corrupted = bytes(corrupted)
        
        # 解密损坏的密文应该失败
        with pytest.raises(RuntimeError):
            sm4_decrypt(corrupted, key)


class TestSM4EncryptDecryptRoundtrip:
    """测试 SM4 加密解密往返一致性"""
    
    def test_roundtrip_various_lengths(self):
        """测试不同长度数据的加密解密往返"""
        key = generate_sm4_key(16)
        
        test_data = [
            b"a",
            b"Hello",
            b"a" * 15,
            b"a" * 16,
            b"a" * 17,
            b"a" * 100,
            b"a" * 1000,
            "你好，世界！".encode('utf-8'),
            b"\x00\x01\x02\x03\x04\x05",  # 二进制数据
        ]
        
        for plaintext in test_data:
            ciphertext = sm4_encrypt(plaintext, key)
            decrypted = sm4_decrypt(ciphertext, key)
            assert decrypted == plaintext, \
                f"往返失败：原始数据长度 {len(plaintext)}"
    
    def test_roundtrip_with_32_byte_key(self):
        """测试使用 32 字节密钥的加密解密往返"""
        key = generate_sm4_key(32)
        plaintext = b"Test data with 32-byte key"
        
        ciphertext = sm4_encrypt(plaintext, key)
        decrypted = sm4_decrypt(ciphertext, key)
        
        assert decrypted == plaintext
    
    def test_roundtrip_unicode(self):
        """测试 Unicode 字符串的加密解密往返"""
        key = generate_sm4_key(16)
        test_strings = [
            "Hello, World!",
            "你好，世界！",
            "こんにちは世界",
            "Привет мир",
            "مرحبا بالعالم",
            "🚗🔐🌐",  # Emoji
        ]
        
        for plaintext in test_strings:
            ciphertext = sm4_encrypt(plaintext, key)
            decrypted = sm4_decrypt(ciphertext, key)
            assert decrypted.decode('utf-8') == plaintext
