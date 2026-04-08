# Web 端看不到数据诊断指南

## 问题描述

客户端显示数据上传成功，但 Web 界面看不到车辆数据。

## 诊断步骤

### 步骤 1: 确认数据已写入数据库

```bash
# 查看特定车辆的数据（替换 VIN1234 为你的车辆 ID）
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "SELECT vehicle_id, timestamp, state, motion_speed, gps_latitude, gps_longitude 
   FROM vehicle_data 
   WHERE vehicle_id='VIN1234' 
   ORDER BY timestamp DESC 
   LIMIT 5;"
```

**预期结果**: 应该看到最近的 5 条数据记录

**如果没有数据**:
- 数据没有真正写入数据库
- 检查 Gateway 日志: `kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=50`

### 步骤 2: 测试查询 API

```bash
# 方法 1: 从 Gateway Pod 内部测试
GATEWAY_POD=$(kubectl get pods -n vehicle-iot-gateway -l app=gateway -o jsonpath='{.items[0].metadata.name}')

kubectl exec -it $GATEWAY_POD -n vehicle-iot-gateway -- \
  curl -s "http://localhost:8000/api/vehicles/VIN1234/data/latest" \
  -H "Authorization: Bearer dev-token-12345"

# 方法 2: 从外部测试（如果有 NodePort 或 LoadBalancer）
curl -s "http://<gateway-external-ip>:8000/api/vehicles/VIN1234/data/latest" \
  -H "Authorization: Bearer dev-token-12345"
```

**预期结果**: 应该返回 JSON 格式的车辆数据

**如果返回 404**: 数据库中没有该车辆的数据

**如果返回 500**: API 有错误，检查 Gateway 日志

### 步骤 3: 检查 Web 前端 API 调用

打开浏览器开发者工具（F12），切换到 Network 标签页：

1. 刷新 Web 页面
2. 点击车辆查看详情
3. 查看网络请求

**检查项**:
- 是否有请求到 `/api/vehicles/{vehicle_id}/data/latest`
- 请求状态码是什么（200, 404, 500?）
- 响应内容是什么

**常见问题**:

#### 问题 A: 请求返回 404
```json
{"detail":"车辆数据不存在"}
```

**原因**: 数据库中没有该车辆的数据

**解决**: 
1. 确认车辆 ID 正确
2. 确认数据已写入数据库（步骤 1）

#### 问题 B: 请求返回 500
```json
{"detail":"获取车辆最新数据失败: ..."}
```

**原因**: API 查询数据库时出错

**解决**: 检查 Gateway 日志，查看具体错误

#### 问题 C: 请求返回 200 但数据为空
```json
{}
```

**原因**: API 返回了空对象

**解决**: 检查 API 实现，可能是数据转换问题

### 步骤 4: 检查数据库视图

```bash
# 检查 latest_vehicle_data 视图
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "SELECT * FROM latest_vehicle_data WHERE vehicle_id='VIN1234';"
```

**预期结果**: 应该返回该车辆的最新数据

**如果没有数据**: 视图可能有问题，或者数据表中确实没有数据

### 步骤 5: 检查 Web 前端代码

查看浏览器控制台（Console 标签页）是否有 JavaScript 错误。

**常见错误**:
- `Cannot read property 'gps' of undefined` - 数据结构不匹配
- `Network Error` - 无法连接到 API
- `401 Unauthorized` - 认证失败

## 快速诊断脚本

运行自动诊断脚本：

```bash
chmod +x check_data_flow.sh
./check_data_flow.sh VIN1234
```

## 常见问题和解决方案

### 问题 1: 数据库中有数据，但 API 返回 404

**可能原因**: 
- API 查询条件不正确
- 视图定义有问题

**检查 API 实现**:
```bash
# 查看 vehicles.py 中的查询逻辑
kubectl exec -it $GATEWAY_POD -n vehicle-iot-gateway -- \
  cat /app/src/api/routes/vehicles.py | grep -A 30 "get_latest_vehicle_data"
```

**临时解决**: 直接查询表而不是视图
```python
# 修改 src/api/routes/vehicles.py
query = """
    SELECT * FROM vehicle_data
    WHERE vehicle_id = %s
    ORDER BY timestamp DESC
    LIMIT 1
"""
```

### 问题 2: API 返回数据，但 Web 界面不显示

**可能原因**:
- 前端数据解析错误
- 前端组件没有正确渲染

**检查步骤**:

1. **查看浏览器控制台**
   - 打开 F12 开发者工具
   - 切换到 Console 标签
   - 查看是否有 JavaScript 错误

2. **检查 Network 请求**
   - 切换到 Network 标签
   - 找到 `/api/vehicles/{id}/data/latest` 请求
   - 查看 Response 内容是否正确

3. **检查前端代码**
   ```bash
   # 查看 VehicleMonitor 组件
   cat web/src/pages/VehicleMonitor.jsx | grep -A 10 "fetchVehicleData"
   ```

### 问题 3: 数据格式不匹配

**症状**: API 返回数据，但前端显示 "暂无车辆数据"

**原因**: 前端期望的数据结构与 API 返回的不一致

**检查数据结构**:

API 返回的数据应该是：
```json
{
  "vehicle_id": "VIN1234",
  "timestamp": "2026-03-30T06:00:00",
  "state": "巡航",
  "gps": {
    "latitude": 39.9042,
    "longitude": 116.4074,
    ...
  },
  "motion": {
    "speed": 80.5,
    ...
  },
  ...
}
```

**修复**: 确保 API 返回的数据结构与前端期望的一致

### 问题 4: 时区问题

**症状**: 数据存在但查询不到

**原因**: 时间戳时区不一致

**检查**:
```bash
# 查看数据库中的时间戳
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "SELECT vehicle_id, timestamp, NOW() as current_time FROM vehicle_data ORDER BY timestamp DESC LIMIT 5;"
```

**解决**: 确保客户端、数据库、API 使用统一的时区（建议使用 UTC）

## 完整测试流程

```bash
# 1. 清空现有数据（可选）
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "DELETE FROM vehicle_data WHERE vehicle_id='TEST_VIN';"

# 2. 运行客户端发送数据
python client/vehicle_client.py \
  --vehicle-id TEST_VIN \
  --gateway-host <gateway-host> \
  --mode once

# 3. 立即检查数据库
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "SELECT * FROM vehicle_data WHERE vehicle_id='TEST_VIN';"

# 4. 测试 API
curl -s "http://<gateway-host>:8000/api/vehicles/TEST_VIN/data/latest" \
  -H "Authorization: Bearer dev-token-12345" | python3 -m json.tool

# 5. 在 Web 界面查看
# 访问 Web UI，搜索 TEST_VIN，点击查看详情
```

## 调试技巧

### 1. 启用详细日志

在 Gateway 中添加调试日志：

```python
# src/api/routes/vehicles.py
@router.get("/{vehicle_id}/data/latest")
async def get_latest_vehicle_data(vehicle_id: str, ...):
    print(f"DEBUG: 查询车辆 {vehicle_id} 的最新数据")
    
    # ... 查询逻辑 ...
    
    print(f"DEBUG: 查询结果: {result}")
    
    # ... 返回数据 ...
```

重新部署后查看日志：
```bash
kubectl logs -n vehicle-iot-gateway -l app=gateway -f | grep DEBUG
```

### 2. 使用 PostgreSQL 日志

启用查询日志：
```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "ALTER SYSTEM SET log_statement = 'all';"

kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "SELECT pg_reload_conf();"

# 查看日志
kubectl logs -n vehicle-iot-gateway -l app=postgres --tail=50
```

### 3. 直接测试数据库连接

```python
# test_db_connection.py
from src.db.postgres import PostgreSQLConnection
from config.database import PostgreSQLConfig

db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())

query = "SELECT * FROM latest_vehicle_data WHERE vehicle_id = %s"
result = db_conn.execute_query(query, ("VIN1234",))

print(f"查询结果: {result}")

db_conn.close()
```

## 联系支持

如果问题仍未解决，请提供：

1. **数据库查询结果**:
   ```bash
   kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
     psql -U gateway_user -d gateway_db -c \
     "SELECT * FROM vehicle_data WHERE vehicle_id='VIN1234' LIMIT 5;"
   ```

2. **API 测试结果**:
   ```bash
   curl -v "http://<gateway-host>:8000/api/vehicles/VIN1234/data/latest" \
     -H "Authorization: Bearer dev-token-12345"
   ```

3. **浏览器开发者工具截图**:
   - Network 标签页的请求详情
   - Console 标签页的错误信息

4. **Gateway 日志**:
   ```bash
   kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=100
   ```
