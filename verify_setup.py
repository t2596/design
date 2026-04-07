#!/usr/bin/env python
"""验证项目初始化是否成功"""

import sys
from datetime import datetime, timedelta

def verify_imports():
    """验证所有模块可以正确导入"""
    print("✓ 验证模块导入...")
    
    try:
        # 验证配置模块
        from config import PostgreSQLConfig, RedisConfig
        print("  ✓ 配置模块导入成功")
        
        # 验证数据模型
        from src.models import (
            Certificate, SubjectInfo, CertificateExtensions,
            SessionInfo, SessionStatus, AuthResult, AuthToken,
            SecureMessage, MessageHeader, MessageType,
            AuditLog, EventType, ErrorCode, ValidationResult
        )
        print("  ✓ 数据模型导入成功")
        
        # 验证数据库连接模块
        from src.db import PostgreSQLConnection, RedisConnection
        print("  ✓ 数据库连接模块导入成功")
        
        return True
    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        return False


def verify_data_models():
    """验证数据模型可以正确实例化"""
    print("\n✓ 验证数据模型...")
    
    try:
        from src.models import (
            Certificate, SubjectInfo, CertificateExtensions,
            SessionInfo, SessionStatus, AuthToken,
            SecureMessage, MessageHeader, MessageType,
            AuditLog, EventType
        )
        
        # 创建证书扩展
        extensions = CertificateExtensions()
        print("  ✓ CertificateExtensions 实例化成功")
        
        # 创建证书
        cert = Certificate(
            version=3,
            serial_number="TEST123456",
            issuer="CN=Test CA",
            subject="CN=Test Vehicle",
            valid_from=datetime.now(),
            valid_to=datetime.now() + timedelta(days=365),
            public_key=b"test_public_key",
            signature=b"test_signature",
            signature_algorithm="SM2",
            extensions=extensions
        )
        print("  ✓ Certificate 实例化成功")
        
        # 创建会话信息
        session = SessionInfo(
            session_id="a" * 64,  # 32 字节的十六进制字符串
            vehicle_id="VIN123456789",
            sm4_session_key=b"0" * 16,  # 16 字节密钥
            established_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            status=SessionStatus.ACTIVE,
            last_activity_time=datetime.now()
        )
        print("  ✓ SessionInfo 实例化成功")
        
        # 创建消息头
        header = MessageHeader(
            version=1,
            message_type=MessageType.DATA_TRANSFER,
            sender_id="vehicle_001",
            receiver_id="gateway_001",
            session_id="session_001"
        )
        print("  ✓ MessageHeader 实例化成功")
        
        # 创建安全报文
        message = SecureMessage(
            header=header,
            encrypted_payload=b"encrypted_data",
            signature=b"signature_data",
            timestamp=datetime.now(),
            nonce=b"0" * 16  # 16 字节 nonce
        )
        print("  ✓ SecureMessage 实例化成功")
        
        # 创建审计日志
        log = AuditLog(
            log_id="LOG123456",
            timestamp=datetime.now(),
            event_type=EventType.AUTHENTICATION_SUCCESS,
            vehicle_id="VIN123456789",
            operation_result=True,
            details="认证成功",
            ip_address="192.168.1.100"
        )
        print("  ✓ AuditLog 实例化成功")
        
        return True
    except Exception as e:
        print(f"  ✗ 实例化失败: {e}")
        return False


def verify_configuration():
    """验证配置可以正确加载"""
    print("\n✓ 验证配置加载...")
    
    try:
        from config import PostgreSQLConfig, RedisConfig
        
        # 从环境变量加载配置
        pg_config = PostgreSQLConfig.from_env()
        print(f"  ✓ PostgreSQL 配置: {pg_config.host}:{pg_config.port}/{pg_config.database}")
        
        redis_config = RedisConfig.from_env()
        print(f"  ✓ Redis 配置: {redis_config.host}:{redis_config.port}/{redis_config.db}")
        
        # 验证连接字符串生成
        conn_str = pg_config.get_connection_string()
        print(f"  ✓ PostgreSQL 连接字符串生成成功")
        
        return True
    except Exception as e:
        print(f"  ✗ 配置加载失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("车联网安全通信网关系统 - 项目初始化验证")
    print("=" * 60)
    
    results = []
    
    # 执行验证
    results.append(verify_imports())
    results.append(verify_data_models())
    results.append(verify_configuration())
    
    # 输出结果
    print("\n" + "=" * 60)
    if all(results):
        print("✓ 所有验证通过！项目初始化成功。")
        print("=" * 60)
        return 0
    else:
        print("✗ 部分验证失败，请检查错误信息。")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
