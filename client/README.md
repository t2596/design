# 车辆客户端模拟器

车辆终端设备模拟器，用于测试车联网安全通信网关系统。

## 功能特性

- ✓ SM2 密钥对生成
- ✓ 证书申请与管理（通过网关 API）
- ✓ 双向身份认证（通过网关 API）
- ✓ 安全数据传输（SM4 加密 + SM2 签名）
- ✓ 车辆传感器数据模拟
- ✓ 单次和连续运行模式
- ✓ Docker 容器化部署
- ✓ 完全独立于数据库，仅通过网关 API 交互

## 架构说明

车辆客户端是一个独立的模拟器，**仅通过网关的 HTTP API 进行交互**，不直接访问数据库或 Redis：

```
┌─────────────────┐
│  车辆客户端      │
│  - 密钥生成     │
│  - 证书申请     │
│  - 数据传输     │
└────────┬────────┘
         │ HTTP API
         ↓
┌─────────────────┐
│  安全通信网关    │
│  - 证书管理     │
│  - 身份认证     │
│  - 数据转发     │
└────────┬────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌────────┐ ┌────────┐
│ 数据库  │ │ Redis  │
└────────┘ └────────┘
```

这种设计确保了：
- 客户端部署简单，无需数据库配置
- 网关作为唯一的数据访问入口
- 更好的安全隔离和权限控制

## 测试验证

车辆客户端已通过完整的单元测试验证：

```bash
# 运行客户端测试
python -m pytest tests/test_vehicle_client.py -v

# 测试结果：8 passed
# - 客户端初始化
# - 密钥对生成
# - 模拟证书创建
# - 数据采集模拟
# - 会话管理
# - 数据传输
# - 完整离线工作流
```

## 快速开始

### 本地运行

```bash
# 1. 安装依赖
pip install -r ../requirements.txt

# 2. 配置环境变量（可选）
export GATEWAY_HOST=localhost
export GATEWAY_PORT=8000
export API_KEY=test-api-key

# 3. 运行客户端（单次模式）
python vehicle_client.py --vehicle-id VIN123456789 --mode once

# 4. 运行客户端（连续模式）
python vehicle_client.py --vehicle-id VIN123456789 --mode continuous --interval 5
```

### Docker 运行

**重要**：Docker 镜像必须从项目根目录构建，因为需要访问 `src/` 和 `config/` 目录。

```bash
# 1. 从项目根目录构建镜像
cd /path/to/vehicle-iot-security-gateway  # 回到项目根目录
docker build -f client/Dockerfile -t vehicle-client:latest .

# 如果你在 client/ 目录中，先回到根目录
cd ..
docker build -f client/Dockerfile -t vehicle-client:latest .

# 2. 运行单个客户端
docker run --rm \
  --network vehicle-iot-network \
  -e GATEWAY_HOST=gateway \
  -e GATEWAY_PORT=8000 \
  vehicle-client:latest \
  --vehicle-id VIN123456789 \
  --mode continuous \
  --interval 10

# 3. 使用 docker-compose 运行多个客户端
docker-compose up -d

# 4. 查看客户端日志
docker-compose logs -f vehicle-client-1

# 5. 停止所有客户端
docker-compose down
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--vehicle-id` | 车辆标识（VIN） | 自动生成 |
| `--gateway-host` | 网关主机地址 | localhost |
| `--gateway-port` | 网关端口 | 8000 |
| `--organization` | 组织名称 | Test Vehicle Manufacturer |
| `--mode` | 运行模式（once/continuous） | once |
| `--interval` | 连续模式发送间隔（秒） | 5 |
| `--iterations` | 连续模式最大迭代次数（0=无限） | 0 |

## 运行模式

### 单次模式（once）

执行一次完整的流程：
1. 生成密钥对
2. 申请证书
3. 身份认证
4. 发送一次数据
5. 退出

```bash
python vehicle_client.py --vehicle-id VIN001 --mode once
```

### 连续模式（continuous）

持续运行，定期发送数据：
1. 生成密钥对
2. 申请证书
3. 身份认证
4. 循环发送数据（按指定间隔）
5. 按 Ctrl+C 退出

```bash
python vehicle_client.py --vehicle-id VIN001 --mode continuous --interval 10
```

## 模拟数据

客户端会模拟真实的车辆行驶状态，数据会随时间动态变化：

### 车辆状态

- **停车 (PARKED)**: 发动机关闭，所有数据静止
- **怠速 (IDLE)**: 发动机启动但未行驶，转速 700-900 RPM
- **加速 (ACCELERATING)**: 速度增加，油门开度大，发动机负载高
- **巡航 (CRUISING)**: 稳定行驶，速度 40-120 km/h
- **减速 (DECELERATING)**: 速度降低，发动机温度下降
- **刹车 (BRAKING)**: 急刹车，速度快速降低

### 动态数据示例

```json
{
  "vehicle_id": "VIN123456789",
  "timestamp": "2026-03-26T05:34:39.450307",
  "state": "加速",
  "gps": {
    "latitude": 39.904286,
    "longitude": 116.407370,
    "altitude": 52.3,
    "heading": 345.1,
    "satellites": 12
  },
  "motion": {
    "speed": 65.3,
    "acceleration": 2.5,
    "odometer": 28666,
    "trip_distance": 12.5
  },
  "fuel": {
    "level": 75.5,
    "consumption": 8.5,
    "range": 453
  },
  "temperature": {
    "engine": 85.0,
    "cabin": 22.0,
    "outside": 25.0
  },
  "battery": {
    "voltage": 12.6,
    "current": 45.2
  },
  "diagnostics": {
    "engine_load": 75.5,
    "rpm": 2500,
    "throttle_position": 65.0
  }
}
```

### 数据变化特点

- **GPS 位置**: 车辆行驶时会实际移动，模拟真实轨迹
- **速度**: 根据状态平滑变化（加速、巡航、减速）
- **发动机温度**: 从冷车 20°C 逐渐升温到 85-95°C
- **油耗**: 根据速度和状态动态计算
- **转速**: 与速度和油门开度相关
- **状态转换**: 自动在不同状态间切换，模拟真实驾驶

### 查看动态数据

运行演示脚本查看数据如何实时变化：

```bash
python examples/view_vehicle_data.py
```

这个脚本会实时显示车辆数据，你可以观察到：
- 车辆从停车到启动
- 加速过程中速度、转速、温度的变化
- GPS 位置的实际移动
- 油量的逐渐消耗

## Docker Compose 配置

`docker-compose.yml` 文件配置了 3 个车辆客户端实例：

- **vehicle-client-1**: VIN000001，每 10 秒发送一次数据
- **vehicle-client-2**: VIN000002，每 15 秒发送一次数据
- **vehicle-client-3**: VIN000003，每 20 秒发送一次数据

可以根据需要调整客户端数量和配置。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GATEWAY_HOST` | 网关主机地址 | localhost |
| `GATEWAY_PORT` | 网关端口 | 8000 |
| `API_KEY` | API 密钥（用于网关 API 调用） | test-api-key |

## 故障排查

### 证书申请失败

```
✗ 证书申请失败: Connection refused
```

**解决方案**：
- 确保网关服务正在运行
- 检查网关地址和端口配置
- 验证网络连接

### 认证失败

```
✗ 认证失败: 证书验证失败
```

**解决方案**：
- 检查证书是否有效
- 验证 CA 公钥配置
- 查看审计日志获取详细错误信息

### 数据传输失败

```
✗ 数据传输失败: 签名验证失败
```

**解决方案**：
- 检查会话密钥是否有效
- 验证网关公钥配置
- 确认会话未过期

## 性能测试

使用多个客户端进行压力测试：

```bash
# 启动 10 个客户端实例
for i in {1..10}; do
  docker run -d \
    --name vehicle-client-$i \
    --network vehicle-iot-network \
    -e GATEWAY_HOST=gateway \
    vehicle-client:latest \
    --vehicle-id VIN$(printf "%06d" $i) \
    --mode continuous \
    --interval 5
done

# 查看所有客户端状态
docker ps | grep vehicle-client

# 停止所有客户端
docker stop $(docker ps -q --filter name=vehicle-client)
docker rm $(docker ps -aq --filter name=vehicle-client)
```

## 开发说明

### 添加新的传感器数据

编辑 `vehicle_client.py` 中的 `simulate_data_collection()` 方法：

```python
def simulate_data_collection(self) -> bytes:
    vehicle_data = {
        "vehicle_id": self.vehicle_id,
        "timestamp": datetime.utcnow().isoformat(),
        # 添加新的传感器数据
        "tire_pressure": {
            "front_left": 2.3,
            "front_right": 2.3,
            "rear_left": 2.2,
            "rear_right": 2.2
        }
    }
    return json.dumps(vehicle_data, ensure_ascii=False).encode('utf-8')
```

### 自定义认证流程

修改 `authenticate_with_gateway()` 方法以实现自定义认证逻辑。

## 安全注意事项

- 私钥仅存储在内存中，不会持久化到磁盘
- 会话密钥在会话结束后自动清除
- 所有数据传输都经过 SM4 加密和 SM2 签名
- 支持防重放攻击（nonce + 时间戳验证）

## 许可证

与主项目相同
