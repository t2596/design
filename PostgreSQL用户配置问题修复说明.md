# PostgreSQL 用户配置问题修复说明

## 问题根源

你遇到的错误：
```
FATAL: role "postgres" does not exist
```

### 原因分析

**PostgreSQL 官方镜像的行为**：

1. 当设置 `POSTGRES_USER=gateway_user` 时：
   - PostgreSQL **不会创建** `postgres` 超级用户
   - 只会创建 `gateway_user` 用户
   - `gateway_user` 成为数据库的所有者，但**没有超级用户权限**

2. 初始化脚本的问题：
   - 初始化脚本需要创建数据库、表、视图、函数
   - 这些操作需要**超级用户权限**
   - `gateway_user` 权限不足，导致初始化失败

3. 结果：
   - 初始化脚本执行了，但很多操作失败
   - 数据库 `vehicle_iot_gateway` 没有被正确创建
   - 表结构不完整或不存在

### 你的原始配置（有问题）

**secrets.yaml**:
```yaml
stringData:
  POSTGRES_USER: "gateway_user"  # ← 问题：不是超级用户
  POSTGRES_PASSWORD: "change_me_in_production"
```

**postgres-deployment.yaml**:
```yaml
env:
- name: POSTGRES_USER
  valueFrom:
    secretKeyRef:
      name: gateway-secrets
      key: POSTGRES_USER  # 值为 gateway_user
```

## 修复方案

### 修改内容

#### 1. secrets.yaml

**修改前**:
```yaml
stringData:
  POSTGRES_USER: "gateway_user"
  POSTGRES_PASSWORD: "change_me_in_production"
```

**修改后**:
```yaml
stringData:
  POSTGRES_USER: "postgres"  # ← 使用超级用户
  POSTGRES_PASSWORD: "change_me_in_production"
  # 应用层使用的数据库用户（由初始化脚本创建）
  DB_USER: "gateway_user"
  DB_PASSWORD: "change_me_in_production"
```

#### 2. postgres-init-configmap.yaml

添加新的初始化脚本 `00-create-user.sql`（在 `01-schema.sql` 之前执行）：

```sql
-- 创建应用层使用的数据库用户
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'gateway_user') THEN
      
      CREATE ROLE gateway_user LOGIN PASSWORD 'change_me_in_production';
   END IF;
END
$do$;

-- 授予数据库权限
GRANT ALL PRIVILEGES ON DATABASE vehicle_iot_gateway TO gateway_user;

-- 授予 schema 权限
GRANT ALL PRIVILEGES ON SCHEMA public TO gateway_user;

-- 授予默认权限（对未来创建的对象）
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO gateway_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO gateway_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO gateway_user;
```

在 `01-schema.sql` 末尾添加：

```sql
-- 授予 gateway_user 对所有表的权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gateway_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gateway_user;
```

### 为什么这样修复？

1. **postgres 超级用户**：
   - 拥有所有权限
   - 可以创建数据库、用户、表、视图、函数
   - 初始化脚本可以正常执行

2. **gateway_user 应用用户**：
   - 由初始化脚本创建
   - 被授予所有必要权限
   - Gateway 应用使用此用户连接数据库
   - 遵循最小权限原则（不需要超级用户权限）

3. **初始化顺序**：
   ```
   00-create-user.sql  → 创建 gateway_user
   01-schema.sql       → 创建表结构，授予权限
   02-init-data.sql    → 插入初始数据
   ```

## 部署步骤

### 自动部署（推荐）

```bash
# 运行修复脚本
bash deploy_fixed_postgres.sh
```

脚本会自动：
1. 删除现有 PostgreSQL 部署
2. 应用修复后的配置
3. 重新部署 PostgreSQL
4. 验证数据库、用户、表
5. 测试权限
6. 重启 Gateway

### 手动部署

如果自动脚本失败，手动执行：

#### 步骤 1: 删除现有部署

```bash
kubectl delete deployment postgres -n vehicle-iot-gateway
kubectl wait --for=delete pod -l app=postgres -n vehicle-iot-gateway --timeout=60s
```

#### 步骤 2: 应用配置

```bash
kubectl apply -f deployment/kubernetes/secrets.yaml
kubectl apply -f deployment/kubernetes/configmap.yaml
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml
```

#### 步骤 3: 等待就绪

```bash
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=120s
```

#### 步骤 4: 验证

```bash
# 检查数据库
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -c "\l" | grep vehicle_iot_gateway

# 检查用户
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -c "\du" | grep gateway_user

# 检查表
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt"

# 测试 gateway_user 连接
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d vehicle_iot_gateway -c "SELECT 1;"
```

#### 步骤 5: 重启 Gateway

```bash
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s
```

## 验证修复

### 1. 检查初始化日志

```bash
kubectl logs -n vehicle-iot-gateway -l app=postgres --tail=100
```

应该看到：
```
CREATE ROLE
GRANT
CREATE TABLE
CREATE INDEX
CREATE VIEW
CREATE FUNCTION
GRANT
```

### 2. 验证数据库结构

```bash
# 列出所有数据库
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -c "\l"

# 应该看到 vehicle_iot_gateway

# 列出所有用户
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -c "\du"

# 应该看到 postgres 和 gateway_user

# 列出所有表
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d vehicle_iot_gateway -c "\dt"

# 应该看到：
# - certificates
# - certificate_revocation_list
# - audit_logs
# - vehicle_data
```

### 3. 测试数据写入

```bash
# 使用 gateway_user 插入数据
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d vehicle_iot_gateway -c \
  "INSERT INTO vehicle_data (vehicle_id, timestamp, state, motion_speed) 
   VALUES ('TEST', NOW(), '测试', 100);"

# 查询数据
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d vehicle_iot_gateway -c \
  "SELECT * FROM vehicle_data WHERE vehicle_id='TEST';"
```

### 4. 测试客户端

```bash
cd client
python vehicle_client.py \
  --gateway-host 8.147.67.31 \
  --gateway-port 32620 \
  --mode continuous \
  --iterations 10
```

### 5. 检查数据库

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d vehicle_iot_gateway -c \
  "SELECT vehicle_id, timestamp, state, motion_speed 
   FROM vehicle_data ORDER BY timestamp DESC LIMIT 10;"
```

### 6. 访问 Web 界面

打开浏览器：`http://8.147.67.31:32620`

## 常见问题

### Q1: 为什么不能直接使用 gateway_user？

A: `gateway_user` 不是超级用户，无法执行某些初始化操作（如创建扩展、创建函数等）。使用 `postgres` 超级用户进行初始化，然后授权给 `gateway_user` 是最佳实践。

### Q2: Gateway 应用使用哪个用户连接？

A: Gateway 应用仍然使用 `gateway_user` 连接数据库。这是通过环境变量 `POSTGRES_USER=gateway_user` 传递给 Gateway 的（不是传递给 PostgreSQL 容器）。

**注意**：你可能需要更新 Gateway 的环境变量配置，确保它使用 `gateway_user` 而不是 `postgres`。

### Q3: 密码在哪里配置？

A: 密码在 `secrets.yaml` 中配置：
- `POSTGRES_PASSWORD`: PostgreSQL 超级用户密码
- 初始化脚本中硬编码了 `gateway_user` 的密码（应该从环境变量读取）

**改进建议**：修改初始化脚本，从环境变量读取 `gateway_user` 密码。

### Q4: 如何在生产环境使用？

A: 
1. 修改 `secrets.yaml` 中的密码
2. 使用 Kubernetes Secrets 管理敏感信息
3. 考虑使用 PersistentVolume 而不是 emptyDir
4. 启用 PostgreSQL 的 SSL 连接

## 安全建议

1. **修改默认密码**：
   ```yaml
   POSTGRES_PASSWORD: "your-strong-password-here"
   ```

2. **使用 Kubernetes Secrets**：
   ```bash
   kubectl create secret generic gateway-secrets \
     --from-literal=POSTGRES_PASSWORD='your-password' \
     -n vehicle-iot-gateway
   ```

3. **限制网络访问**：
   - PostgreSQL Service 使用 ClusterIP（已配置）
   - 只允许 Gateway Pod 访问

4. **启用审计日志**：
   - 记录所有数据库操作
   - 定期审查日志

## 总结

**修复前的问题**：
- ✗ 使用 `gateway_user` 作为 PostgreSQL 主用户
- ✗ `gateway_user` 权限不足
- ✗ 初始化脚本执行失败
- ✗ 数据库和表未正确创建

**修复后的状态**：
- ✓ 使用 `postgres` 超级用户进行初始化
- ✓ 初始化脚本创建 `gateway_user`
- ✓ 授予 `gateway_user` 所有必要权限
- ✓ Gateway 应用使用 `gateway_user` 连接
- ✓ 遵循最小权限原则

**下一步**：
1. 运行 `deploy_fixed_postgres.sh`
2. 验证数据库和表
3. 测试客户端
4. 检查 Web 界面
