# 包含问题2和问题3修复的部署指南

## 概述

此部署包含以下修复：

- ✅ **问题2修复**：Web端审计日志查询功能
- ✅ **问题3修复**：Web端安全配置持久化功能

所有修复已集成到Kubernetes部署配置中，一键部署即可完成所有配置。

## 修复内容

### 问题2：审计日志查询

- 在车辆认证、数据传输、证书操作中自动记录审计日志
- 支持审计日志查询和导出
- 记录客户端IP地址

### 问题3：安全配置持久化

- 配置持久化到数据库（不再丢失）
- 支持会话超时控制
- 支持证书有效期控制
- 支持认证失败锁定
- 配置实际应用到系统功能

## 数据库表

部署时会自动创建以下表：

### 原有表
1. `certificates` - 证书表
2. `certificate_revocation_list` - 证书撤销列表
3. `audit_logs` - 审计日志表
4. `vehicle_data` - 车辆数据表

### 新增表（问题3修复）
5. `security_policy` - 安全策略配置表
6. `auth_failure_records` - 认证失败记录表

## 一键部署

### 方式1：使用部署脚本（推荐）

```bash
cd deployment/kubernetes
bash deploy-all.sh
```

### 方式2：手动部署

```bash
cd deployment/kubernetes

# 1. 创建命名空间
kubectl apply -f namespace.yaml

# 2. 创建ConfigMap和Secrets
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f postgres-init-configmap.yaml

# 3. 部署数据库
kubectl apply -f postgres-deployment.yaml
kubectl apply -f redis-deployment.yaml

# 4. 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=120s

# 5. 部署应用
kubectl apply -f gateway-deployment.yaml
kubectl apply -f web-deployment.yaml

# 6. 验证部署
kubectl get pods -n vehicle-iot-gateway
```

## 验证部署

### 1. 检查Pod状态

```bash
kubectl get pods -n vehicle-iot-gateway
```

所有Pod应该处于 `Running` 状态。

### 2. 验证数据库表

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt"
```

应该看到所有6个表。

### 3. 验证默认安全策略

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM security_policy;"
```

应该看到一条默认配置记录。

### 4. 测试审计日志功能

```bash
# 生成测试数据
python3 generate_audit_test_data.py

# 检查审计日志
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) FROM audit_logs;"

# 测试API
bash test_audit_logs_api.sh
```

### 5. 测试安全配置功能

```bash
# 测试配置API
bash test_security_config_api.sh

# 获取配置
curl -X GET "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" | jq '.'
```

## 重新部署（已有环境）

如果你已经有一个运行中的环境，需要应用修复：

### 步骤1：更新ConfigMap

```bash
cd deployment/kubernetes

# 应用新的ConfigMap（包含安全策略表）
kubectl apply -f postgres-init-configmap.yaml
```

### 步骤2：手动执行数据库迁移

由于数据库已经初始化，需要手动添加新表：

```bash
# 方式1：使用脚本
bash apply_security_policy_migration.sh

# 方式2：手动执行
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway < db/migrations/003_security_policy_table.sql
```

### 步骤3：重新构建和部署Gateway

```bash
# 重新构建镜像
docker build -t vehicle-iot-gateway:latest .

# 如果使用远程仓库
docker tag vehicle-iot-gateway:latest your-registry/vehicle-iot-gateway:latest
docker push your-registry/vehicle-iot-gateway:latest

# 重启Gateway
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 等待就绪
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s
```

### 步骤4：验证修复

```bash
# 验证问题2
python3 generate_audit_test_data.py
bash test_audit_logs_api.sh

# 验证问题3
bash test_security_config_api.sh
```

## 配置说明

### 默认安全策略

```yaml
session_timeout: 86400秒 (24小时)
certificate_validity: 365天 (1年)
timestamp_tolerance: 300秒 (5分钟)
concurrent_session_strategy: 'reject_new'
max_auth_failures: 5次
auth_failure_lockout_duration: 300秒 (5分钟)
```

### 修改配置

可以通过API修改配置：

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

配置会立即生效并持久化到数据库。

## 功能验证清单

### 问题2验证

- [ ] 车辆注册时记录审计日志
- [ ] 数据传输时记录审计日志
- [ ] 证书操作时记录审计日志
- [ ] 审计日志API返回数据
- [ ] 按条件过滤审计日志
- [ ] 导出审计报告

### 问题3验证

- [ ] 能够获取安全配置
- [ ] 能够更新安全配置
- [ ] 配置持久化到数据库
- [ ] Pod重启后配置保持
- [ ] 会话超时配置生效
- [ ] 证书有效期配置生效
- [ ] 认证失败锁定功能正常

## 监控和日志

### 查看Gateway日志

```bash
kubectl logs -f deployment/gateway -n vehicle-iot-gateway
```

### 查看PostgreSQL日志

```bash
kubectl logs -f deployment/postgres -n vehicle-iot-gateway
```

### 查看Redis日志

```bash
kubectl logs -f deployment/redis -n vehicle-iot-gateway
```

## 常见问题

### 问题1：安全策略表不存在

**症状：** Gateway启动失败，日志显示 "relation security_policy does not exist"

**解决方案：**
```bash
# 执行数据库迁移
bash apply_security_policy_migration.sh
```

### 问题2：审计日志为空

**症状：** 审计日志API返回空列表

**解决方案：**
```bash
# 生成测试数据
python3 generate_audit_test_data.py

# 检查数据库
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) FROM audit_logs;"
```

### 问题3：配置更新后不生效

**症状：** 更新配置后系统仍使用旧配置

**解决方案：**
```bash
# 重启Gateway清除缓存
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway
```

## 性能优化建议

### 1. 审计日志归档

定期归档旧的审计日志：

```sql
-- 归档30天前的日志
INSERT INTO audit_logs_archive 
SELECT * FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '30 days';

DELETE FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '30 days';
```

### 2. 数据库索引优化

确保关键字段有索引：

```sql
-- 审计日志索引
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_vehicle_id ON audit_logs(vehicle_id);

-- 安全策略索引
CREATE INDEX IF NOT EXISTS idx_security_policy_updated_at ON security_policy(updated_at DESC);
```

### 3. 连接池配置

在Gateway环境变量中配置数据库连接池：

```yaml
env:
  - name: DB_POOL_SIZE
    value: "20"
  - name: DB_MAX_OVERFLOW
    value: "10"
```

## 备份和恢复

### 备份数据库

```bash
# 备份整个数据库
kubectl exec deployment/postgres -n vehicle-iot-gateway -- \
  pg_dump -U postgres vehicle_iot_gateway > backup_$(date +%Y%m%d).sql

# 仅备份安全策略
kubectl exec deployment/postgres -n vehicle-iot-gateway -- \
  pg_dump -U postgres -t security_policy vehicle_iot_gateway > security_policy_backup.sql
```

### 恢复数据库

```bash
# 恢复整个数据库
kubectl exec -i deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres vehicle_iot_gateway < backup_20240101.sql

# 恢复安全策略
kubectl exec -i deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres vehicle_iot_gateway < security_policy_backup.sql
```

## 相关文档

- **Kubernetes数据库初始化**: `docs/K8S_DATABASE_INIT.md`
- **问题2修复详情**: `docs/AUDIT_LOG_FIX.md`
- **问题3修复详情**: `docs/SECURITY_CONFIG_FIX.md`
- **问题2快速开始**: `AUDIT_LOG_FIX_README.md`
- **问题3快速开始**: `SECURITY_CONFIG_FIX_README.md`
- **问题2和3汇总**: `PROBLEMS_2_AND_3_FIXED.md`

## 总结

通过Kubernetes一键部署，所有修复都会自动应用：

✅ 数据库表自动创建
✅ 默认配置自动插入
✅ 审计日志功能自动启用
✅ 安全配置持久化自动启用

无需手动执行迁移脚本，部署即可使用所有功能。
