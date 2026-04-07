"""车辆客户端模拟器

模拟车辆终端设备，实现与安全通信网关的完整交互流程：
1. 证书申请与获取
2. 双向身份认证
3. 安全数据传输
4. 会话管理
"""

import os
import sys
import time
import json
import argparse
import random
import math
from typing import Optional, Tuple
from datetime import datetime
from enum import Enum

# 添加父目录到路径以导入共享模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.crypto.sm2 import generate_sm2_keypair, sm2_sign, sm2_verify
from src.crypto.sm4 import generate_sm4_key, sm4_encrypt, sm4_decrypt
from src.models.certificate import Certificate, SubjectInfo
from src.models.message import SecureMessage, MessageType
from src.secure_messaging import secure_data_transmission, verify_and_decrypt_message


class VehicleState(Enum):
    """车辆状态"""
    PARKED = "停车"
    IDLE = "怠速"
    ACCELERATING = "加速"
    CRUISING = "巡航"
    DECELERATING = "减速"
    BRAKING = "刹车"


class VehicleClient:
    """车辆客户端类
    
    模拟车辆终端设备的行为，包括证书管理、身份认证和安全数据传输。
    """
    
    def __init__(
        self,
        vehicle_id: str,
        gateway_host: str = "localhost",
        gateway_port: int = 8000,
        organization: str = "Test Vehicle Manufacturer",
        country: str = "CN",
        api_token: Optional[str] = None
    ):
        """初始化车辆客户端
        
        参数:
            vehicle_id: 车辆标识（VIN）
            gateway_host: 网关主机地址
            gateway_port: 网关端口
            organization: 组织名称
            country: 国家代码
            api_token: API 认证令牌（用于证书申请）
        """
        self.vehicle_id = vehicle_id
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port
        self.gateway_url = f"http://{gateway_host}:{gateway_port}"
        self.api_token = api_token or os.getenv("API_TOKEN", "dev-token-12345")
        
        # 车辆信息
        self.subject_info = SubjectInfo(
            vehicle_id=vehicle_id,
            organization=organization,
            country=country
        )
        
        # 密钥对（初始为空，需要生成）
        self.private_key: Optional[bytes] = None
        self.public_key: Optional[bytes] = None
        
        # 证书（初始为空，需要申请）
        self.certificate: Optional[Certificate] = None
        
        # 会话信息
        self.session_id: Optional[str] = None
        self.session_key: Optional[bytes] = None
        self.gateway_public_key: Optional[bytes] = None
        
        # 车辆动态状态
        self.state = VehicleState.PARKED
        self.speed = 0.0  # km/h
        self.latitude = 39.9042  # 北京天安门附近
        self.longitude = 116.4074
        self.heading = random.uniform(0, 360)  # 行驶方向（度）
        self.odometer = random.randint(10000, 50000)  # 总里程
        self.fuel_level = random.uniform(30, 95)  # 油量百分比
        self.engine_temp = 20.0  # 发动机温度
        self.cabin_temp = 20.0  # 车内温度
        self.trip_distance = 0.0  # 本次行程距离
        
        print(f"✓ 车辆客户端初始化成功: {vehicle_id}")
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """生成 SM2 密钥对
        
        返回:
            Tuple[bytes, bytes]: (私钥, 公钥)
        """
        print("正在生成 SM2 密钥对...")
        self.private_key, self.public_key = generate_sm2_keypair()
        print(f"✓ 密钥对生成成功")
        print(f"  - 私钥长度: {len(self.private_key)} 字节")
        print(f"  - 公钥长度: {len(self.public_key)} 字节")
        return self.private_key, self.public_key
    
    def request_certificate(self) -> Certificate:
        """向网关申请证书
        
        返回:
            Certificate: 颁发的证书
        """
        if self.private_key is None or self.public_key is None:
            raise RuntimeError("请先生成密钥对")
        
        print(f"\n正在向网关申请证书...")
        print(f"  - 车辆 ID: {self.vehicle_id}")
        print(f"  - 组织: {self.subject_info.organization}")
        
        try:
            import requests
            
            # 调用网关 API 申请证书
            response = requests.post(
                f"{self.gateway_url}/api/certificates/issue",
                json={
                    "vehicle_id": self.vehicle_id,
                    "organization": self.subject_info.organization,
                    "country": self.subject_info.country,
                    "public_key": self.public_key.hex()
                },
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                cert_data = response.json()
                self.certificate = Certificate.from_dict(cert_data)
                print(f"✓ 证书申请成功")
                print(f"  - 序列号: {self.certificate.serial_number}")
                print(f"  - 有效期: {self.certificate.valid_from} 至 {self.certificate.valid_to}")
                return self.certificate
            else:
                raise RuntimeError(f"证书申请失败: {response.status_code} - {response.text}")
                
        except ImportError:
            # 如果没有 requests 库，使用模拟证书
            print("⚠ requests 库未安装，使用模拟证书")
            return self._create_mock_certificate()
        except Exception as e:
            print(f"⚠ 证书申请失败: {str(e)}")
            print("使用模拟证书继续...")
            return self._create_mock_certificate()
    
    def _create_mock_certificate(self) -> Certificate:
        """创建模拟证书（用于离线测试）"""
        from datetime import datetime, timedelta
        from src.models.certificate import CertificateExtensions
        import uuid
        
        # 生成模拟证书（不依赖数据库）
        subject_str = f"C={self.subject_info.country},O={self.subject_info.organization},CN={self.vehicle_id}"
        
        self.certificate = Certificate(
            version=3,
            serial_number=str(uuid.uuid4()),
            issuer="C=CN,O=Mock CA,CN=Mock Root CA",
            subject=subject_str,
            valid_from=datetime.utcnow(),
            valid_to=datetime.utcnow() + timedelta(days=365),
            public_key=self.public_key,
            signature=b"mock_signature_" + os.urandom(32),
            signature_algorithm="SM2",
            extensions=CertificateExtensions()
        )
        
        print(f"✓ 模拟证书创建成功（离线模式）")
        print(f"  - 序列号: {self.certificate.serial_number}")
        return self.certificate
    
    def authenticate_with_gateway(self, gateway_cert: Certificate) -> bool:
        """与网关进行双向身份认证
        
        参数:
            gateway_cert: 网关证书
            
        返回:
            bool: 认证是否成功
        """
        if self.certificate is None:
            raise RuntimeError("请先申请证书")
        
        print(f"\n正在与网关进行双向身份认证...")
        
        try:
            import requests
            
            # 通过网关 API 进行认证
            response = requests.post(
                f"{self.gateway_url}/api/auth/authenticate",
                json={
                    "vehicle_id": self.vehicle_id,
                    "certificate": self.certificate.to_dict(),
                    "challenge_response": "mock_challenge_response"  # 实际应该是签名的挑战响应
                },
                headers={"X-API-Key": os.getenv("API_KEY", "test-api-key")},
                timeout=10
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                self.session_key = bytes.fromhex(auth_data["session_key"])
                self.session_id = auth_data["session_id"]
                self.gateway_public_key = bytes.fromhex(auth_data["gateway_public_key"])
                
                print(f"✓ 双向认证成功")
                print(f"  - 会话密钥长度: {len(self.session_key)} 字节")
                print(f"  - 会话 ID: {self.session_id}")
                return True
            else:
                print(f"✗ 认证失败: {response.status_code} - {response.text}")
                return False
                
        except ImportError:
            print("⚠ requests 库未安装，无法进行在线认证")
            return False
        except Exception as e:
            print(f"✗ 认证异常: {str(e)}")
            return False
    
    def send_vehicle_data(self, data: bytes) -> bool:
        """发送车辆数据到网关（使用 SM4 加密和 SM2 签名）
        
        参数:
            data: 业务数据（JSON 格式的字节串）
            
        返回:
            bool: 发送是否成功
        """
        if self.session_id is None or self.session_key is None:
            raise RuntimeError("请先完成注册并建立会话")
        
        if self.private_key is None or self.gateway_public_key is None:
            raise RuntimeError("缺少加密所需的密钥")
        
        print(f"\n正在发送车辆数据...")
        print(f"  - 原始数据大小: {len(data)} 字节")
        
        try:
            import requests
            
            # 使用 SM4 加密和 SM2 签名
            print(f"  - 正在使用 SM4 加密数据...")
            secure_msg = secure_data_transmission(
                plain_data=data,
                session_key=self.session_key,
                sender_private_key=self.private_key,
                receiver_public_key=self.gateway_public_key,
                sender_id=self.vehicle_id,
                receiver_id="gateway",
                session_id=self.session_id
            )
            
            print(f"  - 加密后数据大小: {len(secure_msg.encrypted_payload)} 字节")
            print(f"  - 签名长度: {len(secure_msg.signature)} 字节")
            
            # 将 SecureMessage 转换为可序列化的字典
            secure_msg_dict = {
                "header": secure_msg.header.to_dict(),
                "encrypted_payload": secure_msg.encrypted_payload.hex(),
                "signature": secure_msg.signature.hex(),
                "timestamp": secure_msg.timestamp.isoformat(),
                "nonce": secure_msg.nonce.hex()
            }
            
            # 通过 HTTP API 发送加密数据
            response = requests.post(
                f"{self.gateway_url}/api/auth/data/secure",
                params={
                    "vehicle_id": self.vehicle_id,
                    "session_id": self.session_id
                },
                json=secure_msg_dict,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ 加密数据发送成功")
                print(f"  - 车辆 ID: {result.get('vehicle_id')}")
                print(f"  - 时间戳: {result.get('timestamp')}")
                print(f"  - 签名验证: 通过")
                return True
            else:
                print(f"✗ 数据发送失败: {response.status_code} - {response.text}")
                return False
                
        except ImportError:
            print("✗ requests 库未安装，无法发送数据")
            return False
        except Exception as e:
            print(f"✗ 发送数据异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def receive_gateway_response(self, secure_msg: SecureMessage) -> Optional[bytes]:
        """接收并解密网关响应
        
        参数:
            secure_msg: 网关发送的安全报文
            
        返回:
            Optional[bytes]: 解密后的数据，如果失败则返回 None
        """
        if self.session_key is None:
            raise RuntimeError("请先完成身份认证")
        
        print(f"\n正在接收网关响应...")
        
        try:
            # 验证并解密报文（不进行 nonce 检查，因为客户端不需要防重放）
            from src.crypto.sm4 import sm4_decrypt
            from src.crypto.sm2 import sm2_verify
            
            # 验证签名
            message_data = (
                secure_msg.header.sender_id.encode('utf-8') +
                secure_msg.header.receiver_id.encode('utf-8') +
                secure_msg.encrypted_payload +
                secure_msg.timestamp.isoformat().encode('utf-8') +
                secure_msg.nonce
            )
            
            if not sm2_verify(message_data, secure_msg.signature, self.gateway_public_key):
                raise ValueError("签名验证失败")
            
            # 解密数据
            plain_data = sm4_decrypt(secure_msg.encrypted_payload, self.session_key)
            
            print(f"✓ 响应接收成功")
            print(f"  - 数据大小: {len(plain_data)} 字节")
            
            return plain_data
            
        except Exception as e:
            print(f"✗ 接收响应失败: {str(e)}")
            return None
    
    def simulate_data_collection(self) -> bytes:
        """模拟车辆数据采集（动态模拟真实行驶状态）
        
        返回:
            bytes: 模拟的车辆数据
        """
        # 更新车辆状态
        self._update_vehicle_state()
        
        # 模拟车辆传感器数据
        vehicle_data = {
            "vehicle_id": self.vehicle_id,
            "timestamp": datetime.utcnow().isoformat(),
            "state": self.state.value,
            "gps": {
                "latitude": round(self.latitude, 6),
                "longitude": round(self.longitude, 6),
                "altitude": round(50.0 + random.uniform(-5, 5), 1),
                "heading": round(self.heading, 1),
                "satellites": random.randint(8, 15)
            },
            "motion": {
                "speed": round(self.speed, 1),
                "acceleration": round(self._calculate_acceleration(), 2),
                "odometer": self.odometer,
                "trip_distance": round(self.trip_distance, 2)
            },
            "fuel": {
                "level": round(self.fuel_level, 1),
                "consumption": round(self._calculate_fuel_consumption(), 2),
                "range": round(self.fuel_level * 6, 0)  # 估算续航里程
            },
            "temperature": {
                "engine": round(self.engine_temp, 1),
                "cabin": round(self.cabin_temp, 1),
                "outside": round(20 + random.uniform(-5, 10), 1)
            },
            "battery": {
                "voltage": round(12.0 + random.uniform(0.3, 0.8), 1),
                "current": round(random.uniform(-5, 50), 1) if self.state != VehicleState.PARKED else 0
            },
            "diagnostics": {
                "engine_load": round(self._calculate_engine_load(), 1),
                "rpm": self._calculate_rpm(),
                "throttle_position": round(self._calculate_throttle(), 1)
            }
        }
        
        return json.dumps(vehicle_data, ensure_ascii=False).encode('utf-8')
    
    def _update_vehicle_state(self):
        """更新车辆动态状态"""
        # 状态转换逻辑
        if self.state == VehicleState.PARKED:
            # 10% 概率启动
            if random.random() < 0.1:
                self.state = VehicleState.IDLE
                self.engine_temp = 25.0
        
        elif self.state == VehicleState.IDLE:
            # 30% 概率开始行驶
            if random.random() < 0.3:
                self.state = VehicleState.ACCELERATING
            # 5% 概率熄火
            elif random.random() < 0.05:
                self.state = VehicleState.PARKED
                self.engine_temp = max(20, self.engine_temp - 5)
        
        elif self.state == VehicleState.ACCELERATING:
            # 加速
            self.speed = min(120, self.speed + random.uniform(5, 15))
            self.engine_temp = min(95, self.engine_temp + random.uniform(2, 5))
            
            # 达到目标速度后进入巡航
            if self.speed > 60 or random.random() < 0.3:
                self.state = VehicleState.CRUISING
        
        elif self.state == VehicleState.CRUISING:
            # 巡航状态，速度小幅波动
            self.speed = max(40, min(120, self.speed + random.uniform(-3, 3)))
            self.engine_temp = min(90, self.engine_temp + random.uniform(0, 1))
            
            # 20% 概率减速
            if random.random() < 0.2:
                self.state = VehicleState.DECELERATING
            # 10% 概率加速
            elif random.random() < 0.1:
                self.state = VehicleState.ACCELERATING
        
        elif self.state == VehicleState.DECELERATING:
            # 减速
            self.speed = max(0, self.speed - random.uniform(5, 10))
            self.engine_temp = max(60, self.engine_temp - random.uniform(1, 2))
            
            # 速度降到很低时
            if self.speed < 10:
                if random.random() < 0.5:
                    self.state = VehicleState.IDLE
                    self.speed = 0
                else:
                    self.state = VehicleState.BRAKING
        
        elif self.state == VehicleState.BRAKING:
            # 急刹车
            self.speed = max(0, self.speed - random.uniform(10, 20))
            if self.speed == 0:
                self.state = VehicleState.IDLE
        
        # 更新位置（如果在移动）
        if self.speed > 0:
            self._update_position()
        
        # 更新油耗
        if self.state != VehicleState.PARKED:
            self.fuel_level = max(0, self.fuel_level - self._calculate_fuel_consumption())
        
        # 更新车内温度（逐渐接近目标温度）
        target_cabin_temp = 22.0 if self.state != VehicleState.PARKED else 20.0
        self.cabin_temp += (target_cabin_temp - self.cabin_temp) * 0.1
    
    def _update_position(self):
        """更新 GPS 位置（模拟车辆移动）"""
        # 计算移动距离（km）
        # 假设每次更新间隔为 5 秒
        distance_km = (self.speed / 3600) * 5  # 5秒内行驶的距离
        
        # 更新里程
        self.odometer += distance_km
        self.trip_distance += distance_km
        
        # 偶尔改变方向（模拟转弯）
        if random.random() < 0.1:
            self.heading = (self.heading + random.uniform(-30, 30)) % 360
        
        # 根据方向和距离更新经纬度
        # 简化计算：1度纬度约111km，1度经度约111*cos(纬度)km
        lat_change = (distance_km / 111) * math.cos(math.radians(self.heading))
        lon_change = (distance_km / (111 * math.cos(math.radians(self.latitude)))) * math.sin(math.radians(self.heading))
        
        self.latitude += lat_change
        self.longitude += lon_change
    
    def _calculate_acceleration(self) -> float:
        """计算加速度 (m/s²)"""
        if self.state == VehicleState.ACCELERATING:
            return random.uniform(1.5, 3.0)
        elif self.state == VehicleState.BRAKING:
            return random.uniform(-5.0, -3.0)
        elif self.state == VehicleState.DECELERATING:
            return random.uniform(-2.0, -0.5)
        else:
            return random.uniform(-0.2, 0.2)
    
    def _calculate_fuel_consumption(self) -> float:
        """计算油耗（每次更新消耗的百分比）"""
        if self.state == VehicleState.PARKED:
            return 0
        elif self.state == VehicleState.IDLE:
            return 0.001
        elif self.state == VehicleState.ACCELERATING:
            return 0.01 * (self.speed / 100)
        elif self.state == VehicleState.CRUISING:
            return 0.005 * (self.speed / 100)
        else:
            return 0.002
    
    def _calculate_engine_load(self) -> float:
        """计算发动机负载百分比"""
        if self.state == VehicleState.PARKED:
            return 0
        elif self.state == VehicleState.IDLE:
            return random.uniform(5, 15)
        elif self.state == VehicleState.ACCELERATING:
            return random.uniform(60, 90)
        elif self.state == VehicleState.CRUISING:
            return random.uniform(30, 50)
        else:
            return random.uniform(10, 30)
    
    def _calculate_rpm(self) -> int:
        """计算发动机转速"""
        if self.state == VehicleState.PARKED:
            return 0
        elif self.state == VehicleState.IDLE:
            return random.randint(700, 900)
        else:
            # 简化：转速与速度成正比
            base_rpm = 800 + (self.speed * 30)
            return int(base_rpm + random.uniform(-100, 100))
    
    def _calculate_throttle(self) -> float:
        """计算油门开度百分比"""
        if self.state == VehicleState.PARKED:
            return 0
        elif self.state == VehicleState.IDLE:
            return 0
        elif self.state == VehicleState.ACCELERATING:
            return random.uniform(50, 100)
        elif self.state == VehicleState.CRUISING:
            return random.uniform(20, 40)
        elif self.state == VehicleState.BRAKING:
            return 0
        else:
            return random.uniform(5, 20)
    
    def unregister(self) -> bool:
        """注销车辆
        
        返回:
            bool: 注销是否成功
        """
        if self.session_id is None:
            return True  # 未注册，无需注销
        
        print(f"\n正在注销车辆...")
        
        try:
            import requests
            
            response = requests.post(
                f"{self.gateway_url}/api/auth/unregister",
                params={
                    "vehicle_id": self.vehicle_id,
                    "session_id": self.session_id
                },
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✓ 车辆注销成功")
                self.session_id = None
                return True
            else:
                print(f"✗ 车辆注销失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 注销异常: {str(e)}")
            return False
    
    def run_continuous_mode(self, interval: int = 5, max_iterations: int = 0):
        """运行连续模式，定期发送数据
        
        参数:
            interval: 发送间隔（秒）
            max_iterations: 最大迭代次数（0 表示无限循环）
        """
        print(f"\n{'='*60}")
        print(f"启动连续数据传输模式")
        print(f"  - 发送间隔: {interval} 秒")
        print(f"  - 最大迭代: {'无限' if max_iterations == 0 else max_iterations}")
        print(f"{'='*60}\n")
        
        iteration = 0
        try:
            while max_iterations == 0 or iteration < max_iterations:
                iteration += 1
                print(f"\n[迭代 {iteration}] {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 采集数据
                vehicle_data = self.simulate_data_collection()
                
                # 发送数据
                success = self.send_vehicle_data(vehicle_data)
                
                if success:
                    print(f"✓ 第 {iteration} 次数据传输成功")
                else:
                    print(f"✗ 第 {iteration} 次数据传输失败")
                
                # 等待下一次发送
                if max_iterations == 0 or iteration < max_iterations:
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            print(f"\n\n用户中断，共完成 {iteration} 次数据传输")
            # 优雅退出：注销车辆
            self.unregister()
        except Exception as e:
            print(f"\n\n运行异常: {str(e)}")
            # 异常退出：尝试注销车辆
            self.unregister()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="车辆客户端模拟器")
    parser.add_argument(
        "--vehicle-id",
        default=f"VIN{int(time.time()) % 1000000:06d}",
        help="车辆标识（VIN）"
    )
    parser.add_argument(
        "--gateway-host",
        default=os.getenv("GATEWAY_HOST", "localhost"),
        help="网关主机地址"
    )
    parser.add_argument(
        "--gateway-port",
        type=int,
        default=int(os.getenv("GATEWAY_PORT", "8000")),
        help="网关端口"
    )
    parser.add_argument(
        "--organization",
        default="Test Vehicle Manufacturer",
        help="组织名称"
    )
    parser.add_argument(
        "--api-token",
        default=os.getenv("API_TOKEN", "dev-token-12345"),
        help="API 认证令牌（用于证书申请）"
    )
    parser.add_argument(
        "--mode",
        choices=["once", "continuous"],
        default="once",
        help="运行模式：once（单次）或 continuous（连续）"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="连续模式下的发送间隔（秒）"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=0,
        help="连续模式下的最大迭代次数（0 表示无限）"
    )
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"车联网安全通信 - 车辆客户端模拟器")
    print(f"{'='*60}\n")
    
    # 创建客户端
    client = VehicleClient(
        vehicle_id=args.vehicle_id,
        gateway_host=args.gateway_host,
        gateway_port=args.gateway_port,
        organization=args.organization,
        api_token=args.api_token
    )
    
    # 步骤 1：生成密钥对
    client.generate_keypair()
    
    # 步骤 2：申请证书
    try:
        client.request_certificate()
    except Exception as e:
        print(f"✗ 证书申请失败: {str(e)}")
        print("提示：请确保网关服务正在运行")
        return
    
    # 步骤 3：注册为在线车辆
    print(f"\n正在注册为在线车辆...")
    try:
        import requests
        
        response = requests.post(
            f"{client.gateway_url}/api/auth/register",
            json={
                "vehicle_id": client.vehicle_id,
                "certificate_serial": client.certificate.serial_number if client.certificate else None,
                "public_key": client.public_key.hex() if client.public_key else None
            },
            headers={"Authorization": f"Bearer {client.api_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            register_data = response.json()
            client.session_id = register_data["session_id"]
            print(f"✓ 注册成功")
            print(f"  - 会话 ID: {client.session_id}")
            
            # 获取会话密钥和网关公钥
            if 'session_key' in register_data:
                client.session_key = bytes.fromhex(register_data['session_key'])
                print(f"  - 会话密钥长度: {len(client.session_key)} 字节")
            else:
                # 生成本地会话密钥
                client.session_key = generate_sm4_key(16)
                print(f"  - 本地会话密钥长度: {len(client.session_key)} 字节")
            
            if 'gateway_public_key' in register_data:
                client.gateway_public_key = bytes.fromhex(register_data['gateway_public_key'])
                print(f"  - 网关公钥长度: {len(client.gateway_public_key)} 字节")
            else:
                # 生成模拟网关公钥
                client.gateway_public_key = generate_sm2_keypair()[1]
                print(f"  - 模拟网关公钥长度: {len(client.gateway_public_key)} 字节")
        else:
            print(f"✗ 注册失败: {response.status_code} - {response.text}")
            print("使用离线模式继续...")
            # 回退到离线模式
            client.session_key = generate_sm4_key(16)
            client.session_id = f"session_{client.vehicle_id}_{int(time.time())}"
            client.gateway_public_key = generate_sm2_keypair()[1]
            
    except Exception as e:
        print(f"✗ 注册异常: {str(e)}")
        print("使用离线模式继续...")
        # 回退到离线模式
        client.session_key = generate_sm4_key(16)
        client.session_id = f"session_{client.vehicle_id}_{int(time.time())}"
        client.gateway_public_key = generate_sm2_keypair()[1]
    
    # 步骤 4：发送数据
    if args.mode == "once":
        # 单次模式
        print(f"\n{'='*60}")
        print(f"单次数据传输模式")
        print(f"{'='*60}\n")
        
        vehicle_data = client.simulate_data_collection()
        print(f"采集的车辆数据:")
        print(json.dumps(json.loads(vehicle_data.decode('utf-8')), indent=2, ensure_ascii=False))
        
        success = client.send_vehicle_data(vehicle_data)
        
        if success:
            print(f"\n✓ 数据传输完成")
        else:
            print(f"\n✗ 数据传输失败")
        
        # 注销车辆
        client.unregister()
    else:
        # 连续模式
        client.run_continuous_mode(
            interval=args.interval,
            max_iterations=args.iterations
        )
    
    print(f"\n{'='*60}")
    print(f"车辆客户端运行完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
