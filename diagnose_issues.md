# 问题诊断报告

## 问题 1：客户端数据传输加密

### 当前状态
**未启用加密** ❌

### 详细说明
虽然代码中实现了完整的加密功能（`src/secure_messaging.py`），但客户端实际使用时**没有启用**：

1. **客户端发送数据**（`client/vehicle_client.py` 的 `send_vehicle_data` 方法）：
   - 直接通过 HTTP POST 发送 JSON 数据
   - 没有调用 `secure_data_transmission` 进行 SM4 加密
   - 没有使用 SM2 签名

2. **网关接收数据**（`src/api/routes/auth.py` 的 `receive_vehicle_data` 方法）：
   - 直接接收 JSON 数据
   - 没有调用 `verify_and_decrypt_message` 进行验证和解密

### 影响
- 数据在传输过程中是明文的
- 没有防重放攻击保护
- 没有数据完整性验证

### 解决方案
需要修改客户端和网关代码，启用加密传输：

1. **客户端修改**：
   ```python
   # 在 send_vehicle_data 方法中
   # 使用 secure_data_transmission 加密数据
   secure_msg = secure_data_transmission(
       plain_data=data,
       session_key=self.session_key,
       sender_private_key=self.private_key,
       receiver_public_key=self.gateway_public_key,
       sender_id=self.vehicle_id,
       receiver_id="gateway",
       session_id=self.session_id
   )
   # 发送加密后的 SecureMessage
   ```

2. **网关修改**：
   ```python
   # 在 receive_vehicle_data 方法中
   # 使用 verify_and_decrypt_message 解密数据
   plain_data = verify_and_decrypt_message(
       secure_message=secure_msg,
       session_key=session_key,
       sender_public_key=vehicle_public_key
   )
   ```

---

## 问题 2：Web 端审计日志查询失效

### 当前状态
**后端 API 已实现，但可能返回空数据** ⚠️

### 详细说明
1. **后端 API**（`src/api/routes/audit.py`）：
   - ✅ `/api/audit/logs` 端点已实现
   - ✅ `/api/audit/export` 端点已实现
   - ✅ 已在 `src/api/main.py` 中注册路由

2. **前端页面**（`web/src/pages/AuditLogs.jsx`）：
   - ✅ 页面已实现
   - ✅ API 调用已实现

3. **可能的问题**：
   - 数据库中可能没有审计日志数据
   - 审计日志功能可能没有被调用

### 诊断步骤
运行以下命令检查数据库中是否有审计日志：

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) FROM audit_logs;"
```

如果返回 0 或很少的记录，说明审计日志功能没有被正确调用。

### 解决方案
需要在关键操作中添加审计日志记录：

1. **车辆认证时**：
   ```python
   # 在 src/api/routes/auth.py 的 register_vehicle 中
   audit_logger.log_event(
       event_type=EventType.AUTHENTICATION_SUCCESS,
       vehicle_id=request.vehicle_id,
       operation_result=True,
       details="车辆注册成功"
   )
   ```

2. **证书操作时**：
   ```python
   # 在 src/api/routes/certificates.py 中
   audit_logger.log_event(
       event_type=EventType.CERTIFICATE_ISSUED,
       vehicle_id=vehicle_id,
       operation_result=True,
       details=f"证书颁发成功: {serial_number}"
   )
   ```

3. **数据加密/解密时**：
   ```python
   # 在 src/secure_messaging.py 中
   audit_logger.log_event(
       event_type=EventType.DATA_ENCRYPTED,
       vehicle_id=sender_id,
       operation_result=True,
       details="数据加密成功"
   )
   ```

---

## 问题 3：Web 端安全配置失效

### 当前状态
**后端 API 已实现，但配置未持久化** ⚠️

### 详细说明
1. **后端 API**（`src/api/routes/config.py`）：
   - ✅ `/api/config/security` GET 端点已实现
   - ✅ `/api/config/security` PUT 端点已实现
   - ✅ 已在 `src/api/main.py` 中注册路由

2. **前端页面**（`web/src/pages/SecurityConfig.jsx`）：
   - ✅ 页面已实现
   - ✅ API 调用已实现

3. **问题**：
   - 配置只保存在内存中（全局变量 `_current_policy`）
   - Gateway Pod 重启后配置会丢失
   - 配置没有实际应用到系统中

### 解决方案
1. **持久化配置到数据库**：
   ```python
   # 创建配置表
   CREATE TABLE security_policy (
       id SERIAL PRIMARY KEY,
       session_timeout INTEGER NOT NULL,
       certificate_validity INTEGER NOT NULL,
       timestamp_tolerance INTEGER NOT NULL,
       concurrent_session_strategy VARCHAR(20) NOT NULL,
       max_auth_failures INTEGER NOT NULL,
       auth_failure_lockout_duration INTEGER NOT NULL,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_by VARCHAR(64)
   );
   ```

2. **应用配置到实际功能**：
   - 在会话管理中使用 `session_timeout`
   - 在证书颁发中使用 `certificate_validity`
   - 在报文验证中使用 `timestamp_tolerance`
   - 在认证失败处理中使用 `max_auth_failures` 和 `auth_failure_lockout_duration`

---

## 测试脚本

创建以下测试脚本来验证修复：

### 1. 测试审计日志 API
```bash
#!/bin/bash
GATEWAY_URL="http://8.147.67.31:32620"
TOKEN="dev-token-12345"

echo "测试审计日志 API..."
curl -X GET "${GATEWAY_URL}/api/audit/logs" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json"
```

### 2. 测试安全配置 API
```bash
#!/bin/bash
GATEWAY_URL="http://8.147.67.31:32620"
TOKEN="dev-token-12345"

echo "获取安全配置..."
curl -X GET "${GATEWAY_URL}/api/config/security" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json"

echo ""
echo "更新安全配置..."
curl -X PUT "${GATEWAY_URL}/api/config/security" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 3600,
    "certificate_validity": 365,
    "timestamp_tolerance": 300,
    "concurrent_session_strategy": "reject_new",
    "max_auth_failures": 5,
    "auth_failure_lockout_duration": 300
  }'
```

### 3. 检查数据库审计日志
```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT event_type, vehicle_id, operation_result, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"
```

---

## 优先级建议

1. **高优先级**：启用数据传输加密（安全核心功能）
2. **中优先级**：修复审计日志功能（合规要求）
3. **低优先级**：完善安全配置持久化（运维便利性）
