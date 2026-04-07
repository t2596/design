# 车辆数据存储和显示功能实现

## 概述

实现完整的车辆数据存储、查询和 Web 界面显示功能，包括：
- GPS 位置和轨迹
- 实时速度和加速度
- 燃油和温度
- 历史数据查询

## 实现内容

### 1. 数据库层

**文件**: `db/migrations/002_vehicle_data_table.sql`（已创建）

创建 `vehicle_data` 表存储车辆传感器数据：
- GPS 数据（位置、方向、卫星数）
- 运动数据（速度、加速度、里程）
- 燃油数据（油量、油耗、续航）
- 温度数据（发动机、车内、室外）
- 电池数据（电压、电流）
- 诊断数据（负载、转速、油门）

**特性**：
- 自动索引优化查询性能
- `latest_vehicle_data` 视图获取最新数据
- 自动清理 7 天前的旧数据

### 2. 后端 API 层

需要实现以下功能：

#### 2.1 数据存储

修改网关接收车辆数据时保存到数据库。

**位置**: `src/security_gateway.py` 的 `forward_vehicle_data_to_cloud` 方法

**实现**：
```python
def save_vehicle_data(self, vehicle_id: str, data: dict, db_conn):
    """保存车辆数据到数据库"""
    try:
        query = """
            INSERT INTO vehicle_data (
                vehicle_id, timestamp, state,
                gps_latitude, gps_longitude, gps_altitude, gps_heading, gps_satellites,
                motion_speed, motion_acceleration, motion_odometer, motion_trip_distance,
                fuel_level, fuel_consumption, fuel_range,
                temp_engine, temp_cabin, temp_outside,
                battery_voltage, battery_current,
                diag_engine_load, diag_rpm, diag_throttle_position,
                raw_data
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s
            )
            ON CONFLICT (vehicle_id, timestamp) DO UPDATE SET
                received_at = CURRENT_TIMESTAMP,
                raw_data = EXCLUDED.raw_data
        """
        
        params = (
            vehicle_id,
            data.get('timestamp'),
            data.get('state'),
            data.get('gps', {}).get('latitude'),
            data.get('gps', {}).get('longitude'),
            data.get('gps', {}).get('altitude'),
            data.get('gps', {}).get('heading'),
            data.get('gps', {}).get('satellites'),
            data.get('motion', {}).get('speed'),
            data.get('motion', {}).get('acceleration'),
            data.get('motion', {}).get('odometer'),
            data.get('motion', {}).get('trip_distance'),
            data.get('fuel', {}).get('level'),
            data.get('fuel', {}).get('consumption'),
            data.get('fuel', {}).get('range'),
            data.get('temperature', {}).get('engine'),
            data.get('temperature', {}).get('cabin'),
            data.get('temperature', {}).get('outside'),
            data.get('battery', {}).get('voltage'),
            data.get('battery', {}).get('current'),
            data.get('diagnostics', {}).get('engine_load'),
            data.get('diagnostics', {}).get('rpm'),
            data.get('diagnostics', {}).get('throttle_position'),
            json.dumps(data)
        )
        
        db_conn.execute_query(query, params)
        return True
    except Exception as e:
        print(f"保存车辆数据失败: {str(e)}")
        return False
```

#### 2.2 查询 API

**文件**: `src/api/routes/vehicles.py`（需要更新）

添加以下 API 端点：

1. **GET /api/vehicles/{vehicle_id}/data/latest** - 获取最新数据
2. **GET /api/vehicles/{vehicle_id}/data/history** - 获取历史数据
3. **GET /api/vehicles/{vehicle_id}/data/track** - 获取 GPS 轨迹

**实现示例**：
```python
@router.get("/{vehicle_id}/data/latest")
async def get_latest_vehicle_data(
    vehicle_id: str,
    user: str = Depends(verify_token)
):
    """获取车辆最新数据"""
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        query = """
            SELECT * FROM latest_vehicle_data
            WHERE vehicle_id = %s
        """
        result = db_conn.execute_query(query, (vehicle_id,))
        db_conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="车辆数据不存在")
        
        return result[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{vehicle_id}/data/history")
async def get_vehicle_data_history(
    vehicle_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    user: str = Depends(verify_token)
):
    """获取车辆历史数据"""
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        query = """
            SELECT * FROM vehicle_data
            WHERE vehicle_id = %s
            AND (%s IS NULL OR timestamp >= %s)
            AND (%s IS NULL OR timestamp <= %s)
            ORDER BY timestamp DESC
            LIMIT %s
        """
        params = (vehicle_id, start_time, start_time, end_time, end_time, limit)
        result = db_conn.execute_query(query, params)
        db_conn.close()
        
        return {"data": result, "total": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 3. Web 前端层

#### 3.1 API 客户端

**文件**: `web/src/api/vehicles.js`（需要更新）

添加新的 API 调用：
```javascript
export const getVehicleLatestData = async (vehicleId) => {
  const response = await apiClient.get(`/api/vehicles/${vehicleId}/data/latest`);
  return response.data;
};

export const getVehicleDataHistory = async (vehicleId, params = {}) => {
  const response = await apiClient.get(`/api/vehicles/${vehicleId}/data/history`, {
    params
  });
  return response.data;
};

export const getVehicleTrack = async (vehicleId, params = {}) => {
  const response = await apiClient.get(`/api/vehicles/${vehicleId}/data/track`, {
    params
  });
  return response.data;
};
```

#### 3.2 车辆监控页面

**文件**: `web/src/pages/VehicleMonitor.jsx`（需要大幅更新）

添加以下功能：
1. 显示车辆列表（已有）
2. 点击车辆查看详细数据（新增）
3. 实时数据刷新（新增）
4. GPS 地图显示（新增）
5. 数据图表（新增）

**UI 结构**：
```
┌─────────────────────────────────────────┐
│ 车辆列表（左侧）                          │
├─────────────────────────────────────────┤
│ ☑ VIN001 - 在线 - 速度: 60 km/h        │
│ ☐ VIN002 - 在线 - 速度: 0 km/h         │
│ ☐ VIN003 - 离线                         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 车辆详情（右侧）                          │
├─────────────────────────────────────────┤
│ 📍 GPS: 39.9042, 116.4074              │
│ ⚡ 速度: 60 km/h                        │
│ 🌡️ 发动机温度: 85°C                    │
│ ⛽ 油量: 75%                            │
│                                         │
│ [GPS 地图]                              │
│ [速度曲线图]                            │
│ [温度曲线图]                            │
└─────────────────────────────────────────┘
```

## 部署步骤

### 步骤 1: 更新数据库

```bash
# 方法 1: 使用 psql 直接执行
psql -h <数据库地址> -U gateway_user -d vehicle_iot_gateway -f db/migrations/002_vehicle_data_table.sql

# 方法 2: 在 Kubernetes 中执行
kubectl exec -it -n vehicle-iot-gateway deployment/postgres -- \
  psql -U gateway_user -d vehicle_iot_gateway -f /path/to/002_vehicle_data_table.sql
```

### 步骤 2: 更新后端代码

需要修改的文件：
1. `src/security_gateway.py` - 添加数据保存逻辑
2. `src/api/routes/vehicles.py` - 添加查询 API

### 步骤 3: 更新前端代码

需要修改的文件：
1. `web/src/api/vehicles.js` - 添加 API 调用
2. `web/src/pages/VehicleMonitor.jsx` - 更新 UI 显示

### 步骤 4: 重新部署

```bash
# 重新构建镜像
docker build -t vehicle-iot-gateway:latest .
docker build -t vehicle-iot-gateway-web:latest web/

# 重启服务
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway
kubectl rollout restart deployment/web -n vehicle-iot-gateway
```

## 数据流程

```
车辆客户端
    ↓ (发送加密数据)
网关接收
    ↓ (解密验证)
保存到数据库 ← 新增
    ↓
Web 前端查询 ← 新增
    ↓
显示给用户 ← 新增
```

## 性能考虑

### 数据量估算

- 每辆车每 5 秒发送一次数据
- 每天每辆车：17,280 条记录
- 100 辆车 7 天：12,096,000 条记录（约 1.2GB）

### 优化措施

1. **索引优化**：已创建必要索引
2. **数据清理**：自动清理 7 天前数据
3. **查询限制**：默认最多返回 100 条
4. **视图优化**：使用 `latest_vehicle_data` 视图

## 测试验证

### 1. 测试数据保存

```bash
# 运行客户端发送数据
python client/vehicle_client.py \
  --gateway-host <网关地址> \
  --gateway-port <端口> \
  --mode continuous \
  --iterations 10

# 查询数据库验证
psql -U gateway_user -d vehicle_iot_gateway \
  -c "SELECT COUNT(*) FROM vehicle_data;"
```

### 2. 测试 API

```bash
# 获取最新数据
curl -H "Authorization: Bearer dev-token-12345" \
  http://<网关地址>/api/vehicles/VIN001/data/latest

# 获取历史数据
curl -H "Authorization: Bearer dev-token-12345" \
  "http://<网关地址>/api/vehicles/VIN001/data/history?limit=10"
```

### 3. 测试 Web 界面

访问 Web 界面，验证：
- ✅ 车辆列表显示
- ✅ 点击车辆显示详情
- ✅ 实时数据更新
- ✅ GPS 位置显示
- ✅ 数据图表显示

## 后续优化

1. **实时推送**：使用 WebSocket 推送实时数据
2. **地图集成**：集成高德/百度地图显示轨迹
3. **数据分析**：添加统计分析功能
4. **告警功能**：异常数据告警
5. **数据导出**：支持导出 CSV/Excel

## 相关文档

- [API 文档](API.md) - API 接口说明
- [数据库架构](../db/schema.sql) - 数据库设计
- [Web 开发指南](../web/README.md) - 前端开发说明

## 注意事项

1. **数据隐私**：车辆位置数据敏感，注意权限控制
2. **性能监控**：监控数据库性能，及时优化
3. **数据备份**：定期备份重要数据
4. **存储空间**：监控磁盘使用，及时清理旧数据
