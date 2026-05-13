# 多客户端运行指南

## 概述

本指南介绍如何运行多个车辆客户端连接到云端的Gateway，用于测试和演示。

## 方法1：使用Python脚本（推荐）

### 安装要求

- Python 3.6+
- Docker

### 基本使用

```bash
# 进入client目录
cd client

# 启动3个客户端（默认）
python3 run_clients.py

# 启动10个客户端
python3 run_clients.py --num 10

# 启动5个客户端，每5秒发送一次数据
python3 run_clients.py --num 5 --interval 5

# 指定Gateway地址
python3 run_clients.py --num 3 --gateway 192.168.1.100 --port 8000

# 只发送一次数据（测试用）
python3 run_clients.py --num 3 --mode once
```

### 管理命令

```bash
# 查看所有客户端状态
python3 run_clients.py --status

# 查看第1个客户端的日志
python3 run_clients.py --logs 1

# 停止所有客户端
python3 run_clients.py --stop

# 删除所有客户端容器
python3 run_clients.py --remove

# 重新构建镜像
python3 run_clients.py --rebuild
```

### 完整参数

```bash
python3 run_clients.py \
  --num 10 \                    # 客户端数量
  --gateway 8.160.179.59 \      # Gateway地址
  --port 32677 \                # Gateway端口
  --mode continuous \           # 运行模式：continuous 或 once
  --interval 10 \               # 发送间隔（秒）
  --prefix CLOUD-VIN            # 车辆ID前缀
```

## 方法2：使用Bash脚本

### 基本使用

```bash
# 进入client目录
cd client

# 给脚本添加执行权限
chmod +x run-multiple-clients.sh

# 启动3个客户端（默认）
bash run-multiple-clients.sh 3

# 启动10个客户端，每5秒发送一次
bash run-multiple-clients.sh 10 --interval 5

# 指定Gateway地址
bash run-multiple-clients.sh 5 --gateway 192.168.1.100 --port 8000
```

### 管理命令

```bash
# 查看所有客户端
docker ps | grep vehicle-client

# 查看客户端日志
docker logs -f vehicle-client-1

# 停止所有客户端
docker stop $(docker ps -q --filter name=vehicle-client)

# 删除所有客户端
docker rm -f $(docker ps -aq --filter name=vehicle-client)
```

## 方法3：使用Docker Compose

### 配置文件

编辑 `docker-compose-cloud.yml`，修改Gateway地址：

```yaml
environment:
  - GATEWAY_HOST=8.160.179.59  # 修改为你的Gateway地址
  - GATEWAY_PORT=32677         # 修改为你的Gateway端口
```

### 使用方法

```bash
# 启动1个客户端
docker-compose -f docker-compose-cloud.yml up -d

# 启动10个客户端
docker-compose -f docker-compose-cloud.yml up -d --scale vehicle-client=10

# 查看日志
docker-compose -f docker-compose-cloud.yml logs -f

# 停止所有客户端
docker-compose -f docker-compose-cloud.yml down
```

## 默认配置

| 参数 | 默认值 | 说明 |
|-----|--------|------|
| Gateway地址 | 8.160.179.59 | 云端Gateway的IP地址 |
| Gateway端口 | 32677 | Gateway的NodePort端口 |
| 客户端数量 | 3 | 启动的客户端数量 |
| 运行模式 | continuous | continuous（持续发送）或 once（发送一次） |
| 发送间隔 | 10秒 | 数据发送间隔 |
| 车辆ID前缀 | CLOUD-VIN | 车辆ID前缀，后面会加编号 |

## 车辆ID命名规则

客户端会自动生成车辆ID：

```
CLOUD-VIN-001
CLOUD-VIN-002
CLOUD-VIN-003
...
CLOUD-VIN-010
```

可以通过 `--prefix` 参数自定义前缀：

```bash
python3 run_clients.py --num 5 --prefix TEST-VEHICLE
# 生成: TEST-VEHICLE-001, TEST-VEHICLE-002, ...
```

## 监控和调试

### 查看所有客户端状态

```bash
# 使用Python脚本
python3 run_clients.py --status

# 或使用Docker命令
docker ps --filter name=vehicle-client --format 'table {{.Names}}\t{{.Status}}'
```

### 查看客户端日志

```bash
# 查看第1个客户端的日志
python3 run_clients.py --logs 1

# 或使用Docker命令
docker logs -f vehicle-client-1

# 查看所有客户端的日志
docker logs -f vehicle-client-1 &
docker logs -f vehicle-client-2 &
docker logs -f vehicle-client-3 &
```

### 实时监控

```bash
# 监控所有容器的资源使用
docker stats $(docker ps -q --filter name=vehicle-client)

# 查看Gateway的审计日志
curl -X GET "http://8.160.179.59:32677/api/audit/logs?limit=20" \
  -H "Authorization: Bearer dev-token-12345"
```

## 性能测试

### 压力测试

启动大量客户端进行压力测试：

```bash
# 启动50个客户端，每5秒发送一次
python3 run_clients.py --num 50 --interval 5

# 启动100个客户端，每10秒发送一次
python3 run_clients.py --num 100 --interval 10
```

### 监控Gateway性能

```bash
# 查看Gateway Pod的资源使用
kubectl top pods -n vehicle-iot-gateway -l app=gateway

# 查看Gateway日志
kubectl logs -f deployment/gateway -n vehicle-iot-gateway

# 查看审计日志统计
curl -X GET "http://8.160.179.59:32677/api/metrics/realtime" \
  -H "Authorization: Bearer dev-token-12345"
```

## 常见问题

### Q1: 客户端无法连接到Gateway

**检查：**
1. Gateway地址和端口是否正确
2. 网络是否可达
3. Gateway是否正常运行

```bash
# 测试连接
curl http://8.160.179.59:32677/health

# 检查Gateway状态
kubectl get pods -n vehicle-iot-gateway -l app=gateway
```

### Q2: 客户端启动失败

**检查：**
1. Docker镜像是否构建成功
2. 容器日志中的错误信息

```bash
# 查看容器日志
docker logs vehicle-client-1

# 重新构建镜像
python3 run_clients.py --rebuild
```

### Q3: 如何清理所有客户端

```bash
# 使用Python脚本
python3 run_clients.py --stop
python3 run_clients.py --remove

# 或使用Docker命令
docker stop $(docker ps -q --filter name=vehicle-client)
docker rm -f $(docker ps -aq --filter name=vehicle-client)
```

### Q4: 如何修改发送的数据

编辑 `client/vehicle_client.py` 文件中的 `generate_vehicle_data()` 方法。

### Q5: 客户端占用太多资源

减少客户端数量或增加发送间隔：

```bash
# 减少到5个客户端
python3 run_clients.py --num 5

# 增加发送间隔到30秒
python3 run_clients.py --num 10 --interval 30
```

## 高级用法

### 分批启动客户端

```bash
# 第一批：启动10个客户端
python3 run_clients.py --num 10 --prefix BATCH1

# 第二批：启动10个客户端（不会覆盖第一批）
# 需要手动指定不同的容器名称
for i in {11..20}; do
    docker run -d \
        --name vehicle-client-${i} \
        --network host \
        -e GATEWAY_HOST=8.160.179.59 \
        -e GATEWAY_PORT=32677 \
        vehicle-client:latest \
        --vehicle-id BATCH2-$(printf "%03d" $i) \
        --mode continuous \
        --interval 10
done
```

### 使用环境变量

```bash
# 设置环境变量
export GATEWAY_HOST=192.168.1.100
export GATEWAY_PORT=8000

# 使用环境变量启动
python3 run_clients.py --num 5
```

### 自定义客户端行为

修改 `client/vehicle_client.py`，可以自定义：
- 数据生成逻辑
- 发送频率
- 错误处理
- 重连机制

## 总结

**推荐使用Python脚本** (`run_clients.py`)，因为它提供了：
- ✅ 简单易用的命令行界面
- ✅ 完整的管理功能（启动、停止、查看状态、查看日志）
- ✅ 灵活的配置选项
- ✅ 友好的输出格式

**快速开始：**
```bash
cd client
python3 run_clients.py --num 5
```

**查看帮助：**
```bash
python3 run_clients.py --help
```
