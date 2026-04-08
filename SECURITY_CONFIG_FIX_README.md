# 安全配置功能修复指南

## 快速开始

问题3（Web端安全配置失效）已修复。按照以下步骤部署和验证修复。

## 📋 修复内容

- ✅ 配置持久化到数据库（不再丢失）
- ✅ 配置实际应用到系统功能
- ✅ 实现认证失败锁定功能
- ✅ 支持会话超时控制
- ✅ 支持证书有效期控制
- ✅ 提供完整的测试工具

## 🚀 部署修复

### 步骤1：应用数据库迁移（必须先执行）

```bash
bash apply_security_policy_migration.sh
```

或手动执行：

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway < db/migrations/003_security_policy_table.sql
```

### 步骤2：验证数据库表

```bash
# 检查表是否创建
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt security_policy"

# 检查默认配置
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM security_policy;"
```

### 步骤3：重新部署Gateway

```bash
# 重新构建镜像
docker build -t vehicle-iot-gateway:latest .

# 重启Gateway
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 等待就绪
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s
```

## 🧪 测试验证

### 测试1：配置持久化功能

```bash
bash test_security_config_api.sh
```

预期结果：
- ✅ 能够获取当前配置
- ✅ 能够更新配置
- ✅ 更新后的配置能够正确读取
- ✅ 数据库中有配置记录

### 测试2：认证失败锁定功能

```bash
python3 test_auth_failure_lockout.py
```

预期结果：
- ✅ 认证失败次数正确记录
- ✅ 达到阈值后车辆被锁定
- ✅ 锁定期间拒绝认证
- ✅ 锁定期过后可以再次认证

### 测试3：Pod重启后配置保持

```bash
# 1. 更新配置
curl -X PUT "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 7200,
    "certificate_validity": 180,
    "timestamp_tolerance": 600,
    "concurrent_session_strategy": "terminate_old",
    "max_auth_failures": 3,
    "auth_failure_lockout_duration": 600
  }'

# 2. 重启Pod
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s

# 3. 再次获取配置（应该保持更新后的值）
curl -X GET "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" | jq '.'
```

## 📊 配置参数说明

| 参数 | 说明 | 默认值 | 范围 |
|-----|------|--------|------|
| session_timeout | 会话超时时间（秒） | 86400 (24小时) | 300-604800 |
| certificate_validity | 证书有效期（天） | 365 (1年) | 30-1825 |
| timestamp_tolerance | 时间戳容差（秒） | 300 (5分钟) | 60-600 |
| concurrent_session_strategy | 并发会话策略 | reject_new | reject_new/terminate_old |
| max_auth_failures | 最大认证失败次数 | 5 | 3-10 |
| auth_failure_lockout_duration | 认证失败锁定时长（秒） | 300 (5分钟) | 60-3600 |

## 🔍 API使用示例

### 获取当前配置

```bash
curl -X GET "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json"
```

响应示例：
```json
{
  "policy": {
    "session_timeout": 86400,
    "certificate_validity": 365,
    "timestamp_tolerance": 300,
    "concurrent_session_strategy": "reject_new",
    "max_auth_failures": 5,
    "auth_failure_lockout_duration": 300
  },
  "message": "成功获取安全策略"
}
```

### 更新配置

```bash
curl -X PUT "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 7200,
    "certificate_validity": 180,
    "timestamp_tolerance": 600,
    "concurrent_session_strategy": "terminate_old",
    "max_auth_failures": 3,
    "auth_failure_lockout_duration": 600
  }'
```

## 💾 数据库操作

### 查看当前配置

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM security_policy ORDER BY updated_at DESC LIMIT 1;"
```

### 查看配置历史

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT id, session_timeout, certificate_validity, updated_at, updated_by 
   FROM security_policy 
   ORDER BY updated_at DESC;"
```

### 查看认证失败记录

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM auth_failure_records;"
```

### 查看被锁定的车辆

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT vehicle_id, failure_count, locked_until 
   FROM auth_failure_records 
   WHERE locked_until > NOW();"
```

### 手动解锁车辆

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "DELETE FROM auth_failure_records WHERE vehicle_id = 'VIN_XXX';"
```

## ✅ 验证清单

完成以下检查以确认修复成功：

- [ ] 数据库表 `security_policy` 创建成功
- [ ] 数据库表 `auth_failure_records` 创建成功
- [ ] 默认配置插入成功
- [ ] Gateway Pod成功重启
- [ ] 能够获取安全配置
- [ ] 能够更新安全配置
- [ ] 配置持久化到数据库
- [ ] Pod重启后配置不丢失
- [ ] 会话超时配置生效
- [ ] 证书有效期配置生效
- [ ] 认证失败锁定功能正常
- [ ] 锁定期过后可以再次认证

## 📁 相关文件

| 文件 | 说明 |
|-----|------|
| `db/migrations/003_security_policy_table.sql` | 数据库迁移脚本 |
| `src/security_policy_manager.py` | 安全策略管理器（新增） |
| `src/api/routes/config.py` | 配置API（已修改） |
| `src/api/routes/auth.py` | 认证API（已修改） |
| `src/api/routes/certificates.py` | 证书API（已修改） |
| `src/certificate_manager.py` | 证书管理器（已修改） |
| `apply_security_policy_migration.sh` | 数据库迁移脚本 |
| `test_security_config_api.sh` | API测试脚本 |
| `test_auth_failure_lockout.py` | 认证失败锁定测试脚本 |
| `docs/SECURITY_CONFIG_FIX.md` | 详细修复文档 |
| `PROBLEM_3_SOLUTION_SUMMARY.md` | 解决方案总结 |

## 🐛 问题排查

### 问题1：数据库迁移失败

**症状：** 执行迁移脚本时报错

**解决方案：**
```bash
# 检查PostgreSQL是否运行
kubectl get pods -n vehicle-iot-gateway | grep postgres

# 查看PostgreSQL日志
kubectl logs deployment/postgres -n vehicle-iot-gateway

# 手动连接数据库测试
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway
```

### 问题2：配置更新后不生效

**症状：** 更新配置后，系统仍使用旧配置

**解决方案：**
```bash
# 1. 检查数据库中的配置
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM security_policy ORDER BY updated_at DESC LIMIT 1;"

# 2. 重启Gateway清除缓存
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 3. 查看Gateway日志
kubectl logs -f deployment/gateway -n vehicle-iot-gateway
```

### 问题3：认证失败锁定不工作

**症状：** 多次认证失败后仍可以认证

**解决方案：**
```bash
# 1. 检查认证失败记录表
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM auth_failure_records;"

# 2. 检查安全策略配置
curl -X GET "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345"

# 3. 查看Gateway日志中的认证相关信息
kubectl logs deployment/gateway -n vehicle-iot-gateway | grep -i "auth"
```

## 📚 更多信息

- 详细修复说明：`docs/SECURITY_CONFIG_FIX.md`
- 解决方案总结：`PROBLEM_3_SOLUTION_SUMMARY.md`
- 原始问题诊断：`diagnose_issues.md`

## 💡 使用建议

1. **生产环境配置**：
   - session_timeout: 3600-7200秒（1-2小时）
   - certificate_validity: 365天（1年）
   - max_auth_failures: 5次
   - auth_failure_lockout_duration: 300-600秒（5-10分钟）

2. **测试环境配置**：
   - session_timeout: 300-600秒（5-10分钟）
   - certificate_validity: 30-90天
   - max_auth_failures: 3次
   - auth_failure_lockout_duration: 60秒（1分钟）

3. **高安全环境配置**：
   - session_timeout: 1800秒（30分钟）
   - certificate_validity: 90-180天
   - max_auth_failures: 3次
   - auth_failure_lockout_duration: 600-1800秒（10-30分钟）

## 🎯 快速验证命令

如果时间有限，可以运行以下快速验证命令：

```bash
# 1. 应用数据库迁移
bash apply_security_policy_migration.sh

# 2. 重新部署
docker build -t vehicle-iot-gateway:latest .
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 3. 测试配置API
curl -X GET "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" | jq '.'

# 4. 检查数据库
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) FROM security_policy;"

# 5. 如果以上都成功，问题3已修复 ✓
```

---

**修复完成时间：** 2024年
**修复版本：** v1.0
**验证需求：** 16.1, 16.2, 16.3, 16.4, 16.5, 16.6
