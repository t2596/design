#!/usr/bin/env python3
"""生成 CA 密钥对并输出为十六进制格式

用于配置 Kubernetes secrets 中的 CA_PRIVATE_KEY 和 CA_PUBLIC_KEY 环境变量。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.crypto.sm2 import generate_sm2_keypair


def main():
    """生成 CA 密钥对"""
    
    print("=" * 70)
    print("生成 CA 密钥对（SM2 算法）")
    print("=" * 70)
    print()
    
    # 生成 SM2 密钥对
    print("正在生成 SM2 密钥对...")
    private_key, public_key = generate_sm2_keypair()
    
    print(f"✓ 密钥对生成成功")
    print(f"  - 私钥长度: {len(private_key)} 字节")
    print(f"  - 公钥长度: {len(public_key)} 字节")
    print()
    
    # 转换为十六进制
    private_key_hex = private_key.hex()
    public_key_hex = public_key.hex()
    
    print("=" * 70)
    print("密钥（十六进制格式）")
    print("=" * 70)
    print()
    print("CA 私钥（CA_PRIVATE_KEY）:")
    print(private_key_hex)
    print()
    print("CA 公钥（CA_PUBLIC_KEY）:")
    print(public_key_hex)
    print()
    
    # 生成 Kubernetes Secret 配置
    print("=" * 70)
    print("Kubernetes Secret 配置")
    print("=" * 70)
    print()
    print("方法 1: 直接在 deployment/kubernetes/gateway-deployment.yaml 中添加环境变量：")
    print()
    print("```yaml")
    print("        env:")
    print("        # ... 其他环境变量 ...")
    print(f"        - name: CA_PRIVATE_KEY")
    print(f"          value: \"{private_key_hex}\"")
    print(f"        - name: CA_PUBLIC_KEY")
    print(f"          value: \"{public_key_hex}\"")
    print("```")
    print()
    
    print("方法 2: 在 deployment/kubernetes/secrets.yaml 中添加（推荐）：")
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
    print("然后在 gateway-deployment.yaml 中引用：")
    print()
    print("```yaml")
    print("        env:")
    print("        - name: CA_PRIVATE_KEY")
    print("          valueFrom:")
    print("            secretKeyRef:")
    print("              name: gateway-secrets")
    print("              key: CA_PRIVATE_KEY")
    print("        - name: CA_PUBLIC_KEY")
    print("          valueFrom:")
    print("            secretKeyRef:")
    print("              name: gateway-secrets")
    print("              key: CA_PUBLIC_KEY")
    print("```")
    print()
    
    print("=" * 70)
    print("部署步骤")
    print("=" * 70)
    print()
    print("1. 更新 secrets.yaml 文件，添加上述 CA_PRIVATE_KEY 和 CA_PUBLIC_KEY")
    print("2. 应用 secrets 配置：")
    print("   kubectl apply -f deployment/kubernetes/secrets.yaml")
    print()
    print("3. 更新 gateway-deployment.yaml，添加环境变量引用")
    print("4. 重新部署网关：")
    print("   kubectl rollout restart deployment/gateway -n vehicle-iot-gateway")
    print()
    print("5. 验证部署：")
    print("   kubectl get pods -n vehicle-iot-gateway")
    print("   kubectl logs -n vehicle-iot-gateway deployment/gateway")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
