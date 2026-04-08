# API 文档

## 概述

车联网安全通信网关提供 RESTful API 接口，用于管理证书、监控车辆状态、查询审计日志和配置安全策略。

**基础 URL**: `http://localhost:8000`

**认证方式**: HTTP Bearer Token

所有 API 请求需要在 Header 中包含认证令牌：
```
Authorization: Bearer <your-api-token>
```

## 自动生成的 API 文档

FastAPI 自动生成交互式 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API 端点

### 健康检查

#### GET /health

检查 API 服务健康状态。

**请求示例**:
```bash
curl http://localhost:8000/health
```

**响应示例**:
```json
{
  "status": "healthy"
}
```

---

### 车辆管理

#### GET /api/vehicles/online

获取当前在线车辆列表。

**请求参数**: 无

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  http://localhost:8000/api/vehicles/online
```

**响应示例**:
```json
{
  "vehicles": [
    {
      "vehicle_id": "VIN123456789",
      "connected_at": "2026-03-21T10:30:00Z",
      "session_id": "abc123...",
      "status": "ACTIVE"
    }
  ],
  "total": 1
}
```

#### GET /api/vehicles/{vehicle_id}/status

获取特定车辆的详细状态信息。

**路径参数**:
- `vehicle_id` (string): 车辆标识

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  http://localhost:8000/api/vehicles/VIN123456789/status
```

**响应示例**:
```json
{
  "vehicle_id": "VIN123456789",
  "status": "ACTIVE",
  "session_id": "abc123...",
  "connected_at": "2026-03-21T10:30:00Z",
  "last_activity": "2026-03-21T10:35:00Z",
  "certificate_serial": "CERT-001",
  "certificate_expires_at": "2027-03-21T10:30:00Z"
}
```

#### GET /api/vehicles/search

搜索车辆。

**查询参数**:
- `query` (string): 搜索关键字

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  "http://localhost:8000/api/vehicles/search?query=VIN123"
```

**响应示例**:
```json
{
  "vehicles": [
    {
      "vehicle_id": "VIN123456789",
      "status": "ACTIVE"
    }
  ],
  "total": 1
}
```

---

### 安全指标

#### GET /api/metrics/realtime

获取实时安全指标。

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  http://localhost:8000/api/metrics/realtime
```

**响应示例**:
```json
{
  "timestamp": "2026-03-21T10:35:00Z",
  "auth_success_rate": 98.5,
  "auth_failures": 15,
  "data_transfer_volume": 1048576,
  "signature_failures": 2,
  "security_exceptions": 1,
  "active_sessions": 1234,
  "cache_hit_rate": 95.2
}
```

#### GET /api/metrics/history

获取历史安全指标。

**查询参数**:
- `start_time` (string): 开始时间（ISO 8601 格式）
- `end_time` (string): 结束时间（ISO 8601 格式）

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  "http://localhost:8000/api/metrics/history?start_time=2026-03-21T00:00:00Z&end_time=2026-03-21T23:59:59Z"
```

**响应示例**:
```json
{
  "metrics": [
    {
      "timestamp": "2026-03-21T10:00:00Z",
      "auth_success_rate": 98.5,
      "auth_failures": 15,
      "data_transfer_volume": 1048576
    }
  ],
  "total": 24
}
```

---

### 证书管理

#### GET /api/certificates

获取证书列表。

**查询参数**:
- `status` (string, 可选): 证书状态（valid, expired, revoked）
- `vehicle_id` (string, 可选): 车辆标识

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  "http://localhost:8000/api/certificates?status=valid"
```

**响应示例**:
```json
{
  "certificates": [
    {
      "serial_number": "CERT-001",
      "subject": "CN=VIN123456789, O=某汽车制造商, C=CN",
      "valid_from": "2026-03-21T00:00:00Z",
      "valid_to": "2027-03-21T00:00:00Z",
      "status": "valid"
    }
  ],
  "total": 1
}
```

#### POST /api/certificates/issue

颁发新证书。

**请求体**:
```json
{
  "vehicle_id": "VIN123456789",
  "organization": "某汽车制造商",
  "country": "CN",
  "public_key": "base64_encoded_public_key"
}
```

**请求示例**:
```bash
curl -X POST -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "VIN123456789",
    "organization": "某汽车制造商",
    "country": "CN",
    "public_key": "MFkwEwYHKoZIzj0CAQYIKoEcz1UBgi0DQgAE..."
  }' \
  http://localhost:8000/api/certificates/issue
```

**响应示例**:
```json
{
  "serial_number": "CERT-001",
  "version": 3,
  "issuer": "CN=Vehicle IoT CA, O=Security Gateway, C=CN",
  "subject": "CN=VIN123456789, O=某汽车制造商, C=CN",
  "valid_from": "2026-03-26T00:00:00",
  "valid_to": "2027-03-26T00:00:00",
  "public_key": "b0668ec547a5232f2eaa6a47dd3dc97e...",
  "signature": "3045022100...",
  "signature_algorithm": "SM2",
  "extensions": {
    "keyUsage": ["digitalSignature", "keyEncipherment"],
    "extendedKeyUsage": ["clientAuth"]
  },
  "message": "证书颁发成功，序列号: CERT-001"
}
```

#### POST /api/certificates/revoke

撤销证书。

**请求体**:
```json
{
  "serial_number": "CERT-001",
  "reason": "密钥泄露"
}
```

**请求示例**:
```bash
curl -X POST -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "serial_number": "CERT-001",
    "reason": "密钥泄露"
  }' \
  http://localhost:8000/api/certificates/revoke
```

**响应示例**:
```json
{
  "success": true,
  "message": "证书已撤销",
  "revoked_at": "2026-03-21T10:35:00Z"
}
```

#### GET /api/certificates/crl

获取证书撤销列表。

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  http://localhost:8000/api/certificates/crl
```

**响应示例**:
```json
{
  "revoked_certificates": [
    {
      "serial_number": "CERT-001",
      "revoked_at": "2026-03-21T10:35:00Z",
      "reason": "密钥泄露"
    }
  ],
  "total": 1,
  "last_updated": "2026-03-21T10:35:00Z"
}
```

---

### 审计日志

#### GET /api/audit/logs

查询审计日志。

**查询参数**:
- `start_time` (string, 可选): 开始时间（ISO 8601 格式）
- `end_time` (string, 可选): 结束时间（ISO 8601 格式）
- `vehicle_id` (string, 可选): 车辆标识
- `event_type` (string, 可选): 事件类型
- `operation_result` (boolean, 可选): 操作结果
- `limit` (integer, 可选): 返回数量限制（默认: 100）
- `offset` (integer, 可选): 偏移量（默认: 0）

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  "http://localhost:8000/api/audit/logs?vehicle_id=VIN123456789&limit=10"
```

**响应示例**:
```json
{
  "logs": [
    {
      "log_id": "LOG-001",
      "timestamp": "2026-03-21T10:35:00Z",
      "event_type": "AUTHENTICATION_SUCCESS",
      "vehicle_id": "VIN123456789",
      "operation_result": true,
      "details": "双向认证成功",
      "ip_address": "192.168.1.100"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

#### GET /api/audit/export

导出审计报告。

**查询参数**:
- `start_time` (string): 开始时间（ISO 8601 格式）
- `end_time` (string): 结束时间（ISO 8601 格式）
- `format` (string, 可选): 导出格式（json, csv）

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  "http://localhost:8000/api/audit/export?start_time=2026-03-01T00:00:00Z&end_time=2026-03-31T23:59:59Z&format=json" \
  -o audit_report.json
```

**响应**: 下载审计报告文件

---

### 配置管理

#### GET /api/config/security

获取当前安全策略配置。

**请求示例**:
```bash
curl -H "Authorization: Bearer your-token" \
  http://localhost:8000/api/config/security
```

**响应示例**:
```json
{
  "session_timeout": 3600,
  "certificate_validity_period": 31536000,
  "timestamp_tolerance": 300,
  "concurrent_session_policy": "reject_new",
  "cache_size": 10000,
  "cache_ttl": 300
}
```

#### PUT /api/config/security

更新安全策略配置。

**请求体**:
```json
{
  "session_timeout": 7200,
  "timestamp_tolerance": 600
}
```

**请求示例**:
```bash
curl -X PUT -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 7200,
    "timestamp_tolerance": 600
  }' \
  http://localhost:8000/api/config/security
```

**响应示例**:
```json
{
  "success": true,
  "message": "安全策略已更新",
  "updated_at": "2026-03-21T10:35:00Z"
}
```

---

## 错误响应

所有 API 错误响应遵循统一格式：

```json
{
  "detail": "错误描述信息"
}
```

### HTTP 状态码

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未授权（缺少或无效的认证令牌）
- `403 Forbidden`: 禁止访问
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

## 使用示例

### Python 示例

```python
import requests

# API 基础 URL
BASE_URL = "http://localhost:8000"
API_TOKEN = "your-api-token"

# 设置认证头
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# 获取在线车辆
response = requests.get(f"{BASE_URL}/api/vehicles/online", headers=headers)
vehicles = response.json()
print(f"在线车辆数: {vehicles['total']}")

# 颁发证书
cert_request = {
    "vehicle_id": "VIN123456789",
    "organization": "某汽车制造商",
    "country": "CN",
    "public_key": "MFkwEwYHKoZIzj0CAQYIKoEcz1UBgi0DQgAE..."
}
response = requests.post(
    f"{BASE_URL}/api/certificates/issue",
    headers=headers,
    json=cert_request
)
certificate = response.json()
print(f"证书序列号: {certificate['serial_number']}")

# 查询审计日志
params = {
    "vehicle_id": "VIN123456789",
    "limit": 10
}
response = requests.get(
    f"{BASE_URL}/api/audit/logs",
    headers=headers,
    params=params
)
logs = response.json()
print(f"日志条数: {logs['total']}")
```

### JavaScript 示例

```javascript
const BASE_URL = 'http://localhost:8000';
const API_TOKEN = 'your-api-token';

// 设置认证头
const headers = {
  'Authorization': `Bearer ${API_TOKEN}`,
  'Content-Type': 'application/json'
};

// 获取在线车辆
async function getOnlineVehicles() {
  const response = await fetch(`${BASE_URL}/api/vehicles/online`, {
    headers: headers
  });
  const data = await response.json();
  console.log(`在线车辆数: ${data.total}`);
  return data;
}

// 颁发证书
async function issueCertificate(vehicleId, organization, publicKey) {
  const response = await fetch(`${BASE_URL}/api/certificates/issue`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({
      vehicle_id: vehicleId,
      organization: organization,
      country: 'CN',
      public_key: publicKey
    })
  });
  const data = await response.json();
  console.log(`证书序列号: ${data.serial_number}`);
  return data;
}

// 查询审计日志
async function getAuditLogs(vehicleId, limit = 10) {
  const params = new URLSearchParams({
    vehicle_id: vehicleId,
    limit: limit
  });
  const response = await fetch(`${BASE_URL}/api/audit/logs?${params}`, {
    headers: headers
  });
  const data = await response.json();
  console.log(`日志条数: ${data.total}`);
  return data;
}
```

### cURL 示例

```bash
# 设置 API Token
export API_TOKEN="your-api-token"

# 获取在线车辆
curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost:8000/api/vehicles/online

# 获取实时指标
curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost:8000/api/metrics/realtime

# 颁发证书
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "VIN123456789",
    "organization": "某汽车制造商",
    "country": "CN",
    "public_key": "MFkwEwYHKoZIzj0CAQYIKoEcz1UBgi0DQgAE..."
  }' \
  http://localhost:8000/api/certificates/issue

# 撤销证书
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "serial_number": "CERT-001",
    "reason": "密钥泄露"
  }' \
  http://localhost:8000/api/certificates/revoke

# 查询审计日志
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/audit/logs?vehicle_id=VIN123456789&limit=10"

# 导出审计报告
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/audit/export?start_time=2026-03-01T00:00:00Z&end_time=2026-03-31T23:59:59Z" \
  -o audit_report.json

# 获取安全配置
curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost:8000/api/config/security

# 更新安全配置
curl -X PUT -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 7200,
    "timestamp_tolerance": 600
  }' \
  http://localhost:8000/api/config/security
```

## 速率限制

为防止 API 滥用，实施以下速率限制：

- 认证端点: 10 请求/分钟/IP
- 查询端点: 100 请求/分钟/IP
- 写入端点: 20 请求/分钟/IP

超过限制将返回 `429 Too Many Requests` 错误。

## WebSocket 支持（未来版本）

计划支持 WebSocket 实时推送：
- 车辆状态变化通知
- 安全告警实时推送
- 指标实时更新

## API 版本控制

当前版本: v1.0.0

未来版本将通过 URL 路径区分：
- v1: `/api/v1/...`
- v2: `/api/v2/...`

## 更多信息

- 完整的交互式文档: http://localhost:8000/docs
- OpenAPI 规范: http://localhost:8000/openapi.json
