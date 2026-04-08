# 完整部署流程指南

## 概述

本指南提供从代码修改到Kubernetes部署的完整流程，包含问题2和问题3的所有修复。

## 📋 部署流程总览

```
代码修改 → 构建镜像 → 推送镜像 → 更新K8s配置 → 部署到集群 → 验证功能
```

## 🚀 完整部署步骤

### 步骤1：确认代码修改

确保以下文件已修改：

**问题2相关：**
- ✅ `src/api/routes/auth.py` - 添加审计日志记录
- ✅ `src/api/routes/certificates.py` - 添加审计日志记录

**问题3相关：**
- ✅ `src/security_policy_manager.py` - 新增安全策略管理器
- ✅ `src/api/routes/config.py` - 使用数据库持久化
- ✅ `src/api/routes/auth.py` - 应用安全策略
- ✅ `src/api/routes/certificates.py` - 应用证书有效期
- ✅ `src/certificate_manager.py` - 支持自定义有效期

**数据库相关：**
- ✅ `deployment/kubernetes/postgres-init-configmap.yaml` - 包含新表定义
- ✅ `db/schema.sql` - 包含新表定义
- ✅ `db/init_data.sql` - 包含默认配置

### 步骤2：构建Docker镜像

#### 方式A：使用快速构建脚本（本地测试）

```bash
# 快速构建
bash quick-build.sh

# 测试运行
docker run --rm -p 8000:8000 vehicle-iot-gateway:latest
```

#### 方式B：使用完整构建脚本（推荐）

```bash
# 交互式构建和推送
bash build-and-push.sh -r your-username -v v1.0

# 自动推送
bash build-and-push.sh -r your-username -v v1.0 -p
```

#### 方式C：手动构建

```bash
# 1. 构建镜像
docker build -t your-username/vehicle-iot-gateway:v1.0 .

# 2. 打标签
docker tag your-username/vehicle-iot-gateway:v1.0 your-username/vehicle-iot-gateway:latest

# 3. 推送镜像
docker push your-username/vehicle-iot-gateway:v1.0
docker push your-username/vehicle-iot-gateway:latest
```

### 步骤3：更新Kubernetes配置

编辑 `deployment/kubernetes/gateway-deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
  namespace: vehicle-iot-gateway
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gateway
  template:
    metadata:
      labels:
        app: gateway
    spec:
      containers:
      - name: gateway
        image: your-username/vehicle-iot-gateway:v1.0  # 修改这里
        imagePullPolicy: Always  # 确保总是拉取最新镜像
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_HOST
          value: "postgres"
        - name: POSTGRES_PORT
          value: "5432"
        - name: POSTGRES_DB
          value: "vehicle_iot_gateway"
        - name: POSTGRES_USER
          value: "postgres"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: REDIS_HOST
          value: "redis"
        - name: REDIS_PORT
          value: "6379"
```

### 步骤4：部署到Kubernetes

#### 全新部署

```bash
cd deployment/kubernetes

# 一键部署
bash deploy-all.sh
```

#### 更新已有环境

```bash
# 1. 应用数据库迁移（如果需要）
bash apply_security_policy_migration.sh

# 2. 更新ConfigMap
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml

# 3. 更新Gateway部署
kubectl apply -f deployment/kubernetes/gateway-deployment.yaml

# 4. 等待Pod就绪
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s

# 5. 查看状态
kubectl get pods -n vehicle-iot-gateway
```

### 步骤5：验证部署

#### 5.1 检查Pod状态

```bash
kubectl get pods -n vehicle-iot-gateway

# 预期输出：所有Pod都是Running状态
NAME                        READY   STATUS    RESTARTS   AGE
gateway-xxx                 1/1     Running   0          2m
postgres-xxx                1/1     Running   0          5m
redis-xxx                   1/1     Running   0          5m
web-xxx                     1/1     Running   0          2m
```

#### 5.2 检查Gateway日志

```bash
kubectl logs -f deployment/gateway -n vehicle-iot-gateway

# 应该看到类似输出：
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 5.3 验证数据库表

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt"

# 应该看到6个表：
# - certificates
# - certificate_revocation_list
# - audit_logs
# - vehicle_data
# - security_policy (新增)
# - auth_failure_records (新增)
```

#### 5.4 验证默认配置

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM security_policy;"

# 应该看到一条默认配置记录
```

#### 5.5 测试审计日志功能

```bash
# 生成测试数据
python3 generate_audit_test_data.py

# 测试API
bash test_audit_logs_api.sh

# 检查数据库
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) FROM audit_logs;"
```

#### 5.6 测试安全配置功能

```bash
# 测试配置API
bash test_security_config_api.sh

# 获取配置
curl -X GET "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" | jq '.'
```

### 步骤6：功能测试

#### 测试车辆注册

```bash
curl -X POST "http://8.147.67.31:32620/api/auth/register" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "VIN_TEST_001",
    "public_key": "'$(printf '0%.0s' {1..128})'"
  }' | jq '.'
```

#### 测试审计日志查询

```bash
curl -X GET "http://8.147.67.31:32620/api/audit/logs?limit=10" \
  -H "Authorization: Bearer dev-token-12345" | jq '.'
```

#### 测试安全配置更新

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
  }' | jq '.'
```

## 🔄 滚动更新流程

当需要更新代码时：

```bash
# 1. 修改代码

# 2. 构建新版本镜像
bash build-and-push.sh -r your-username -v v1.1 -p

# 3. 更新deployment配置中的镜像版本
# 编辑 deployment/kubernetes/gateway-deployment.yaml
# 将 image 改为: your-username/vehicle-iot-gateway:v1.1

# 4. 应用更新
kubectl apply -f deployment/kubernetes/gateway-deployment.yaml

# 5. 查看滚动更新状态
kubectl rollout status deployment/gateway -n vehicle-iot-gateway

# 6. 如果需要回滚
kubectl rollout undo deployment/gateway -n vehicle-iot-gateway
```

## 📊 监控和日志

### 查看实时日志

```bash
# Gateway日志
kubectl logs -f deployment/gateway -n vehicle-iot-gateway

# PostgreSQL日志
kubectl logs -f deployment/postgres -n vehicle-iot-gateway

# Redis日志
kubectl logs -f deployment/redis -n vehicle-iot-gateway

# Web日志
kubectl logs -f deployment/web -n vehicle-iot-gateway
```

### 查看资源使用

```bash
# 查看Pod资源使用
kubectl top pods -n vehicle-iot-gateway

# 查看节点资源使用
kubectl top nodes
```

### 查看事件

```bash
# 查看命名空间事件
kubectl get events -n vehicle-iot-gateway --sort-by='.lastTimestamp'

# 查看特定Pod事件
kubectl describe pod <pod-name> -n vehicle-iot-gateway
```

## 🐛 故障排查

### 问题1：Pod无法启动

```bash
# 查看Pod状态
kubectl get pods -n vehicle-iot-gateway

# 查看Pod详情
kubectl describe pod <pod-name> -n vehicle-iot-gateway

# 查看Pod日志
kubectl logs <pod-name> -n vehicle-iot-gateway

# 常见原因：
# - 镜像拉取失败：检查镜像名称和拉取密钥
# - 配置错误：检查ConfigMap和Secrets
# - 资源不足：检查节点资源
```

### 问题2：数据库连接失败

```bash
# 检查PostgreSQL是否运行
kubectl get pods -l app=postgres -n vehicle-iot-gateway

# 检查PostgreSQL日志
kubectl logs deployment/postgres -n vehicle-iot-gateway

# 测试数据库连接
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "SELECT 1;"
```

### 问题3：镜像拉取失败

```bash
# 检查镜像拉取密钥
kubectl get secrets -n vehicle-iot-gateway

# 创建镜像拉取密钥
kubectl create secret docker-registry registry-secret \
  --docker-server=your-registry \
  --docker-username=your-username \
  --docker-password=your-password \
  -n vehicle-iot-gateway

# 在deployment中引用
spec:
  imagePullSecrets:
  - name: registry-secret
```

### 问题4：服务无法访问

```bash
# 检查Service
kubectl get svc -n vehicle-iot-gateway

# 检查端口转发
kubectl port-forward deployment/gateway 8000:8000 -n vehicle-iot-gateway

# 测试访问
curl http://localhost:8000/health
```

## 📝 完整验证清单

### 部署验证
- [ ] 所有Pod处于Running状态
- [ ] Gateway日志正常
- [ ] PostgreSQL包含6个表
- [ ] 默认安全策略已插入
- [ ] Redis正常运行

### 功能验证
- [ ] 车辆注册成功
- [ ] 审计日志记录正常
- [ ] 审计日志查询返回数据
- [ ] 安全配置获取成功
- [ ] 安全配置更新成功
- [ ] 配置持久化到数据库
- [ ] Pod重启后配置保持

### 性能验证
- [ ] API响应时间 < 2秒
- [ ] 数据库查询正常
- [ ] 内存使用正常
- [ ] CPU使用正常

## 🎯 快速命令参考

```bash
# 构建镜像
bash quick-build.sh

# 完整构建和推送
bash build-and-push.sh -r username -v v1.0 -p

# 部署到K8s
cd deployment/kubernetes && bash deploy-all.sh

# 更新Gateway
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 查看状态
kubectl get pods -n vehicle-iot-gateway

# 查看日志
kubectl logs -f deployment/gateway -n vehicle-iot-gateway

# 测试功能
python3 generate_audit_test_data.py
bash test_audit_logs_api.sh
bash test_security_config_api.sh
```

## 📚 相关文档

- **镜像构建详解**: `BUILD_AND_PUSH_IMAGE.md`
- **K8s数据库初始化**: `docs/K8S_DATABASE_INIT.md`
- **一键部署指南**: `K8S_ONE_CLICK_DEPLOY_README.md`
- **问题2修复**: `docs/AUDIT_LOG_FIX.md`
- **问题3修复**: `docs/SECURITY_CONFIG_FIX.md`

## 🎉 总结

完整部署流程：

1. ✅ 确认代码修改
2. ✅ 构建Docker镜像
3. ✅ 推送到镜像仓库
4. ✅ 更新K8s配置
5. ✅ 部署到集群
6. ✅ 验证功能

所有步骤都有详细说明和脚本支持，确保部署顺利进行！
