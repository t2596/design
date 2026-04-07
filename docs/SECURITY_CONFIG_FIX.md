# 问题3修复：Web端安全配置失效

## 问题描述

根据 `diagnose_issues.md` 中的问题3，Web端安全配置功能虽然后端API已实现，但存在以下问题：

1. 配置只保存在内存中（全局变量 `_current_policy`）
2. Gateway Pod 重启后配置会丢失
3. 配置没有实际应用到系统功能中

## 修复内容

### 1. 创建数据库表用于持久化配置

新增文件：`db/migrations/003_security_policy_table.sql`

创建了两个表：

#### security_policy 表
存储安全策略配置，包括：
- `session_timeout`: 会话超时时间（秒）
- `certificate_validity`: 证书有效期（天）
- `timestamp_tolerance`: 时间戳容差（秒）
- `concurrent_session_strategy`: 并发会话策略
- `max_auth_failures`: 最大认证失败次数
- `auth_failure_lockout_duration`: 认证失败锁定时长（秒）
- `updated_at`: 更新时间
- `updated_by`: 更新者

#### auth_failure_records 表
记录认证失败信息，用于实现认证失败锁定功能：
- `vehicle_id`: 车辆标识
- `failure_count`: 失败次数
- `first_failure_at`: 首次失败时间
- `last_failure_at`: 最后失败时间
- `locked_until`: 锁定截止时间

### 2. 创建安全策略管理器

新增文件：`src/security_policy_manager.py`

提供以下功能：

#### SecurityPolicy 数据类
- 封装安全策略配置
- 提供 `to_dict()` 和 `from_dict()` 方法

#### SecurityPolicyManager 类
- `get_policy()`: 从数据库加载安全策略（带缓存）
- `update_policy()`: 更新安全策略到数据库
- `record_auth_failure()`: 记录认证失败
- `reset_auth_failures()`: 重置认证失败记录
- `is_vehicle_locked()`: 检查车辆是否被锁定
- `get_session_timeout()`: 获取会话超时配置
- `get_certificate_validity()`: 获取证书有效期配置
- `get_timestamp_tolerance()`: 获取时间戳容差配置
- `get_concurrent_session_strategy()`: 获取并发会话策略

### 3. 修改配置API

修改文件：`src/api/routes/config.py`

关键改进：

```python
# 从数据库加载配置
@router.get("/security")
async def get_security_policy():
    db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
    policy_manager = SecurityPolicyManager(db_conn)
    policy_model = policy_manager.get_policy()
    # 返回配置
    db_conn.close()

# 保存配置到数据库
@router.put("/security")
async def update_security_policy(policy: SecurityPolicy):
    db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
    policy_manager = SecurityPolicyManager(db_conn)
    success = policy_manager.update_policy(policy_model, updated_by=user)
    db_conn.close()
```

### 4. 应用配置到系统功能

#### 4.1 会话管理（src/api/routes/auth.py）

```python
# 获取会话超时配置
policy_manager = SecurityPolicyManager(db_conn)
session_timeout = policy_manager.get_session_timeout()

# 使用配置的超时时间保存会话
redis_conn.set(session_key, session_data, ex=session_timeout)
```

#### 4.2 认证失败锁定（src/api/routes/auth.py）

```python
# 检查车辆是否被锁定
if policy_manager.is_vehicle_locked(vehicle_id):
    raise HTTPException(status_code=403, detail="车辆被锁定")

# 认证成功时重置失败记录
policy_manager.reset_auth_failures(vehicle_id)

# 认证失败时记录
should_lock = policy_manager.record_auth_failure(vehicle_id)
```

#### 4.3 证书有效期（src/api/routes/certificates.py）

```python
# 获取证书有效期配置
policy_manager = SecurityPolicyManager(db_conn)
certificate_validity_days = policy_manager.get_certificate_validity()

# 使用配置的有效期颁发证书
certificate = issue_certificate(
    subject_info,
    public_key,
    ca_private_key,
    ca_public_key,
    db_conn,
    validity_days=certificate_validity_days
)
```

#### 4.4 证书颁发函数（src/certificate_manager.py）

```python
def issue_certificate(
    ...,
    validity_days: int = 365  # 新增参数
) -> Certificate:
    # 使用配置的有效期
    valid_to = valid_from + timedelta(days=validity_days)
```

## 部署步骤

### 步骤1：应用数据库迁移

```bash
# 使用脚本
bash apply_security_policy_migration.sh

# 或手动执行
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

## 测试验证

### 测试1：配置持久化

```bash
bash test_security_config_api.sh
```

验证要点：
- ✅ 能够获取当前配置
- ✅ 能够更新配置
- ✅ 更新后的配置能够正确读取
- ✅ 数据库中有配置记录
- ✅ Pod重启后配置不丢失

### 测试2：认证失败锁定

```bash
python3 test_auth_failure_lockout.py
```

验证要点：
- ✅ 认证失败次数正确记录
- ✅ 达到阈值后车辆被锁定
- ✅ 锁定期间拒绝认证
- ✅ 锁定期过后可以再次认证

### 测试3：会话超时

```bash
# 1. 设置较短的会话超时（例如60秒）
curl -X PUT "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 60,
    "certificate_validity": 365,
    "timestamp_tolerance": 300,
    "concurrent_session_strategy": "reject_new",
    "max_auth_failures": 5,
    "auth_failure_lockout_duration": 300
  }'

# 2. 注册一个车辆
curl -X POST "http://8.147.67.31:32620/api/auth/register" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "VIN_TIMEOUT_TEST",
    "public_key": "'$(printf '0%.0s' {1..128})'"
  }'

# 3. 等待60秒后检查会话是否过期
sleep 60

# 4. 尝试发送数据（应该失败，会话已过期）
curl -X POST "http://8.147.67.31:32620/api/auth/data?vehicle_id=VIN_TIMEOUT_TEST&session_id=xxx" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### 测试4：证书有效期

```bash
# 1. 设置较短的证书有效期（例如30天）
curl -X PUT "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 86400,
    "certificate_validity": 30,
    "timestamp_tolerance": 300,
    "concurrent_session_strategy": "reject_new",
    "max_auth_failures": 5,
    "auth_failure_lockout_duration": 300
  }'

# 2. 颁发证书
curl -X POST "http://8.147.67.31:32620/api/certificates/issue" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "VIN_CERT_TEST",
    "organization": "Test Org",
    "country": "CN",
    "public_key": "'$(printf '0%.0s' {1..128})'"
  }'

# 3. 检查证书有效期（应该是30天）
```

## 配置参数说明

### session_timeout（会话超时时间）
- 单位：秒
- 范围：300 - 604800（5分钟 - 7天）
- 默认：86400（24小时）
- 作用：控制车辆会话在Redis中的过期时间

### certificate_validity（证书有效期）
- 单位：天
- 范围：30 - 1825（1个月 - 5年）
- 默认：365（1年）
- 作用：控制颁发证书的有效期

### timestamp_tolerance（时间戳容差）
- 单位：秒
- 范围：60 - 600（1分钟 - 10分钟）
- 默认：300（5分钟）
- 作用：验证报文时允许的时间戳偏差

### concurrent_session_strategy（并发会话策略）
- 可选值：`reject_new` 或 `terminate_old`
- 默认：`reject_new`
- 作用：
  - `reject_new`: 拒绝新会话，保留现有会话
  - `terminate_old`: 终止旧会话，接受新会话

### max_auth_failures（最大认证失败次数）
- 单位：次
- 范围：3 - 10
- 默认：5
- 作用：达到此次数后锁定车辆

### auth_failure_lockout_duration（认证失败锁定时长）
- 单位：秒
- 范围：60 - 3600（1分钟 - 1小时）
- 默认：300（5分钟）
- 作用：车辆被锁定的时长

## API端点

### GET /api/config/security
获取当前安全策略配置

**响应示例：**
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

### PUT /api/config/security
更新安全策略配置

**请求示例：**
```json
{
  "session_timeout": 7200,
  "certificate_validity": 180,
  "timestamp_tolerance": 600,
  "concurrent_session_strategy": "terminate_old",
  "max_auth_failures": 3,
  "auth_failure_lockout_duration": 600
}
```

**响应示例：**
```json
{
  "policy": {
    "session_timeout": 7200,
    "certificate_validity": 180,
    "timestamp_tolerance": 600,
    "concurrent_session_strategy": "terminate_old",
    "max_auth_failures": 3,
    "auth_failure_lockout_duration": 600
  },
  "message": "安全策略更新成功并已持久化，立即生效"
}
```

## 数据库查询

### 查看当前配置
```sql
SELECT * FROM security_policy ORDER BY updated_at DESC LIMIT 1;
```

### 查看配置历史
```sql
SELECT * FROM security_policy ORDER BY updated_at DESC;
```

### 查看认证失败记录
```sql
SELECT * FROM auth_failure_records;
```

### 查看被锁定的车辆
```sql
SELECT vehicle_id, failure_count, locked_until 
FROM auth_failure_records 
WHERE locked_until > NOW();
```

### 手动解锁车辆
```sql
DELETE FROM auth_failure_records WHERE vehicle_id = 'VIN_XXX';
```

## 相关文件

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

## 验证需求

此修复满足以下需求：

- **需求 16.1**：查询安全策略配置
- **需求 16.2**：更新会话超时配置
- **需求 16.3**：更新证书有效期配置
- **需求 16.4**：更新时间戳容差配置
- **需求 16.5**：更新并发会话策略
- **需求 16.6**：更新认证失败锁定配置

## 注意事项

1. **配置缓存**：安全策略管理器使用60秒缓存，减少数据库查询

2. **配置历史**：每次更新都会在数据库中插入新记录，保留配置历史

3. **立即生效**：配置更新后立即生效（通过缓存失效机制）

4. **认证失败重置**：认证成功后会自动重置失败记录

5. **锁定时间**：锁定时间从最后一次失败开始计算

## 后续优化建议

1. **配置版本管理**：实现配置回滚功能

2. **配置审计**：记录配置变更的审计日志

3. **配置验证**：添加更严格的配置验证规则

4. **配置通知**：配置变更时通知相关系统

5. **动态配置**：支持不重启服务动态加载配置

6. **配置导入导出**：支持配置的批量导入导出

## 问题排查

### 问题1：配置更新后不生效

**解决方案：**
1. 检查数据库中的配置是否更新
2. 清除缓存（重启Gateway Pod）
3. 检查Gateway日志

### 问题2：认证失败锁定不工作

**解决方案：**
1. 检查 `auth_failure_records` 表是否存在
2. 检查失败记录是否正确插入
3. 检查锁定时间是否正确计算

### 问题3：会话超时不准确

**解决方案：**
1. 检查Redis中的会话过期时间
2. 确认配置已正确应用
3. 检查时钟同步

## 总结

问题3已完全修复：

✅ 配置持久化到数据库
✅ Pod重启后配置不丢失
✅ 配置实际应用到系统功能
✅ 支持会话超时控制
✅ 支持证书有效期控制
✅ 支持认证失败锁定
✅ 支持并发会话策略
✅ 提供完整的测试工具
