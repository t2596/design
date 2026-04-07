# Web 界面 Kubernetes 快速部署

## 快速开始（3 步）

### 1. 构建镜像

```bash
cd web
docker build -t vehicle-iot-gateway-web:latest .
```

### 2. 部署到 Kubernetes

```bash
cd ../deployment/kubernetes
kubectl apply -f web-deployment.yaml
```

### 3. 访问 Web 界面

```bash
# 获取访问地址
kubectl get svc web-service -n vehicle-iot-gateway

# 使用 NodePort 访问
http://<NODE-IP>:30080
```

## 完整部署（包含所有服务）

```bash
cd deployment/kubernetes
./deploy-all.sh
```

脚本会自动部署：
1. Namespace
2. ConfigMaps
3. Secrets
4. PostgreSQL
5. Redis
6. 网关 API
7. Web 界面

## 本地测试

### 端口转发

```bash
kubectl port-forward -n vehicle-iot-gateway svc/web-service 3000:80
```

访问: http://localhost:3000

### 开发模式

```bash
cd web
npm install
npm run dev
```

访问: http://localhost:3000

## 验证部署

```bash
# 查看 Pod 状态
kubectl get pods -n vehicle-iot-gateway -l app=web

# 查看服务
kubectl get svc web-service -n vehicle-iot-gateway

# 查看日志
kubectl logs -n vehicle-iot-gateway -l app=web --tail=50

# 测试健康检查
curl http://<NODE-IP>:30080/health
```

## 故障排查

### Pod 无法启动

```bash
kubectl describe pod -n vehicle-iot-gateway -l app=web
kubectl logs -n vehicle-iot-gateway -l app=web
```

### 无法访问

```bash
# 检查服务
kubectl get svc -n vehicle-iot-gateway

# 检查端口
kubectl get svc web-service -n vehicle-iot-gateway -o yaml
```

## 更新部署

```bash
# 重新构建镜像
docker build -t vehicle-iot-gateway-web:latest web/

# 重启服务
kubectl rollout restart deployment/web -n vehicle-iot-gateway
```

## 详细文档

查看 [KUBERNETES_DEPLOYMENT.md](KUBERNETES_DEPLOYMENT.md) 了解更多详情。
