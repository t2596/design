"""安全通信网关演示脚本

演示如何使用 SecurityGateway 类进行车辆认证和安全通信。

注意：此演示需要 PostgreSQL 和 Redis 服务运行。
"""

from src.security_gateway import SecurityGateway
from src.models.certificate import SubjectInfo
from src.models.message import MessageType
from src.crypto.sm2 import generate_sm2_keypair
from src.certificate_manager import issue_certificate
from config.database import PostgreSQLConfig, RedisConfig
from src.db.postgres import PostgreSQLConnection


def main():
    """主演示函数"""
    print("=" * 60)
    print("车联网安全通信网关演示")
    print("=" * 60)
    
    # 步骤 1：生成密钥对
    print("\n步骤 1：生成密钥对...")
    ca_keypair = generate_sm2_keypair()
    gateway_keypair = generate_sm2_keypair()
    vehicle_keypair = generate_sm2_keypair()
    
    print(f"  CA 私钥长度: {len(ca_keypair[0])} 字节")
    print(f"  CA 公钥长度: {len(ca_keypair[1])} 字节")
    print(f"  网关私钥长度: {len(gateway_keypair[0])} 字节")
    print(f"  网关公钥长度: {len(gateway_keypair[1])} 字节")
    print(f"  车辆私钥长度: {len(vehicle_keypair[0])} 字节")
    print(f"  车辆公钥长度: {len(vehicle_keypair[1])} 字节")
    
    # 步骤 2：颁发证书
    print("\n步骤 2：颁发证书...")
    
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
            gateway_keypair[1],  # 公钥
            ca_keypair[0],  # CA 私钥
            ca_keypair[1],  # CA 公钥
            db_conn
        )
        
        print(f"  网关证书序列号: {gateway_cert.serial_number}")
        print(f"  网关证书有效期: {gateway_cert.valid_from} 至 {gateway_cert.valid_to}")
        
        # 颁发车辆证书
        vehicle_subject = SubjectInfo(
            vehicle_id="VIN123456789",
            organization="Test Vehicle Manufacturer",
            country="CN"
        )
        
        vehicle_cert = issue_certificate(
            vehicle_subject,
            vehicle_keypair[1],  # 公钥
            ca_keypair[0],  # CA 私钥
            ca_keypair[1],  # CA 公钥
            db_conn
        )
        
        print(f"  车辆证书序列号: {vehicle_cert.serial_number}")
        print(f"  车辆证书有效期: {vehicle_cert.valid_from} 至 {vehicle_cert.valid_to}")
        
        # 步骤 3：创建安全通信网关
        print("\n步骤 3：创建安全通信网关...")
        
        with SecurityGateway(
            ca_private_key=ca_keypair[0],
            ca_public_key=ca_keypair[1],
            gateway_private_key=gateway_keypair[0],
            gateway_public_key=gateway_keypair[1],
            gateway_cert=gateway_cert
        ) as gateway:
            print("  安全通信网关已创建")
            
            # 步骤 4：验证车辆证书
            print("\n步骤 4：验证车辆证书...")
            result, message = gateway.verify_vehicle_certificate(vehicle_cert)
            print(f"  验证结果: {result.value}")
            print(f"  验证消息: {message}")
            
            # 步骤 5：认证车辆
            print("\n步骤 5：认证车辆...")
            auth_result = gateway.authenticate_vehicle(
                vehicle_cert,
                vehicle_keypair[0]  # 私钥
            )
            
            if auth_result.success:
                print("  认证成功！")
                print(f"  会话密钥长度: {len(auth_result.session_key)} 字节")
                print(f"  令牌车辆 ID: {auth_result.token.vehicle_id}")
                print(f"  令牌有效期: {auth_result.token.issued_at} 至 {auth_result.token.expires_at}")
            else:
                print(f"  认证失败: {auth_result.error_message}")
                return
            
            # 步骤 6：创建会话
            print("\n步骤 6：创建会话...")
            vehicle_id = "VIN123456789"
            session_info = gateway.create_session(vehicle_id, auth_result)
            
            print(f"  会话 ID: {session_info.session_id}")
            print(f"  会话密钥长度: {len(session_info.sm4_session_key)} 字节")
            print(f"  会话状态: {session_info.status.value}")
            print(f"  会话过期时间: {session_info.expires_at}")
            
            # 步骤 7：发送安全报文
            print("\n步骤 7：发送安全报文...")
            plain_data = b"Hello from vehicle! This is test data."
            
            secure_msg = gateway.send_secure_message(
                plain_data,
                session_info.sm4_session_key,
                "GATEWAY001",
                vehicle_id,
                session_info.session_id,
                MessageType.DATA_TRANSFER
            )
            
            print(f"  原始数据长度: {len(plain_data)} 字节")
            print(f"  加密数据长度: {len(secure_msg.encrypted_payload)} 字节")
            print(f"  签名长度: {len(secure_msg.signature)} 字节")
            print(f"  Nonce 长度: {len(secure_msg.nonce)} 字节")
            print(f"  时间戳: {secure_msg.timestamp}")
            
            # 步骤 8：接收并验证安全报文
            print("\n步骤 8：接收并验证安全报文...")
            decrypted_data = gateway.receive_secure_message(
                secure_msg,
                session_info.sm4_session_key,
                gateway_keypair[1],  # 发送方公钥
                "GATEWAY001"
            )
            
            print(f"  解密数据长度: {len(decrypted_data)} 字节")
            print(f"  解密数据内容: {decrypted_data.decode('utf-8')}")
            print(f"  数据完整性验证: {'通过' if decrypted_data == plain_data else '失败'}")
            
            # 步骤 9：检查证书状态
            print("\n步骤 9：检查证书状态...")
            cert_status = gateway.check_certificate_status(vehicle_cert)
            
            print(f"  证书状态: {cert_status['status']}")
            print(f"  距离过期天数: {cert_status['days_until_expiry']} 天")
            print(f"  状态消息: {cert_status['message']}")
            
            # 步骤 10：终止会话
            print("\n步骤 10：终止会话...")
            success = gateway.terminate_session(
                session_info.session_id,
                vehicle_id
            )
            
            print(f"  会话终止: {'成功' if success else '失败'}")
        
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db_conn.close()


if __name__ == "__main__":
    main()
