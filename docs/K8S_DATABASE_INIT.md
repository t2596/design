# Kubernetes 数据库初始化说明

## 概述

Kubernetes部署时，PostgreSQL数据库会自动初始化所有必需的表和数据，包括：

1. 证书管理表
2. 审计日志表
3. 车辆数据表
4. 安全策略配置表（问题3修复）
5. 认证失败记录表（问题3修复）

## 初始化流程

### 1. ConfigMap配置

数据库初始化脚本存储在 `postgres-init-configmap.yaml` 中，包含三个脚本：

- `00-create-user.sql`: 创建应用数据库用户
- `01-schema.sql`: 创建所有数据库表和索引
- `02-init-data.sql`: 插入初始数据

### 2. 执行顺序

PostgreSQL容器启动时会按文件名顺序执行这些脚本：

```
00-create-user.sql
  ↓
01-schema.sql
  ↓
02-init-data.sql
```

### 3. 创建的表

#### 核心表

1. **certificates** - 证书表
2. **certificate_revocation_list** - 证书撤销列表
3. **audit_logs** - 审计日志表
4. **vehicle_data** - 车辆数据表

#### 新增表（问题3修复）

5. **security_policy** - 安全策略配置表
6. **auth_failure_records** - 认证失败记录表

### 4. 初始数据

部署时会自动插入：

- 示例CA证书（开发测试用）
- 系统初始化审计日志
- 默认安全策略配置

## 默认安全策略配置

```sql
session_timeout: 86400秒 (24小时)
certificate_validity: 365天 (1年)
timestamp_tolerance: 300秒 (5分钟)
concurrent_session_strategy: 'reject_new'
max_auth_failures: 5次
auth_failure_lockout_duration: 300秒 (5分钟)
```

## 部署步骤

### 方式1：完整部署（推荐）

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

### 方式2：使用一键部署脚本

```bash
cd deployment/kubernetes
bash deploy-all.sh
```

## 验证数据库初始化

### 检查表是否创建

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt"
```

预期输出应包含：
- certificates
- certificate_revocation_list
- audit_logs
- vehicle_data
- security_policy
- auth_failure_records

### 检查默认安全策略

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM security_policy;"
```

预期输出：
```
 id | session_timeout | certificate_validity | timestamp_tolerance | concurrent_session_strategy | max_auth_failures | auth_failure_lockout_duration | updated_at | updated_by
----+-----------------+----------------------+---------------------+-----------------------------+-------------------+-------------------------------+------------+------------
  1 |           86400 |                  365 |                 300 | reject_new                  |                 5 |                           300 | ...        | system
```

### 检查审计日志初始数据

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM audit_logs;"
```

预期输出应包含两条系统初始化日志。

## 重新初始化数据库

如果需要重新初始化数据库：

### 方式1：删除并重新创建Pod

```bash
# 删除PostgreSQL Pod
kubectl delete pod -l app=postgres -n vehicle-iot-gateway

# Kubernetes会自动重新创建Pod并执行初始化脚本
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=120s
```

### 方式2：删除PVC并重新部署

```bash
# 警告：这会删除所有数据！

# 1. 删除PostgreSQL部署
kubectl delete deployment postgres -n vehicle-iot-gateway

# 2. 删除PVC
kubectl delete pvc postgres-pvc -n vehicle-iot-gateway

# 3. 重新部署
kubectl apply -f postgres-deployment.yaml

# 4. 等待就绪
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=120s
```

## 更新ConfigMap

如果需要修改初始化脚本：

```bash
# 1. 编辑ConfigMap
kubectl edit configmap postgres-init-scripts -n vehicle-iot-gateway

# 或者重新应用
kubectl apply -f postgres-init-configmap.yaml

# 2. 删除PostgreSQL Pod以应用新配置
kubectl delete pod -l app=postgres -n vehicle-iot-gateway

# 3. 等待新Pod就绪
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=120s
```

注意：如果数据库已经初始化，重新创建Pod不会重新执行初始化脚本（因为数据已存在）。

## 手动执行迁移脚本

如果数据库已经运行，需要添加新表：

```bash
# 执行迁移脚本
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway < db/migrations/003_security_policy_table.sql
```

或者使用提供的脚本：

```bash
bash apply_security_policy_migration.sh
```

## 常见问题

### 问题1：表已存在错误

**症状：** 初始化脚本报错 "table already exists"

**原因：** 使用了持久化存储，数据库已经初始化过

**解决方案：** 
- 如果是开发环境，可以删除PVC重新初始化
- 如果是生产环境，使用迁移脚本添加新表

### 问题2：默认配置未插入

**症状：** `security_policy` 表为空

**原因：** 可能是 `ON CONFLICT DO NOTHING` 导致插入被跳过

**解决方案：**
```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "INSERT INTO security_policy (session_timeout, certificate_validity, timestamp_tolerance, concurrent_session_strategy, max_auth_failures, auth_failure_lockout_duration, updated_by) 
   VALUES (86400, 365, 300, 'reject_new', 5, 300, 'system');"
```

### 问题3：权限错误

**症状：** Gateway无法访问新表

**原因：** `gateway_user` 没有权限

**解决方案：**
```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gateway_user;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gateway_user;"
```

## 数据库备份

建议在生产环境定期备份数据库：

```bash
# 备份整个数据库
kubectl exec deployment/postgres -n vehicle-iot-gateway -- \
  pg_dump -U postgres vehicle_iot_gateway > backup.sql

# 恢复数据库
kubectl exec -i deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres vehicle_iot_gateway < backup.sql
```

## 监控数据库状态

```bash
# 查看数据库大小
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT pg_size_pretty(pg_database_size('vehicle_iot_gateway'));"

# 查看表大小
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size 
   FROM pg_tables 
   WHERE schemaname = 'public' 
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# 查看连接数
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT count(*) FROM pg_stat_activity;"
```

## 相关文件

- `deployment/kubernetes/postgres-init-configmap.yaml` - 数据库初始化ConfigMap
- `deployment/kubernetes/postgres-deployment.yaml` - PostgreSQL部署配置
- `db/schema.sql` - 本地数据库架构文件
- `db/init_data.sql` - 本地初始化数据文件
- `db/migrations/003_security_policy_table.sql` - 安全策略表迁移脚本

## 总结

Kubernetes部署时会自动初始化所有必需的数据库表和数据，包括问题3修复所需的安全策略表。无需手动执行迁移脚本，一键部署即可完成所有配置。
