# Kubernetes 部署文件

## 快速开始

### 一键部署

```bash
cd deployment/kubernetes
chmod +x deploy-all.sh
./deploy-all.sh
```

### 一键清理

```bash
cd deployment/kubernetes
chmod +x cleanup.sh
./cleanup.sh
```

## 文件说明

### 核心配置文件

| 文件 | 说明 | 必需 |
|------|------|------|
| `namespace.yaml` | 创建 vehicle-iot-gateway namespace | ✅ |
| `configmap.yaml` | 应用配置（数据库地址、端口等） | ✅ |
| `secrets.yaml` | 敏感信息（密码、CA 密钥等） | ✅ |
| `postgres-init-configmap.yaml` | PostgreSQL 初始化脚本 | ✅ |

### 部署文件

| 文件 | 说明 | 存储 |
|------|------|------|
| `postgres-deployment.yaml` | PostgreSQL 数据库 | emptyDir（临时） |
| `redis-deployment.yaml` | Redis 缓存 | emptyDir（临时） |
| `gateway-deployment.yaml` | 网关应用 | 无状态 |

### 脚本文件

| 文件 | 说明 |
|------|------|
| `deploy-all.sh` | 一键部署脚本 |
| `cleanup.sh` | 一键清理脚本 |

## 手动部署步骤

### 1. 创建 Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. 创建 ConfigMaps

```bash
kubectl apply -f configmap.yaml
kubectl apply -f postgres-init-configmap.yaml
```

### 3. 创建 Secrets

```bash
kubectl apply -f secrets.yaml
```

### 4. 部署数据库和缓存

```bash
# PostgreSQL
kubectl apply -f postgres-deployment.yaml

# Redis
kubectl apply -f redis-deployment.yaml

# 等待就绪
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=120s
kubectl wait --for=condition=ready pod -l app=redis -n vehicle-iot-gateway --timeout=120s
```

### 5. 部署网关

```bash
kubectl apply -f gateway-deployment.yaml

# 等待就绪
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s
```

### 6. 验证部署

```bash
# 查看所有资源
kubectl get all -n vehicle-iot-gateway

# 查看 Pod 状态
kubectl get pods -n vehicle-iot-gateway

# 查看服务
kubectl get svc -n vehicle-iot-gateway
```

## 访问网关

### 方法 1: 端口转发（推荐用于测试）

```bash
kubectl port-forward -n vehicle-iot-gateway svc/gateway-service 8000:8000
```

然后访问：
- 健康检查: http://localhost:8000/health
- API 文档: http://localhost:8000/docs

### 方法 2: LoadBalancer（如果支持）

```bash
# 获取外部 IP
kubectl get svc gateway-service -n vehicle-iot-gateway

# 访问
curl http://<EXTERNAL-IP>:8000/health
```

### 方法 3: NodePort

修改 `gateway-deployment.yaml` 中的 Service 类型：

```yaml
spec:
  type: NodePort
```

然后：

```bash
kubectl apply -f gateway-deployment.yaml

# 获取 NodePort
kubectl get svc gateway-service -n vehicle-iot-gateway

# 访问
curl http://<NODE-IP>:<NODE-PORT>/health
```

## 常用命令

### 查看日志

```bash
# 网关日志
kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=50 -f

# PostgreSQL 日志
kubectl logs -n vehicle-iot-gateway -l app=postgres --tail=50

# Redis 日志
kubectl logs -n vehicle-iot-gateway -l app=redis --tail=50
```

### 进入容器

```bash
# 进入网关容器
kubectl exec -it -n vehicle-iot-gateway deployment/gateway -- /bin/sh

# 进入 PostgreSQL 容器
kubectl exec -it -n vehicle-iot-gateway deployment/postgres -- psql -U gateway_user -d vehicle_iot_gateway

# 进入 Redis 容器
kubectl exec -it -n vehicle-iot-gateway deployment/redis -- redis-cli
```

### 重启服务

```bash
# 重启网关
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 重启 PostgreSQL
kubectl rollout restart deployment/postgres -n vehicle-iot-gateway

# 重启 Redis
kubectl rollout restart deployment/redis -n vehicle-iot-gateway
```

### 扩缩容

```bash
# 扩展网关副本数
kubectl scale deployment/gateway -n vehicle-iot-gateway --replicas=3

# 查看副本状态
kubectl get pods -n vehicle-iot-gateway -l app=gateway
```

### 更新配置

```bash
# 更新 ConfigMap
kubectl apply -f configmap.yaml

# 更新 Secrets
kubectl apply -f secrets.yaml

# 重启相关服务使配置生效
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway
```

## 存储说明

### 当前配置（emptyDir）

- **PostgreSQL**: 使用 `emptyDir`，Pod 重启后数据丢失
- **Redis**: 使用 `emptyDir`，Pod 重启后缓存清空

### 特点

✅ **优点**：
- 部署简单，无需配置 PVC
- 启动快速，无需等待存储绑定
- 适合快速测试和开发

⚠️ **注意**：
- 数据不持久化
- 仅用于测试环境
- Pod 重启后需要重新初始化

### 迁移到持久化存储

如果需要持久化存储，参考 [NO_PVC_DEPLOYMENT.md](../../docs/NO_PVC_DEPLOYMENT.md)

## 故障排查

### Pod 无法启动

```bash
# 查看 Pod 详情
kubectl describe pod -n vehicle-iot-gateway <pod-name>

# 查看事件
kubectl get events -n vehicle-iot-gateway --sort-by='.lastTimestamp'

# 查看日志
kubectl logs -n vehicle-iot-gateway <pod-name>
```

### ConfigMap 不存在

```bash
# 检查 ConfigMap
kubectl get configmap -n vehicle-iot-gateway

# 如果缺少 postgres-init-scripts
kubectl apply -f postgres-init-configmap.yaml
```

### 数据库连接失败

```bash
# 测试 PostgreSQL 连接
kubectl exec -it -n vehicle-iot-gateway deployment/gateway -- \
  nc -zv postgres-service 5432

# 测试 Redis 连接
kubectl exec -it -n vehicle-iot-gateway deployment/gateway -- \
  nc -zv redis-service 6379
```

### 证书申请失败

检查 CA 密钥配置：

```bash
# 查看 Secrets
kubectl get secret gateway-secrets -n vehicle-iot-gateway -o yaml

# 确认包含 CA_PRIVATE_KEY 和 CA_PUBLIC_KEY
```

参考 [CA_KEY_CONFIGURATION.md](../../docs/CA_KEY_CONFIGURATION.md)

## 清理部署

### 删除所有资源

```bash
./cleanup.sh
```

### 手动删除

```bash
# 删除所有 Deployments
kubectl delete deployment --all -n vehicle-iot-gateway

# 删除所有 Services
kubectl delete service --all -n vehicle-iot-gateway

# 删除所有 ConfigMaps
kubectl delete configmap --all -n vehicle-iot-gateway

# 删除所有 Secrets
kubectl delete secret --all -n vehicle-iot-gateway

# 删除 Namespace
kubectl delete namespace vehicle-iot-gateway
```

## 相关文档

- [无 PVC 部署说明](../../docs/NO_PVC_DEPLOYMENT.md) - emptyDir 配置详解
- [PostgreSQL 初始化修复](../../docs/POSTGRES_INIT_FIX.md) - 数据库初始化问题
- [CA 密钥配置](../../docs/CA_KEY_CONFIGURATION.md) - CA 密钥配置指南
- [部署指南](../../docs/DEPLOYMENT.md) - 完整部署文档

## 生产环境建议

1. **使用持久化存储**：配置 PVC 或使用外部数据库
2. **配置资源限制**：设置合理的 CPU 和内存限制
3. **启用监控**：集成 Prometheus 和 Grafana
4. **配置备份**：定期备份数据库
5. **使用 Ingress**：配置域名和 HTTPS
6. **多副本部署**：提高可用性
7. **配置健康检查**：优化 liveness 和 readiness probe

## 支持

如有问题，请查看：
- [故障排查文档](../../docs/TROUBLESHOOTING.md)
- [运维手册](../../docs/OPERATIONS.md)
