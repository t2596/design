# PostgreSQL 初始化脚本问题修复

## 问题描述

PostgreSQL Pod 卡在启动阶段，无法正常运行。查看日志可能会看到类似以下错误：

```
Error: configmaps "postgres-init-scripts" not found
```

或者 Pod 状态显示：

```
Status: ContainerCreating
Events: MountVolume.SetUp failed for volume "init-scripts" : configmap "postgres-init-scripts" not found
```

## 问题原因

`postgres-deployment.yaml` 引用了一个名为 `postgres-init-scripts` 的 ConfigMap 来挂载数据库初始化脚本，但是这个 ConfigMap 没有被创建。

```yaml
volumes:
- name: init-scripts
  configMap:
    name: postgres-init-scripts  # ← 这个 ConfigMap 不存在
```

## 解决方案

### 方案 1: 创建 ConfigMap（推荐）

创建包含初始化脚本的 ConfigMap。

#### 步骤 1: 应用 ConfigMap

```bash
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml
```

#### 步骤 2: 验证 ConfigMap 创建成功

```bash
kubectl get configmap postgres-init-scripts -n vehicle-iot-gateway
```

应该看到：

```
NAME                     DATA   AGE
postgres-init-scripts    2      5s
```

#### 步骤 3: 重启 PostgreSQL Pod

如果 Pod 已经在运行但卡住了：

```bash
# 删除现有 Pod，让 Deployment 重新创建
kubectl delete pod -l app=postgres -n vehicle-iot-gateway

# 或者重启 Deployment
kubectl rollout restart deployment/postgres -n vehicle-iot-gateway
```

#### 步骤 4: 验证 Pod 启动成功

```bash
# 查看 Pod 状态
kubectl get pods -n vehicle-iot-gateway -l app=postgres

# 查看 Pod 日志
kubectl logs -n vehicle-iot-gateway -l app=postgres

# 应该看到类似输出：
# PostgreSQL init process complete; ready for start up.
# database system is ready to accept connections
```

### 方案 2: 移除初始化脚本挂载（快速修复）

如果你不需要自动初始化数据库，可以移除 ConfigMap 引用。

#### 修改 postgres-deployment.yaml

删除以下部分：

```yaml
# 删除 volumeMounts 中的这部分
volumeMounts:
- name: init-scripts
  mountPath: /docker-entrypoint-initdb.d

# 删除 volumes 中的这部分
volumes:
- name: init-scripts
  configMap:
    name: postgres-init-scripts
```

保留：

```yaml
volumeMounts:
- name: postgres-storage
  mountPath: /var/lib/postgresql/data

volumes:
- name: postgres-storage
  persistentVolumeClaim:
    claimName: postgres-pvc
```

然后应用更新：

```bash
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml
```

**注意**：使用此方案后，需要手动初始化数据库架构。

## 初始化脚本说明

ConfigMap 包含两个 SQL 脚本：

### 1. `01-schema.sql` - 数据库架构

创建以下表和索引：
- `certificates` - 证书表
- `certificate_revocation_list` - 证书撤销列表
- `audit_logs` - 审计日志表
- 相关索引和视图

### 2. `02-init-data.sql` - 初始数据

插入示例数据：
- CA 根证书（用于测试）
- 系统初始化日志

**注意**：初始数据脚本仅用于开发测试环境。生产环境建议删除或修改。

## 手动初始化数据库（如果使用方案 2）

如果你选择了方案 2（移除初始化脚本），需要手动初始化数据库：

### 方法 1: 使用 kubectl exec

```bash
# 进入 PostgreSQL Pod
kubectl exec -it -n vehicle-iot-gateway deployment/postgres -- psql -U gateway_user -d vehicle_iot_gateway

# 在 psql 中执行 SQL
\i /path/to/schema.sql
\i /path/to/init_data.sql
```

### 方法 2: 使用本地脚本

```bash
# 从本地执行初始化脚本
kubectl port-forward -n vehicle-iot-gateway svc/postgres-service 5432:5432

# 在另一个终端
psql -h localhost -U gateway_user -d vehicle_iot_gateway -f db/schema.sql
psql -h localhost -U gateway_user -d vehicle_iot_gateway -f db/init_data.sql
```

### 方法 3: 使用 Python 脚本

```bash
# 设置环境变量
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=vehicle_iot_gateway
export POSTGRES_USER=gateway_user
export POSTGRES_PASSWORD=your_password

# 运行初始化脚本
python scripts/init_database.py
```

## 验证数据库初始化

连接到数据库并验证表已创建：

```bash
kubectl exec -it -n vehicle-iot-gateway deployment/postgres -- psql -U gateway_user -d vehicle_iot_gateway -c "\dt"
```

应该看到：

```
                    List of relations
 Schema |             Name              | Type  |    Owner     
--------+-------------------------------+-------+--------------
 public | audit_logs                    | table | gateway_user
 public | certificate_revocation_list   | table | gateway_user
 public | certificates                  | table | gateway_user
```

## 故障排查

### 问题 1: ConfigMap 创建失败

**错误信息：**
```
error: error validating "postgres-init-configmap.yaml": error validating data
```

**解决方案：**
- 检查 YAML 格式是否正确
- 确保缩进使用空格而不是 Tab
- 验证 SQL 脚本中没有特殊字符导致 YAML 解析错误

### 问题 2: Pod 仍然卡住

**检查步骤：**

```bash
# 查看 Pod 详细信息
kubectl describe pod -n vehicle-iot-gateway -l app=postgres

# 查看事件
kubectl get events -n vehicle-iot-gateway --sort-by='.lastTimestamp'

# 查看 Pod 日志
kubectl logs -n vehicle-iot-gateway -l app=postgres
```

**常见原因：**
- PVC 未绑定：检查 `kubectl get pvc -n vehicle-iot-gateway`
- 资源不足：检查节点资源
- 镜像拉取失败：检查镜像名称和网络

### 问题 3: 数据库连接失败

**测试连接：**

```bash
# 从 Pod 内部测试
kubectl exec -it -n vehicle-iot-gateway deployment/postgres -- pg_isready -U gateway_user

# 从网关 Pod 测试
kubectl exec -it -n vehicle-iot-gateway deployment/gateway -- nc -zv postgres-service 5432
```

## 完整部署顺序

正确的部署顺序应该是：

```bash
# 1. 创建 namespace
kubectl apply -f deployment/kubernetes/namespace.yaml

# 2. 创建 ConfigMap（包括 postgres-init-scripts）
kubectl apply -f deployment/kubernetes/configmap.yaml
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml

# 3. 创建 Secrets
kubectl apply -f deployment/kubernetes/secrets.yaml

# 4. 部署 PostgreSQL
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml

# 5. 等待 PostgreSQL 就绪
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=300s

# 6. 部署 Redis
kubectl apply -f deployment/kubernetes/redis-deployment.yaml

# 7. 等待 Redis 就绪
kubectl wait --for=condition=ready pod -l app=redis -n vehicle-iot-gateway --timeout=300s

# 8. 部署网关
kubectl apply -f deployment/kubernetes/gateway-deployment.yaml

# 9. 验证所有服务
kubectl get all -n vehicle-iot-gateway
```

## 相关文档

- [部署指南](DEPLOYMENT.md) - 完整的 Kubernetes 部署说明
- [故障排查](TROUBLESHOOTING.md) - 常见问题解决方案
- [运维手册](OPERATIONS.md) - 日常运维操作

## 生产环境建议

1. **移除测试数据**：
   - 编辑 `postgres-init-configmap.yaml`
   - 删除或注释掉 `02-init-data.sql` 中的测试数据

2. **使用外部数据库**：
   - 考虑使用云服务商提供的托管 PostgreSQL
   - 更好的可用性和备份方案

3. **数据持久化**：
   - 确保 PVC 使用可靠的存储类
   - 配置定期备份策略

4. **安全加固**：
   - 使用强密码
   - 限制数据库访问权限
   - 启用 SSL/TLS 连接
