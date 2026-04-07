#!/usr/bin/env python3
"""将 PEM 格式的 CA 密钥转换为十六进制格式

用于配置 Kubernetes secrets 中的 CA_PRIVATE_KEY 和 CA_PUBLIC_KEY 环境变量。
"""

import sys
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def convert_pem_to_hex():
    """转换 PEM 格式密钥为十六进制"""
    
    # 你的 PEM 格式私钥（加密的）
    encrypted_private_key_pem = """-----BEGIN ENCRYPTED PRIVATE KEY-----
MIIBBjBhBgkqhkiG9w0BBQ0wVDA0BgkqhkiG9w0BBQwwJwQQPa75SPuGyXCFfTC5
gISDigIDAQAAAgEQMAsGCSqBHM9VAYMRAjAcBggqgRzPVQFoAgQQPWwhmVWIESVW
UsHKwmGqwQSBoBw4Ver14Ig2fmUpe5i6wOzzK2Naf+HHba2xN8phxYmqlSkHe8Dh
GIR9Uo+7u31XM014mywghis/0MRI+C+ODneKGrx+wx7JTmkErK02AXmm6BYdxnQK
Mqj/Dd9wAwFsS882WCBisbrSFfmypS4+LqPUEnG0FX+LSWZu5QDz0Zm9PW5/1r9u
eFO33Q9GJ2eTFHOOg8FXeSh7Nni2xicTtSE=
-----END ENCRYPTED PRIVATE KEY-----"""

    # 你的 PEM 格式公钥
    public_key_pem = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoEcz1UBgi0DQgAEv5QyonX+WWi/xciKEzH9ymQxdCQ+
atFNwPuMEprRBuqyH0U9rBDg1GtwbhzES409v99DNbzm/LqDbUQAhYtn0w==
-----END PUBLIC KEY-----"""

    print("=" * 70)
    print("CA 密钥转换工具")
    print("=" * 70)
    print()
    
    # 注意：这个私钥是加密的，需要密码才能解密
    # 对于 SM2 密钥，我们需要使用 gmssl 库
    # 但是由于这是加密的私钥，我们需要先解密
    
    print("⚠️  注意：你提供的私钥是加密的（ENCRYPTED PRIVATE KEY）")
    print("需要密码才能解密。")
    print()
    
    # 尝试解析公钥
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        
        public_key = load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )
        
        # 获取公钥的原始字节
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        public_key_hex = public_key_bytes.hex()
        
        print("✓ 公钥转换成功")
        print(f"公钥长度: {len(public_key_bytes)} 字节")
        print(f"公钥（十六进制）:")
        print(public_key_hex)
        print()
        
    except Exception as e:
        print(f"✗ 公钥转换失败: {str(e)}")
        print()
    
    # 对于加密的私钥，我们需要密码
    print("=" * 70)
    print("私钥解密")
    print("=" * 70)
    print()
    print("你的私钥是加密的，需要提供密码才能解密。")
    print("请输入私钥密码（如果没有密码，请按 Enter 跳过）：")
    
    try:
        password = input().strip()
        
        if password:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            
            private_key = load_pem_private_key(
                encrypted_private_key_pem.encode('utf-8'),
                password=password.encode('utf-8'),
                backend=default_backend()
            )
            
            # 获取私钥的原始字节（32 字节）
            private_key_bytes = private_key.private_numbers().private_value.to_bytes(32, byteorder='big')
            private_key_hex = private_key_bytes.hex()
            
            print()
            print("✓ 私钥解密成功")
            print(f"私钥长度: {len(private_key_bytes)} 字节")
            print(f"私钥（十六进制）:")
            print(private_key_hex)
            print()
            
            # 生成 Kubernetes Secret 配置
            print("=" * 70)
            print("Kubernetes Secret 配置")
            print("=" * 70)
            print()
            print("将以下内容添加到 deployment/kubernetes/secrets.yaml 中：")
            print()
            print("```yaml")
            print("apiVersion: v1")
            print("kind: Secret")
            print("metadata:")
            print("  name: gateway-secrets")
            print("  namespace: vehicle-iot-gateway")
            print("type: Opaque")
            print("stringData:")
            print(f"  CA_PRIVATE_KEY: \"{private_key_hex}\"")
            print(f"  CA_PUBLIC_KEY: \"{public_key_hex}\"")
            print("  # ... 其他 secrets ...")
            print("```")
            print()
            
        else:
            print()
            print("⚠️  未提供密码，跳过私钥解密")
            print()
            print("如果你的私钥没有密码保护，可能是格式问题。")
            print("建议使用 gmssl 工具生成新的 SM2 密钥对。")
            
    except Exception as e:
        print()
        print(f"✗ 私钥解密失败: {str(e)}")
        print()
        print("可能的原因：")
        print("1. 密码错误")
        print("2. 密钥格式不兼容")
        print("3. 需要使用 gmssl 库处理 SM2 密钥")


if __name__ == "__main__":
    try:
        convert_pem_to_hex()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {str(e)}")
        sys.exit(1)
