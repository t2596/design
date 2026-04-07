"""查看车辆动态数据示例

演示车辆数据如何随时间动态变化
"""

import sys
import os
import json
import time

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client.vehicle_client import VehicleClient


def main():
    """主函数"""
    print("\n" + "="*80)
    print("车辆动态数据演示 - 观察数据如何随时间变化")
    print("="*80 + "\n")
    
    # 创建客户端
    client = VehicleClient(
        vehicle_id="DEMO_DYNAMIC",
        gateway_host="localhost",
        gateway_port=8000
    )
    
    # 生成密钥对
    client.generate_keypair()
    
    # 创建模拟证书
    client._create_mock_certificate()
    
    print("\n" + "="*80)
    print("开始采集数据（按 Ctrl+C 停止）")
    print("="*80 + "\n")
    
    iteration = 0
    try:
        while True:
            iteration += 1
            
            # 采集数据
            vehicle_data_bytes = client.simulate_data_collection()
            vehicle_data = json.loads(vehicle_data_bytes.decode('utf-8'))
            
            # 清屏（Windows）
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(f"\n{'='*80}")
            print(f"迭代 {iteration} - {vehicle_data['timestamp']}")
            print(f"{'='*80}\n")
            
            # 显示关键信息
            print(f"🚗 车辆状态: {vehicle_data['state']}")
            print(f"📍 位置: ({vehicle_data['gps']['latitude']:.6f}, {vehicle_data['gps']['longitude']:.6f})")
            print(f"🧭 方向: {vehicle_data['gps']['heading']:.1f}°")
            print(f"🛰️  卫星: {vehicle_data['gps']['satellites']} 颗")
            print()
            
            print(f"⚡ 速度: {vehicle_data['motion']['speed']:.1f} km/h")
            print(f"📈 加速度: {vehicle_data['motion']['acceleration']:.2f} m/s²")
            print(f"🛣️  总里程: {vehicle_data['motion']['odometer']:.0f} km")
            print(f"📏 本次行程: {vehicle_data['motion']['trip_distance']:.2f} km")
            print()
            
            print(f"⛽ 油量: {vehicle_data['fuel']['level']:.1f}%")
            print(f"💧 油耗: {vehicle_data['fuel']['consumption']:.2f} L/100km")
            print(f"🎯 续航: {vehicle_data['fuel']['range']:.0f} km")
            print()
            
            print(f"🌡️  发动机温度: {vehicle_data['temperature']['engine']:.1f}°C")
            print(f"🏠 车内温度: {vehicle_data['temperature']['cabin']:.1f}°C")
            print(f"🌤️  外部温度: {vehicle_data['temperature']['outside']:.1f}°C")
            print()
            
            print(f"🔋 电池电压: {vehicle_data['battery']['voltage']:.1f}V")
            print(f"⚡ 电流: {vehicle_data['battery']['current']:.1f}A")
            print()
            
            print(f"🔧 发动机负载: {vehicle_data['diagnostics']['engine_load']:.1f}%")
            print(f"🔄 转速: {vehicle_data['diagnostics']['rpm']} RPM")
            print(f"🎚️  油门开度: {vehicle_data['diagnostics']['throttle_position']:.1f}%")
            
            print(f"\n{'='*80}")
            print("提示：观察数据如何随车辆状态变化（停车 → 怠速 → 加速 → 巡航 → 减速）")
            print(f"{'='*80}\n")
            
            # 等待 2 秒
            time.sleep(2)
            
    except KeyboardInterrupt:
        print(f"\n\n✓ 共采集 {iteration} 次数据")
        print("\n" + "="*80)
        print("演示结束")
        print("="*80 + "\n")


if __name__ == "__main__":
    main()
