"""车辆客户端使用示例

演示如何使用车辆客户端模拟器进行测试。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client.vehicle_client import VehicleClient


def demo_single_transmission():
    """演示单次数据传输"""
    print("\n" + "="*60)
    print("示例 1：单次数据传输")
    print("="*60 + "\n")
    
    # 创建客户端
    client = VehicleClient(
        vehicle_id="DEMO_VIN_001",
        gateway_host="localhost",
        gateway_port=8000
    )
    
    # 生成密钥对
    client.generate_keypair()
    
    # 创建模拟证书（离线模式）
    client._create_mock_certificate()
    
    # 模拟会话建立
    from src.crypto.sm4 import generate_sm4_key
    from src.crypto.sm2 import generate_sm2_keypair
    
    client.session_key = generate_sm4_key(16)
    client.session_id = "demo_session_001"
    client.gateway_public_key = generate_sm2_keypair()[1]
    
    # 采集并发送数据
    vehicle_data = client.simulate_data_collection()
    secure_msg = client.send_vehicle_data(vehicle_data)
    
    if secure_msg:
        print("\n✓ 单次数据传输演示完成")
    else:
        print("\n✗ 数据传输失败")


def demo_continuous_transmission():
    """演示连续数据传输"""
    print("\n" + "="*60)
    print("示例 2：连续数据传输（5 次迭代）")
    print("="*60 + "\n")
    
    # 创建客户端
    client = VehicleClient(
        vehicle_id="DEMO_VIN_002",
        gateway_host="localhost",
        gateway_port=8000
    )
    
    # 生成密钥对
    client.generate_keypair()
    
    # 创建模拟证书
    client._create_mock_certificate()
    
    # 模拟会话建立
    from src.crypto.sm4 import generate_sm4_key
    from src.crypto.sm2 import generate_sm2_keypair
    
    client.session_key = generate_sm4_key(16)
    client.session_id = "demo_session_002"
    client.gateway_public_key = generate_sm2_keypair()[1]
    
    # 连续发送数据
    client.run_continuous_mode(interval=2, max_iterations=5)
    
    print("\n✓ 连续数据传输演示完成")


def demo_multiple_clients():
    """演示多个客户端同时运行"""
    print("\n" + "="*60)
    print("示例 3：多个客户端并发传输")
    print("="*60 + "\n")
    
    from src.crypto.sm4 import generate_sm4_key
    from src.crypto.sm2 import generate_sm2_keypair
    
    # 创建 3 个客户端
    clients = []
    for i in range(1, 4):
        client = VehicleClient(
            vehicle_id=f"DEMO_VIN_{i:03d}",
            gateway_host="localhost",
            gateway_port=8000
        )
        
        # 初始化客户端
        client.generate_keypair()
        client._create_mock_certificate()
        client.session_key = generate_sm4_key(16)
        client.session_id = f"demo_session_{i:03d}"
        client.gateway_public_key = generate_sm2_keypair()[1]
        
        clients.append(client)
    
    # 每个客户端发送一次数据
    for client in clients:
        vehicle_data = client.simulate_data_collection()
        secure_msg = client.send_vehicle_data(vehicle_data)
        
        if secure_msg:
            print(f"✓ 客户端 {client.vehicle_id} 数据传输成功")
        else:
            print(f"✗ 客户端 {client.vehicle_id} 数据传输失败")
    
    print("\n✓ 多客户端并发传输演示完成")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("车辆客户端模拟器 - 使用示例")
    print("="*60)
    
    # 运行所有示例
    demo_single_transmission()
    demo_continuous_transmission()
    demo_multiple_clients()
    
    print("\n" + "="*60)
    print("所有示例演示完成")
    print("="*60 + "\n")
