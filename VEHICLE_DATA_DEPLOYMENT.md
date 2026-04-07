# 车辆数据功能部署指南

## 更新内容

已完成车辆数据存储和显示功能的实现：

1. **客户端更新** (`client/vehicle_client.py`)
   - 修改 `send_vehicle_data()` 方法，通过 HTTP API 发送数据
   - 调用 `/api/auth/data` 端点保存数据到数据库

2. **后端 API** (`src/api/routes/auth.py`)
   - 已添加 POST `/api/auth/data` 端点接收车辆数据
   - 验证会话、更新心跳、保存数据到 PostgreSQL

3. **数据库** (`deployment/kubernetes/postgres-init-configmap.yaml`)
   - 已包含 vehicle_data 表结构
   - 包含索引和视图

## 部署步骤

### 1. 重新部署 PostgreSQL（如果需要）

如果 PostgreSQL 已经运行但没有 vehicle_data 表：

```bash
# 删除现有 PostgreSQL 部署
kubectl delete -f deployment/kubernetes/postgres-deployment.yaml

# 更新 ConfigMap
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml

# 重新部署 PostgreSQL
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml

# 等待 Pod 就绪
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=120s
```

### 2. 重新构建并部署 Gateway

```bash
# 构建新的 Gateway 镜像
docker build -t vehicle-iot-gateway:latest .

# 如果使用远程仓库，推送镜像
# docker tag vehicle-iot-gateway:latest your-registry/vehicle-iot-gateway:latest
# docker push your-registry/vehicle-iot-gateway:latest

# 重启 Gateway 部署
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 等待部署完成
kubectl rollout status deployment/gateway -n vehicle-iot-gateway
```

### 3. 重新构建并部署 Client

```bash
# 从项目根目录构建 Client 镜像
docker build -f client/Dockerfile -t vehicle-client:latest .

# 如果使用远程仓库，推送镜像
# docker tag vehicle-client:latest your-registry/vehicle-client:latest
# docker push your-registry/vehicle-client:latest
```

### 4. 运行 Client

```bash
# 使用 Docker 运行
docker run --rm \
  -e GATEWAY_HOST=<gateway-service-ip> \
  -e GATEWAY_PORT=8000 \
  -e API_TOKEN=dev-token-12345 \
  vehicle-client:latest \
  --vehicle-id VIN123456789 \
  --mode continuous \
  --interval 10

# 或者使用 Python 直接运行
cd client
python vehicle_client.py \
  --vehicle-id VIN123456789 \
  --gateway-host <gateway-host> \
  --gateway-port 8000 \
  --mode continuous \
  --interval 10
```

### 5. 验证数据流

1. **检查客户端输出**：应该看到 "✓ 数据发送成功"
2. **检查 Web 界面**：访问 Web UI，点击在线车辆，应该能看到实时数据
3. **检查数据库**：

```bash
# 进入 PostgreSQL Pod
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- psql -U gateway_user -d gateway_db

# 查询车辆数据
SELECT vehicle_id, timestamp, state, motion_speed, gps_latitude, gps_longitude 
FROM vehicle_data 
ORDER BY timestamp DESC 
LIMIT 10;

# 查看最新数据
SELECT * FROM latest_vehicle_data;
```

## 故障排查

### 客户端显示 "✗ 数据发送失败"

1. 检查 Gateway 服务是否运行：
```bash
kubectl get pods -n vehicle-iot-gateway -l app=gateway
kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=50
```

2. 检查网络连接：
```bash
# 测试 Gateway API
curl http://<gateway-host>:8000/health
```

### Web 界面不显示数据

1. 检查浏览器控制台是否有错误
2. 检查 Gateway 日志：
```bash
kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=100 | grep "auth/data"
```

3. 检查数据库是否有数据：
```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c "SELECT COUNT(*) FROM vehicle_data;"
```

### 数据库连接失败

1. 检查 PostgreSQL 是否运行：
```bash
kubectl get pods -n vehicle-iot-gateway -l app=postgres
```

2. 检查 Gateway 环境变量：
```bash
kubectl describe deployment gateway -n vehicle-iot-gateway | grep -A 10 "Environment:"
```

## 快速重新部署所有服务

```bash
# 从项目根目录执行
cd deployment/kubernetes

# 重新部署所有服务
./deploy-all.sh

# 等待所有服务就绪
kubectl wait --for=condition=ready pod --all -n vehicle-iot-gateway --timeout=300s
```

## 测试完整流程

```bash
# 1. 运行客户端（连续模式，10秒间隔）
python client/vehicle_client.py \
  --vehicle-id TEST001 \
  --gateway-host localhost \
  --mode continuous \
  --interval 10

# 2. 打开 Web 界面
# 访问 http://<web-service-ip>:3000

# 3. 在 Web 界面中：
#    - 查看在线车辆列表（应该看到 TEST001）
#    - 点击车辆查看详细数据
#    - 观察数据实时更新（每10秒）
```
