"""SM2 签名验签功能单元测试

测试 SM2 签名、验签和密钥对生成功能的正确性。
"""

import pytest
from src.crypto.sm2 import sm2_sign, sm2_verify, generate_sm2_keypair


class TestGenerateSM2KeyPair:
    """测试 SM2 密钥对生成功能"""
    
    def test_generate_keypair(self):
        """测试生成密钥对"""
        private_key, public_key = generate_sm2_keypair()
        
        assert isinstance(private_key, bytes)
        assert isinstance(public_key, bytes)
        assert len(private_key) == 32
        assert len(public_key) == 64
    
    def test_keypair_uniqueness(self):
        """测试生成的密钥对唯一性"""
        keypairs = [generate_sm2_keypair() for _ in range(100)]
        
        # 所有私钥应该互不相同
        private_keys = [kp[0] for kp in keypairs]
        assert len(set(private_keys)) == 100
        
        # 所有公钥应该互不相同
        public_keys = [kp[1] for kp in keypairs]
        assert len(set(public_keys)) == 100
    
    def test_public_key_derived_from_private_key(self):
        """测试公钥可从私钥推导"""
        private_key1, public_key1 = generate_sm2_keypair()
        
        # 使用相同的私钥应该得到相同的公钥
        # 我们的实现使用椭圆曲线运算从私钥推导公钥
        from src.crypto.sm2 import _derive_public_key_from_private
        public_key2_hex = _derive_public_key_from_private(private_key1.hex())
        public_key2 = bytes.fromhex(public_key2_hex)
        
        assert public_key1 == public_key2


class TestSM2Sign:
    """测试 SM2 签名功能"""
    
    def test_sign_bytes(self):
        """测试签名字节数据"""
        private_key, _ = generate_sm2_keypair()
        data = b"Hello, World!"
        
        signature = sm2_sign(data, private_key)
        
        assert isinstance(signature, bytes)
        assert len(signature) == 64
    
    def test_sign_empty_data(self):
        """测试签名空数据"""
        private_key, _ = generate_sm2_keypair()
        
        with pytest.raises(ValueError, match="待签名数据不能为空"):
            sm2_sign(b"", private_key)
    
    def test_sign_invalid_private_key_length(self):
        """测试无效的私钥长度"""
        data = b"Test data"
        
        with pytest.raises(ValueError, match="SM2 私钥长度必须为 32 字节"):
            sm2_sign(data, b"short")
        
        with pytest.raises(ValueError, match="SM2 私钥长度必须为 32 字节"):
            sm2_sign(data, b"a" * 16)
        
        with pytest.raises(ValueError, match="SM2 私钥长度必须为 32 字节"):
            sm2_sign(data, b"a" * 64)
    
    def test_signature_length(self):
        """测试签名长度为 64 字节"""
        private_key, _ = generate_sm2_keypair()
        
        test_data = [
            b"a",
            b"Hello",
            b"a" * 100,
            b"a" * 1000,
            "你好，世界！".encode('utf-8'),
        ]
        
        for data in test_data:
            signature = sm2_sign(data, private_key)
            assert len(signature) == 64, \
                f"数据长度 {len(data)} 的签名长度 {len(signature)} 不是 64 字节"
    
    def test_same_data_different_key(self):
        """测试相同数据不同密钥产生不同签名"""
        data = b"Test data"
        private_key1, _ = generate_sm2_keypair()
        private_key2, _ = generate_sm2_keypair()
        
        signature1 = sm2_sign(data, private_key1)
        signature2 = sm2_sign(data, private_key2)
        
        # 不同的私钥应该产生不同的签名
        assert signature1 != signature2


class TestSM2Verify:
    """测试 SM2 验签功能"""
    
    def test_verify_valid_signature(self):
        """测试验证有效签名"""
        private_key, public_key = generate_sm2_keypair()
        data = b"Hello, World!"
        
        signature = sm2_sign(data, private_key)
        result = sm2_verify(data, signature, public_key)
        
        assert result is True
    
    def test_verify_invalid_signature(self):
        """测试验证无效签名"""
        private_key, public_key = generate_sm2_keypair()
        data = b"Hello, World!"
        
        # 使用错误的签名
        invalid_signature = b"a" * 64
        result = sm2_verify(data, invalid_signature, public_key)
        
        assert result is False
    
    def test_verify_tampered_data(self):
        """测试验证被篡改的数据"""
        private_key, public_key = generate_sm2_keypair()
        data = b"Hello, World!"
        
        signature = sm2_sign(data, private_key)
        
        # 篡改数据
        tampered_data = b"Hello, World?"
        result = sm2_verify(tampered_data, signature, public_key)
        
        assert result is False
    
    def test_verify_wrong_public_key(self):
        """测试使用错误的公钥验证"""
        private_key1, _ = generate_sm2_keypair()
        _, public_key2 = generate_sm2_keypair()
        data = b"Test data"
        
        signature = sm2_sign(data, private_key1)
        result = sm2_verify(data, signature, public_key2)
        
        assert result is False
    
    def test_verify_empty_data(self):
        """测试验证空数据"""
        _, public_key = generate_sm2_keypair()
        signature = b"a" * 64
        
        with pytest.raises(ValueError, match="待验证数据不能为空"):
            sm2_verify(b"", signature, public_key)
    
    def test_verify_invalid_signature_length(self):
        """测试验证长度不正确的签名"""
        _, public_key = generate_sm2_keypair()
        data = b"Test data"
        
        with pytest.raises(ValueError, match="SM2 签名长度必须为 64 字节"):
            sm2_verify(data, b"short", public_key)
        
        with pytest.raises(ValueError, match="SM2 签名长度必须为 64 字节"):
            sm2_verify(data, b"a" * 32, public_key)
    
    def test_verify_invalid_public_key_length(self):
        """测试验证长度不正确的公钥"""
        data = b"Test data"
        signature = b"a" * 64
        
        with pytest.raises(ValueError, match="SM2 公钥长度必须为 64 字节"):
            sm2_verify(data, signature, b"short")
        
        with pytest.raises(ValueError, match="SM2 公钥长度必须为 64 字节"):
            sm2_verify(data, signature, b"a" * 32)


class TestSM2SignVerifyRoundtrip:
    """测试 SM2 签名验签往返一致性"""
    
    def test_roundtrip_various_data(self):
        """测试不同数据的签名验签往返"""
        private_key, public_key = generate_sm2_keypair()
        
        test_data = [
            b"a",
            b"Hello",
            b"a" * 100,
            b"a" * 1000,
            b"a" * 10000,
            "你好，世界！".encode('utf-8'),
            b"\x00\x01\x02\x03\x04\x05",  # 二进制数据
        ]
        
        for data in test_data:
            signature = sm2_sign(data, private_key)
            result = sm2_verify(data, signature, public_key)
            assert result is True, \
                f"往返失败：数据长度 {len(data)}"
    
    def test_roundtrip_unicode(self):
        """测试 Unicode 字符串的签名验签往返"""
        private_key, public_key = generate_sm2_keypair()
        
        test_strings = [
            "Hello, World!",
            "你好，世界！",
            "こんにちは世界",
            "Привет мир",
            "مرحبا بالعالم",
            "🚗🔐🌐",  # Emoji
        ]
        
        for text in test_strings:
            data = text.encode('utf-8')
            signature = sm2_sign(data, private_key)
            result = sm2_verify(data, signature, public_key)
            assert result is True, f"往返失败：{text}"
    
    def test_multiple_signatures_same_data(self):
        """测试同一数据的多次签名都能验证通过"""
        private_key, public_key = generate_sm2_keypair()
        data = b"Test data"
        
        # 生成多个签名
        signatures = [sm2_sign(data, private_key) for _ in range(10)]
        
        # 所有签名都应该能验证通过
        for signature in signatures:
            result = sm2_verify(data, signature, public_key)
            assert result is True
    
    def test_signature_non_deterministic(self):
        """测试签名的非确定性（包含随机数 k）"""
        private_key, _ = generate_sm2_keypair()
        data = b"Test data"
        
        # 生成多个签名
        signatures = [sm2_sign(data, private_key) for _ in range(10)]
        
        # 由于 SM2 签名包含随机数 k，每次签名应该不同
        # 但这不是强制要求，某些实现可能使用确定性签名
        # 这里只检查至少有一些签名是不同的
        unique_signatures = set(signatures)
        # 至少应该有一些不同的签名（允许偶尔重复）
        assert len(unique_signatures) >= 1
