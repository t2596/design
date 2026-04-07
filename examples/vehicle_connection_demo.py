"""车辆接入与认证流程演示

演示任务 11.2 的实现：车辆接入与认证流程

此演示脚本展示了 SecurityGateway.handle_vehicle_connection() 方法的使用，
该方法实现了完整的车辆接入流程：
1. 接收车辆连接请求（携带车端证书）
2. 验证车端证书有效性
3. 执行双向身份认证
4. 建立安全会话
5. 记录认证事件到审计日志

注意：此演示需要 PostgreSQL 和 Redis 服务运行。
"""

from src.security_gateway import SecurityGateway
from src.models.certificate import SubjectInfo
from src.crypto.sm2 import generate_sm2_keypair
from src.certificate_manager import issue_certificate
from config.database import PostgreSQLConfig, RedisConfig
from src.db.postgres import PostgreSQLConnection


def main():
    """演示车辆接入与认证流程"""
    
    print("=" * 60)
    print("车辆接入与认证流程演示（任务 11.2）")
    print("=" * 60)
    print()
    
    # 步骤 1：生成密钥对
    print("步骤 1：生成密钥对...")
    ca_keypair = generate_sm2_keypair()
    gateway_keypair = generate_sm2_keypair()
    vehicle_keypair = generate_sm2_keypair()
    print("✓ CA 密钥对已生成")
    print("✓ 网关密钥对已生成")
    print("✓ 车辆密钥对已生成")
    print()
    
    # 步骤 2：颁发证书
    print("步骤 2：颁发证书...")
    db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
    
    try:
        # 颁发网关证书
        gateway_subject = SubjectInfo(
            vehicle_id="GATEWAY001",
            organization="Security Gateway",
            country="CN"
        )
        gateway_cert = issue_certificate(
            gateway_subject,
            gateway_keypair[1],
            ca_keypair[0],
            ca_keypair[1],
            db_conn
        )
        print(f"✓ 网关证书已颁发（序列号: {gateway_cert.serial_number[:16]}...)")
        
        # 颁发车辆证书
        vehicle_subject = SubjectInfo(
            vehicle_id="VIN123456789",
            organization="Test Vehicle Manufacturer",
            country="CN"
        )
        vehicle_cert = issue_certificate(
            vehicle_subject,
            vehicle_keypair[1],
            ca_keypair[0],
            ca_keypair[1],
            db_conn
        )
        print(f"✓ 车辆证书已颁发（序列号: {vehicle_cert.serial_number[:16]}...)")
        print()
        
        # 步骤 3：创建安全通信网关
        print("步骤 3：创建安全通信网关...")
        gateway = SecurityGateway(
            ca_private_key=ca_keypair[0],
            ca_public_key=ca_keypair[1],
            gateway_private_key=gateway_keypair[0],
            gateway_public_key=gateway_keypair[1],
            gateway_cert=gateway_cert
        )
        print("✓ 安全通信网关已创建")
        print()
        
        # 步骤 4：执行车辆接入与认证流程
        print("步骤 4：执行车辆接入与认证流程...")
        print("  - 车辆发起连接请求（携带车端证书）")
        print("  - 网关验证车端证书有效性")
        print("  - 执行双向身份认证（SM2 签名）")
        print("  - 建立安全会话")
        print("  - 记录认证事件到审计日志")
        print()
        
        success, session_info, error_msg = gateway.handle_vehicle_connection(
            vehicle_cert,
            vehicle_keypair[0],
            ip_address="192.168.1.100"
        )
        
        if success:
            print("✓ 车辆接入成功！")
            print()
            print("会话信息：")
            print(f"  - 会话 ID: {session_info.session_id[:32]}...")
            print(f"  - 车辆 ID: {session_info.vehicle_id}")
            print(f"  - 会话密钥长度: {len(session_info.sm4_session_key)} 字节")
            print(f"  - 会话状态: {session_info.status.value}")
            print(f"  - 建立时间: {session_info.established_at.isoformat()}")
            print(f"  - 过期时间: {session_info.expires_at.isoformat()}")
            print()
            
            # 步骤 5：查询审计日志
            print("步骤 5：查询审计日志...")
            from src.models.enums import EventType
            logs = gateway.audit_logger.query_audit_logs(
                vehicle_id="VIN123456789",
                event_type=EventType.AUTHENTICATION_SUCCESS
            )
            
            if logs:
                latest_log = logs[0]
                print("✓ 审计日志已记录")
                print(f"  - 日志 ID: {latest_log.log_id[:16]}...")
                print(f"  - 时间戳: {latest_log.timestamp.isoformat()}")
                print(f"  - 事件类型: {latest_log.event_type.value}")
                print(f"  - 车辆 ID: {latest_log.vehicle_id}")
                print(f"  - 操作结果: {'成功' if latest_log.operation_result else '失败'}")
                print(f"  - IP 地址: {latest_log.ip_address}")
                print(f"  - 详细信息: {latest_log.details}")
            print()
            
            # 步骤 6：清理会话
            print("步骤 6：清理会话...")
            gateway.terminate_session(session_info.session_id, session_info.vehicle_id)
            print("✓ 会话已终止")
            
        else:
            print(f"✗ 车辆接入失败: {error_msg}")
        
        # 关闭网关
        gateway.close()
        
    finally:
        db_conn.close()
    
    print()
    print("=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("\n请确保：")
        print("1. PostgreSQL 服务正在运行")
        print("2. Redis 服务正在运行")
        print("3. 数据库已初始化（运行 db/schema.sql）")
        print("4. 环境变量已配置（.env 文件）")
