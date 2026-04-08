"""证书验证缓存与证书管理器的集成测试"""

import pytest
from datetime import datetime, timedelta
from src.certificate_manager import verify_certificate, revoke_certificate
from src.certificate_cache import get_certificate_cache
from src.models.certificate import Certificate, SubjectInfo, CertificateExtensions
from src.models.enums import ValidationResult
from src.crypto.sm2 import generate_sm2_keypair


class TestCertificateVerificationCache:
    """证书验证缓存集成测试"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试前清空缓存"""
        cache = get_certificate_cache()
        cache.clear()
        yield
        cache.clear()
    
    @pytest.fixture
    def ca_keypair(self):
        """生成 CA 密钥对"""
        private_key, public_key = generate_sm2_keypair()
        return {'private_key': private_key, 'public_key': public_key}
    
    @pytest.fixture
    def valid_certificate(self, ca_keypair):
        """创建有效的测试证书"""
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        
        subject_info = SubjectInfo(
            vehicle_id="TEST_VEHICLE_001",
            organization="测试组织",
            country="CN"
        )
        
        certificate = Certificate(
            version=3,
            serial_number="test_serial_12345678",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject=f"CN={subject_info.vehicle_id},O={subject_info.organization},C={subject_info.country}",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,  # 占位符签名
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature,keyEncipherment",
                extended_key_usage="clientAuth,serverAuth"
            )
        )
        
        # 使用 CA 私钥签名证书
        from src.certificate_manager import encode_tbs_certificate
        from src.crypto.sm2 import sm2_sign
        
        tbs_certificate = encode_tbs_certificate(certificate)
        signature = sm2_sign(tbs_certificate, ca_keypair['private_key'])
        certificate.signature = signature
        
        return certificate
    
    def test_cache_hit_on_second_verification(self, valid_certificate, ca_keypair):
        """测试第二次验证时缓存命中"""
        cache = get_certificate_cache()
        crl_list = []
        
        # 第一次验证（缓存未命中）
        result1 = verify_certificate(
            valid_certificate,
            ca_keypair['public_key'],
            crl_list,
            use_cache=True
        )
        assert result1[0] == ValidationResult.VALID
        
        # 验证缓存中有该证书
        cached_result = cache.get(valid_certificate.serial_number)
        assert cached_result is not None
        assert cached_result[0] == ValidationResult.VALID
        
        # 第二次验证（应该从缓存获取）
        result2 = verify_certificate(
            valid_certificate,
            ca_keypair['public_key'],
            crl_list,
            use_cache=True
        )
        assert result2[0] == ValidationResult.VALID
        assert result2 == result1
    
    def test_cache_bypass_when_disabled(self, valid_certificate, ca_keypair):
        """测试禁用缓存时不使用缓存"""
        cache = get_certificate_cache()
        crl_list = []
        
        # 第一次验证，禁用缓存
        result1 = verify_certificate(
            valid_certificate,
            ca_keypair['public_key'],
            crl_list,
            use_cache=False
        )
        assert result1[0] == ValidationResult.VALID
        
        # 验证缓存中没有该证书
        cached_result = cache.get(valid_certificate.serial_number)
        assert cached_result is None
    
    def test_cache_expired_certificate(self, ca_keypair):
        """测试过期证书的缓存"""
        cache = get_certificate_cache()
        
        # 创建过期证书
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        expired_cert = Certificate(
            version=3,
            serial_number="expired_serial_123",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=EXPIRED_VEHICLE,O=测试组织,C=CN",
            valid_from=datetime.utcnow() - timedelta(days=400),
            valid_to=datetime.utcnow() - timedelta(days=35),  # 过期 35 天
            public_key=vehicle_public_key,
            signature=b'\x00' * 64,
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature,keyEncipherment",
                extended_key_usage="clientAuth,serverAuth"
            )
        )
        
        crl_list = []
        
        # 验证过期证书
        result = verify_certificate(
            expired_cert,
            ca_keypair['public_key'],
            crl_list,
            use_cache=True
        )
        assert result[0] == ValidationResult.INVALID
        assert "过期" in result[1]
        
        # 验证过期结果被缓存
        cached_result = cache.get(expired_cert.serial_number)
        assert cached_result is not None
        assert cached_result[0] == ValidationResult.INVALID
    
    def test_cache_revoked_certificate(self, valid_certificate, ca_keypair):
        """测试已撤销证书的缓存"""
        cache = get_certificate_cache()
        
        # 将证书序列号添加到 CRL
        crl_list = [valid_certificate.serial_number]
        
        # 验证已撤销证书
        result = verify_certificate(
            valid_certificate,
            ca_keypair['public_key'],
            crl_list,
            use_cache=True
        )
        assert result[0] == ValidationResult.REVOKED
        assert "撤销" in result[1]
        
        # 验证撤销结果被缓存
        cached_result = cache.get(valid_certificate.serial_number)
        assert cached_result is not None
        assert cached_result[0] == ValidationResult.REVOKED
    
    @pytest.mark.skip(reason="Requires database connection - integration test")
    def test_cache_invalidation_on_revocation(self, valid_certificate, ca_keypair, db_connection):
        """测试撤销证书时缓存失效"""
        cache = get_certificate_cache()
        crl_list = []
        
        # 首先存储证书到数据库
        from src.certificate_manager import store_certificate
        store_certificate(valid_certificate, db_connection)
        
        # 第一次验证（缓存有效结果）
        result1 = verify_certificate(
            valid_certificate,
            ca_keypair['public_key'],
            crl_list,
            use_cache=True
        )
        assert result1[0] == ValidationResult.VALID
        
        # 验证缓存中有该证书
        cached_result = cache.get(valid_certificate.serial_number)
        assert cached_result is not None
        assert cached_result[0] == ValidationResult.VALID
        
        # 撤销证书（应该使缓存失效）
        revoke_certificate(
            valid_certificate.serial_number,
            reason="测试撤销",
            db_conn=db_connection
        )
        
        # 验证缓存已失效
        cached_result_after_revoke = cache.get(valid_certificate.serial_number)
        assert cached_result_after_revoke is None
    
    def test_cache_invalid_signature(self, ca_keypair):
        """测试签名无效证书的缓存"""
        cache = get_certificate_cache()
        
        # 创建签名无效的证书
        vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
        invalid_cert = Certificate(
            version=3,
            serial_number="invalid_sig_serial",
            issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
            subject="CN=INVALID_VEHICLE,O=测试组织,C=CN",
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=vehicle_public_key,
            signature=b'\xFF' * 64,  # 无效签名
            signature_algorithm="SM2",
            extensions=CertificateExtensions(
                key_usage="digitalSignature,keyEncipherment",
                extended_key_usage="clientAuth,serverAuth"
            )
        )
        
        crl_list = []
        
        # 验证签名无效证书
        result = verify_certificate(
            invalid_cert,
            ca_keypair['public_key'],
            crl_list,
            use_cache=True
        )
        assert result[0] == ValidationResult.INVALID
        assert "签名" in result[1]
        
        # 验证签名失败结果被缓存
        cached_result = cache.get(invalid_cert.serial_number)
        assert cached_result is not None
        assert cached_result[0] == ValidationResult.INVALID
    
    def test_cache_performance_improvement(self, valid_certificate, ca_keypair):
        """测试缓存对性能的改善"""
        import time
        
        crl_list = []
        
        # 第一次验证（无缓存）
        start_time = time.time()
        result1 = verify_certificate(
            valid_certificate,
            ca_keypair['public_key'],
            crl_list,
            use_cache=True
        )
        first_verification_time = time.time() - start_time
        assert result1[0] == ValidationResult.VALID
        
        # 第二次验证（有缓存）
        start_time = time.time()
        result2 = verify_certificate(
            valid_certificate,
            ca_keypair['public_key'],
            crl_list,
            use_cache=True
        )
        second_verification_time = time.time() - start_time
        assert result2[0] == ValidationResult.VALID
        
        # 第二次验证应该明显更快（至少快 50%）
        print(f"第一次验证耗时: {first_verification_time * 1000:.2f} ms")
        print(f"第二次验证耗时: {second_verification_time * 1000:.2f} ms")
        print(f"性能提升: {(1 - second_verification_time / first_verification_time) * 100:.1f}%")
        
        # 缓存命中应该显著提高性能
        assert second_verification_time < first_verification_time * 0.5
    
    def test_cache_multiple_certificates(self, ca_keypair):
        """测试缓存多个证书"""
        cache = get_certificate_cache()
        crl_list = []
        
        certificates = []
        for i in range(10):
            vehicle_private_key, vehicle_public_key = generate_sm2_keypair()
            cert = Certificate(
                version=3,
                serial_number=f"multi_cert_serial_{i}",
                issuer="CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN",
                subject=f"CN=VEHICLE_{i},O=测试组织,C=CN",
                valid_from=datetime.utcnow(),
                valid_to=datetime.utcnow() + timedelta(days=365),
                public_key=vehicle_public_key,
                signature=b'\x00' * 64,
                signature_algorithm="SM2",
                extensions=CertificateExtensions(
                    key_usage="digitalSignature,keyEncipherment",
                    extended_key_usage="clientAuth,serverAuth"
                )
            )
            
            # 签名证书
            from src.certificate_manager import encode_tbs_certificate
            from src.crypto.sm2 import sm2_sign
            tbs_certificate = encode_tbs_certificate(cert)
            signature = sm2_sign(tbs_certificate, ca_keypair['private_key'])
            cert.signature = signature
            
            certificates.append(cert)
        
        # 验证所有证书
        for cert in certificates:
            result = verify_certificate(
                cert,
                ca_keypair['public_key'],
                crl_list,
                use_cache=True
            )
            assert result[0] == ValidationResult.VALID
        
        # 验证所有证书都被缓存
        assert cache.size() == 10
        
        # 再次验证所有证书（应该从缓存获取）
        for cert in certificates:
            cached_result = cache.get(cert.serial_number)
            assert cached_result is not None
            assert cached_result[0] == ValidationResult.VALID


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
