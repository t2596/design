# 无 PVC 部署配置

## 变更说明

为了简化测试部署，移除了 PostgreSQL 和 Redis 的 PersistentVolumeClaim (PVC) 依赖，改用 `emptyDir` 临时存储。

## 变更原因

1. **Redis**：作为缓存使用，不需要持久化存储
2. **PostgreSQL**：计划在测试完成后独立部署，K8s 中只用于测试
3. **简化部署**：避免 PVC 绑定问题，加快部署速度

## 变更内容

### Redis 部署

**之前（使用 PVC）：**
```yaml
volumes:
- name: redis-storage
  persistentVolumeClaim:
    claimName: redis-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

**现在（使用 emptyDir）：**
```yaml
volumes:
- name: redis-storage
  emptyDir: {}
```

### PostgreSQL 部署

**之前（使用 PVC）：**
```yaml
volumes:
- name: postgres-storage
  persistentVolumeClaim:
    claimName: postgres-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

**现在（使用 emptyDir）：**
```yaml
volumes:
- name: postgres-storage
  emptyDir: {}
```

## emptyDir 说明

### 什么是 emptyDir？

`emptyDir` 是 Kubernetes 提供的临时存储卷：
- Pod 创建时自动创建
- Pod 删除时自动清理
- 存储在节点的本地磁盘上
- 不需要预先创建 PVC

### 优点

1. **部署简单**：不需要配置存储类或 PVC
2. **启动快速**：无需等待 PVC 绑定
3. **自动清理**：Pod 删除后自动释放空间
4. **适合测试**：快速迭代，不保留历史数据

### 缺点

1. **数据不持久**：Pod 重启后数据丢失
2. **不适合生产**：无法保证数据安全
3. **无法迁移**：数据绑定在特定节点

## 使用场景

### ✅ 适合使用 emptyDir

- **开发测试环境**
- **临时缓存数据**（Redis）
- **可重建的数据**
- **快速原型验证**

### ❌ 不适合使用 emptyDir

- **生产环境**
- **重要业务数据**
- **需要数据持久化**
- **需要数据备份**

## 部署步骤

### 快速部署（测试环境）

```bash
# 1. 创建 namespace
kubectl apply -f deployment/kubernetes/namespace.yaml

# 2. 创建 ConfigMaps
kubectl apply -f deployment/kubernetes/configmap.yaml
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml

# 3. 创建 Secrets
kubectl apply -f deployment/kubernetes/secrets.yaml

# 4. 部署 PostgreSQL（无 PVC）
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml

# 5. 部署 Redis（无 PVC）
kubectl apply -f deployment/kubernetes/redis-deployment.yaml

# 6. 部署网关
kubectl apply -f deployment/kubernetes/gateway-deployment.yaml

# 7. 验证部署
kubectl get pods -n vehicle-iot-gateway
```

### 验证服务

```bash
# 检查所有 Pod 状态（应该都是 Running）
kubectl get pods -n vehicle-iot-gateway

# 检查服务
kubectl get svc -n vehicle-iot-gateway

# 查看日志
kubectl logs -n vehicle-iot-gateway -l app=postgres --tail=20
kubectl logs -n vehicle-iot-gateway -l app=redis --tail=20
kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=20
```

## 数据持久化注意事项

### Redis

使用 `emptyDir` 后：
- ✅ 缓存功能正常
- ✅ 性能不受影响
- ⚠️ Pod 重启后缓存清空（这是预期行为）
- ⚠️ 不影响系统功能（缓存会自动重建）

### PostgreSQL

使用 `emptyDir` 后：
- ⚠️ Pod 重启后数据丢失
- ⚠️ 需要重新初始化数据库
- ⚠️ 证书、审计日志等数据会丢失

**建议**：
1. 测试期间频繁重启 Pod 时，数据会丢失
2. 初始化脚本会自动重建表结构
3. 测试完成后迁移到独立的 PostgreSQL 实例

## 迁移到独立 PostgreSQL

测试完成后，将 PostgreSQL 从 K8s 中剥离：

### 步骤 1: 准备独立 PostgreSQL

```bash
# 使用 Docker 运行独立 PostgreSQL
docker run -d \
  --name vehicle-iot-postgres \
  -e POSTGRES_DB=vehicle_iot_gateway \
  -e POSTGRES_USER=gateway_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# 初始化数据库
psql -h localhost -U gateway_user -d vehicle_iot_gateway -f db/schema.sql
psql -h localhost -U gateway_user -d vehicle_iot_gateway -f db/init_data.sql
```

### 步骤 2: 更新网关配置

修改 `deployment/kubernetes/configmap.yaml`：

```yaml
data:
  POSTGRES_HOST: "your-postgres-host"  # 独立 PostgreSQL 的地址
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "vehicle_iot_gateway"
```

### 步骤 3: 删除 K8s 中的 PostgreSQL

```bash
# 删除 PostgreSQL Deployment
kubectl delete deployment postgres -n vehicle-iot-gateway

# 删除 PostgreSQL Service
kubectl delete service postgres-service -n vehicle-iot-gateway

# 重启网关使配置生效
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway
```

## 恢复 PVC 配置（如果需要）

如果后续需要在 K8s 中使用持久化存储：

### 创建 PVC

```yaml
# postgres-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: vehicle-iot-gateway
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard  # 根据集群配置修改
```

### 修改 Deployment

```yaml
volumes:
- name: postgres-storage
  persistentVolumeClaim:
    claimName: postgres-pvc
```

## 故障排查

### 问题 1: Pod 启动后立即退出

**检查日志：**
```bash
kubectl logs -n vehicle-iot-gateway -l app=postgres
kubectl logs -n vehicle-iot-gateway -l app=redis
```

**常见原因：**
- 初始化脚本错误
- 环境变量配置错误
- 资源限制过低

### 问题 2: 数据库连接失败

**测试连接：**
```bash
# 从网关 Pod 测试
kubectl exec -it -n vehicle-iot-gateway deployment/gateway -- \
  nc -zv postgres-service 5432

kubectl exec -it -n vehicle-iot-gateway deployment/gateway -- \
  nc -zv redis-service 6379
```

### 问题 3: Pod 重启后数据丢失

这是 `emptyDir` 的预期行为：
- ✅ 正常：数据在 Pod 重启后丢失
- ✅ 解决：初始化脚本会自动重建表结构
- ⚠️ 注意：测试数据需要重新创建

## 性能考虑

### emptyDir 性能

- **读写速度**：与节点本地磁盘相同
- **空间限制**：受节点磁盘空间限制
- **I/O 性能**：通常优于网络存储（PVC）

### 适合测试的原因

1. **快速部署**：无需等待 PVC 绑定
2. **简单清理**：删除 Pod 即可
3. **隔离测试**：每次部署都是全新环境
4. **成本低**：不占用持久化存储配额

## 相关文档

- [快速部署指南](QUICKSTART_DOCKER.md) - Docker Compose 部署
- [部署指南](DEPLOYMENT.md) - 完整的 Kubernetes 部署说明
- [PostgreSQL 初始化修复](POSTGRES_INIT_FIX.md) - 数据库初始化问题

## 总结

使用 `emptyDir` 替代 PVC 后：

✅ **优点**：
- 部署更简单快速
- 不需要配置存储类
- 适合快速测试迭代

⚠️ **注意**：
- 数据不持久化
- 仅用于测试环境
- 生产环境需要独立数据库

🎯 **推荐用法**：
- K8s 中：用于快速测试和开发
- 生产环境：使用独立的 PostgreSQL 和 Redis 实例
