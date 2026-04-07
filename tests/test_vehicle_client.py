"""车辆客户端单元测试"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client.vehicle_client import VehicleClient
from src.models.certificate import Certificate, SubjectInfo, CertificateExtensions


class TestVehicleClient:
    """车辆客户端测试类"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        client = VehicleClient(
            vehicle_id="TEST_VIN_001",
            gateway_host="localhost",
            gateway_port=8000
        )
        
        assert client.vehicle_id == "TEST_VIN_001"
        assert client.gateway_host == "localhost"
        assert client.gateway_port == 8000
        assert client.private_key is None
        assert client.public_key is None
        assert client.certificate is None
    
    def test_generate_keypair(self):
        """测试密钥对生成"""
        client = VehicleClient(vehicle_id="TEST_VIN_002")
        
        private_key, public_key = client.generate_keypair()
        
        assert private_key is not None
        assert public_key is not None
        assert len(private_key) == 32
        assert len(public_key) == 64
        assert client.private_key == private_key
        assert client.public_key == public_key
    
    def test_create_mock_certificate(self):
        """测试模拟证书创建"""
        client = VehicleClient(vehicle_id="TEST_VIN_003")
        client.generate_keypair()
        
        cert = client._create_mock_certificate()
        
        assert cert is not None
        assert cert.serial_number is not None
        assert cert.version == 3
        assert cert.signature_algorithm == "SM2"
        assert cert.public_key == client.public_key
        assert "TEST_VIN_003" in cert.subject
        assert client.certificate == cert
    
    def test_simulate_data_collection(self):
        """测试数据采集模拟"""
        client = VehicleClient(vehicle_id="TEST_VIN_004")
        
        data = client.simulate_data_collection()
        
        assert data is not None
        assert isinstance(data, bytes)
        assert len(data) > 0
        
        # 验证数据格式
        import json
        vehicle_data = json.loads(data.decode('utf-8'))
        
        assert vehicle_data["vehicle_id"] == "TEST_VIN_004"
        assert "timestamp" in vehicle_data
        assert "state" in vehicle_data
        assert "gps" in vehicle_data
        assert "motion" in vehicle_data
        assert "fuel" in vehicle_data
        assert "temperature" in vehicle_data
        assert "battery" in vehicle_data
        assert "diagnostics" in vehicle_data
        
        # 验证 GPS 数据
        assert "latitude" in vehicle_data["gps"]
        assert "longitude" in vehicle_data["gps"]
        assert "heading" in vehicle_data["gps"]
        assert "satellites" in vehicle_data["gps"]
        
        # 验证运动数据
        assert "speed" in vehicle_data["motion"]
        assert "acceleration" in vehicle_data["motion"]
        assert "odometer" in vehicle_data["motion"]
        assert "trip_distance" in vehicle_data["motion"]
    
    def test_send_vehicle_data_without_session(self):
        """测试未建立会话时发送数据"""
        client = VehicleClient(vehicle_id="TEST_VIN_005")
        client.generate_keypair()
        
        data = b"test data"
        
        with pytest.raises(RuntimeError, match="请先完成身份认证"):
            client.send_vehicle_data(data)
    
    def test_send_vehicle_data_with_session(self):
        """测试建立会话后发送数据"""
        from src.crypto.sm4 import generate_sm4_key
        from src.crypto.sm2 import generate_sm2_keypair
        
        client = VehicleClient(vehicle_id="TEST_VIN_006")
        client.generate_keypair()
        
        # 模拟会话建立
        client.session_key = generate_sm4_key(16)
        client.session_id = "test_session"
        client.gateway_public_key = generate_sm2_keypair()[1]
        
        data = client.simulate_data_collection()
        secure_msg = client.send_vehicle_data(data)
        
        assert secure_msg is not None
        assert secure_msg.encrypted_payload is not None
        assert secure_msg.signature is not None
        assert secure_msg.nonce is not None
        assert secure_msg.header.sender_id == "TEST_VIN_006"
        assert secure_msg.header.receiver_id == "GATEWAY"
    
    def test_request_certificate_without_keypair(self):
        """测试未生成密钥对时申请证书"""
        client = VehicleClient(vehicle_id="TEST_VIN_007")
        
        with pytest.raises(RuntimeError, match="请先生成密钥对"):
            client.request_certificate()
    
    def test_full_workflow_offline(self):
        """测试完整离线工作流"""
        from src.crypto.sm4 import generate_sm4_key
        from src.crypto.sm2 import generate_sm2_keypair
        
        # 1. 初始化客户端
        client = VehicleClient(vehicle_id="TEST_VIN_008")
        
        # 2. 生成密钥对
        client.generate_keypair()
        assert client.private_key is not None
        
        # 3. 创建模拟证书
        cert = client._create_mock_certificate()
        assert cert is not None
        
        # 4. 模拟会话建立
        client.session_key = generate_sm4_key(16)
        client.session_id = "test_session"
        client.gateway_public_key = generate_sm2_keypair()[1]
        
        # 5. 采集数据
        data = client.simulate_data_collection()
        assert len(data) > 0
        
        # 6. 发送数据
        secure_msg = client.send_vehicle_data(data)
        assert secure_msg is not None
        
        print(f"✓ 完整离线工作流测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
