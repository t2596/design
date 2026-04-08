"""证书验证缓存模块的单元测试"""

import pytest
import time
from src.certificate_cache import CertificateCache, get_certificate_cache
from src.models.enums import ValidationResult


class TestCertificateCache:
    """证书缓存的单元测试"""
    
    def test_cache_initialization(self):
        """测试缓存初始化"""
        cache = CertificateCache(max_size=100, ttl_seconds=60)
        assert cache.max_size == 100
        assert cache.ttl_seconds == 60
        assert cache.size() == 0
    
    def test_cache_put_and_get(self):
        """测试缓存的存储和获取"""
        cache = CertificateCache(max_size=100, ttl_seconds=60)
        
        # 存储验证结果
        serial_number = "test_serial_123"
        result = ValidationResult.VALID
        message = "证书验证通过"
        
        cache.put(serial_number, result, message)
        
        # 获取验证结果
        cached_result = cache.get(serial_number)
        assert cached_result is not None
        assert cached_result[0] == result
        assert cached_result[1] == message
        assert cache.size() == 1
    
    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = CertificateCache(max_size=100, ttl_seconds=60)
        
        # 获取不存在的条目
        result = cache.get("nonexistent_serial")
        assert result is None
    
    def test_cache_ttl_expiration(self):
        """测试缓存 TTL 过期"""
        cache = CertificateCache(max_size=100, ttl_seconds=1)  # 1 秒 TTL
        
        serial_number = "test_serial_ttl"
        cache.put(serial_number, ValidationResult.VALID, "证书验证通过")
        
        # 立即获取应该成功
        result = cache.get(serial_number)
        assert result is not None
        
        # 等待 TTL 过期
        time.sleep(1.1)
        
        # 过期后获取应该返回 None
        result = cache.get(serial_number)
        assert result is None
        assert cache.size() == 0  # 过期条目应该被删除
    
    def test_cache_lru_eviction(self):
        """测试 LRU 淘汰策略"""
        cache = CertificateCache(max_size=3, ttl_seconds=60)
        
        # 添加 3 个条目（填满缓存）
        cache.put("serial_1", ValidationResult.VALID, "msg1")
        cache.put("serial_2", ValidationResult.VALID, "msg2")
        cache.put("serial_3", ValidationResult.VALID, "msg3")
        assert cache.size() == 3
        
        # 添加第 4 个条目，应该淘汰最旧的（serial_1）
        cache.put("serial_4", ValidationResult.VALID, "msg4")
        assert cache.size() == 3
        
        # serial_1 应该被淘汰
        assert cache.get("serial_1") is None
        
        # 其他条目应该还在
        assert cache.get("serial_2") is not None
        assert cache.get("serial_3") is not None
        assert cache.get("serial_4") is not None
    
    def test_cache_lru_access_order(self):
        """测试 LRU 访问顺序更新"""
        cache = CertificateCache(max_size=3, ttl_seconds=60)
        
        # 添加 3 个条目
        cache.put("serial_1", ValidationResult.VALID, "msg1")
        cache.put("serial_2", ValidationResult.VALID, "msg2")
        cache.put("serial_3", ValidationResult.VALID, "msg3")
        
        # 访问 serial_1，使其成为最近使用的
        cache.get("serial_1")
        
        # 添加新条目，应该淘汰 serial_2（最旧的未访问条目）
        cache.put("serial_4", ValidationResult.VALID, "msg4")
        
        # serial_2 应该被淘汰
        assert cache.get("serial_2") is None
        
        # serial_1 应该还在（因为最近被访问）
        assert cache.get("serial_1") is not None
    
    def test_cache_update_existing_entry(self):
        """测试更新已存在的缓存条目"""
        cache = CertificateCache(max_size=100, ttl_seconds=60)
        
        serial_number = "test_serial_update"
        
        # 第一次存储
        cache.put(serial_number, ValidationResult.VALID, "第一次验证")
        result1 = cache.get(serial_number)
        assert result1[1] == "第一次验证"
        
        # 更新条目
        cache.put(serial_number, ValidationResult.INVALID, "第二次验证")
        result2 = cache.get(serial_number)
        assert result2[0] == ValidationResult.INVALID
        assert result2[1] == "第二次验证"
        
        # 缓存大小应该保持为 1
        assert cache.size() == 1
    
    def test_cache_invalidate(self):
        """测试缓存失效"""
        cache = CertificateCache(max_size=100, ttl_seconds=60)
        
        serial_number = "test_serial_invalidate"
        cache.put(serial_number, ValidationResult.VALID, "证书验证通过")
        
        # 验证条目存在
        assert cache.get(serial_number) is not None
        
        # 使缓存失效
        cache.invalidate(serial_number)
        
        # 验证条目已被删除
        assert cache.get(serial_number) is None
        assert cache.size() == 0
    
    def test_cache_invalidate_nonexistent(self):
        """测试使不存在的条目失效（应该不报错）"""
        cache = CertificateCache(max_size=100, ttl_seconds=60)
        
        # 使不存在的条目失效，不应该抛出异常
        cache.invalidate("nonexistent_serial")
        assert cache.size() == 0
    
    def test_cache_clear(self):
        """测试清空缓存"""
        cache = CertificateCache(max_size=100, ttl_seconds=60)
        
        # 添加多个条目
        cache.put("serial_1", ValidationResult.VALID, "msg1")
        cache.put("serial_2", ValidationResult.VALID, "msg2")
        cache.put("serial_3", ValidationResult.VALID, "msg3")
        assert cache.size() == 3
        
        # 清空缓存
        cache.clear()
        assert cache.size() == 0
        
        # 所有条目应该被删除
        assert cache.get("serial_1") is None
        assert cache.get("serial_2") is None
        assert cache.get("serial_3") is None
    
    def test_cache_cleanup_expired(self):
        """测试清理过期条目"""
        cache = CertificateCache(max_size=100, ttl_seconds=1)  # 1 秒 TTL
        
        # 添加多个条目
        cache.put("serial_1", ValidationResult.VALID, "msg1")
        time.sleep(0.5)
        cache.put("serial_2", ValidationResult.VALID, "msg2")
        time.sleep(0.5)
        cache.put("serial_3", ValidationResult.VALID, "msg3")
        
        # 此时 serial_1 应该过期，serial_2 和 serial_3 还未过期
        time.sleep(0.2)
        
        # 清理过期条目
        expired_count = cache.cleanup_expired()
        assert expired_count >= 1  # 至少 serial_1 过期
        
        # serial_1 应该被删除
        assert cache.get("serial_1") is None
    
    def test_cache_different_validation_results(self):
        """测试缓存不同的验证结果"""
        cache = CertificateCache(max_size=100, ttl_seconds=60)
        
        # 缓存有效证书
        cache.put("valid_cert", ValidationResult.VALID, "证书验证通过")
        
        # 缓存无效证书
        cache.put("invalid_cert", ValidationResult.INVALID, "证书格式错误")
        
        # 缓存已撤销证书
        cache.put("revoked_cert", ValidationResult.REVOKED, "证书已被撤销")
        
        # 验证所有结果都被正确缓存
        valid_result = cache.get("valid_cert")
        assert valid_result[0] == ValidationResult.VALID
        
        invalid_result = cache.get("invalid_cert")
        assert invalid_result[0] == ValidationResult.INVALID
        
        revoked_result = cache.get("revoked_cert")
        assert revoked_result[0] == ValidationResult.REVOKED
    
    def test_global_cache_singleton(self):
        """测试全局缓存单例"""
        cache1 = get_certificate_cache()
        cache2 = get_certificate_cache()
        
        # 应该返回同一个实例
        assert cache1 is cache2
        
        # 在一个实例中存储数据
        cache1.put("test_serial", ValidationResult.VALID, "测试")
        
        # 在另一个实例中应该能获取到
        result = cache2.get("test_serial")
        assert result is not None
        assert result[0] == ValidationResult.VALID
    
    def test_cache_thread_safety_basic(self):
        """测试缓存的基本线程安全性"""
        import threading
        
        cache = CertificateCache(max_size=1000, ttl_seconds=60)
        
        def add_entries(start_index, count):
            for i in range(start_index, start_index + count):
                serial = f"serial_{i}"
                cache.put(serial, ValidationResult.VALID, f"msg_{i}")
        
        # 创建多个线程并发添加条目
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_entries, args=(i * 100, 100))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证缓存大小
        assert cache.size() == 500
    
    def test_cache_performance_large_dataset(self):
        """测试大数据集的缓存性能"""
        cache = CertificateCache(max_size=10000, ttl_seconds=300)
        
        # 添加 10,000 个条目
        start_time = time.time()
        for i in range(10000):
            serial = f"serial_{i}"
            cache.put(serial, ValidationResult.VALID, f"msg_{i}")
        add_time = time.time() - start_time
        
        # 验证缓存大小
        assert cache.size() == 10000
        
        # 测试查询性能
        start_time = time.time()
        for i in range(1000):
            serial = f"serial_{i}"
            result = cache.get(serial)
            assert result is not None
        query_time = time.time() - start_time
        
        # 性能断言（添加和查询应该很快）
        assert add_time < 1.0  # 添加 10,000 条目应该在 1 秒内完成
        assert query_time < 0.1  # 查询 1,000 条目应该在 0.1 秒内完成
        
        print(f"添加 10,000 条目耗时: {add_time:.3f} 秒")
        print(f"查询 1,000 条目耗时: {query_time:.3f} 秒")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
