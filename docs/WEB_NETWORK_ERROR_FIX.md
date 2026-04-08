# Web 界面 Network Error 修复指南

## 问题原因

Web 前端在浏览器中运行，无法直接访问 K8s 内部服务名（如 `gateway-service:8000`）。

## 解决方案

前端应该使用**相对路径**，通过 Nginx 代理访问后端 API。

## 修复步骤

### 1. 更新前端代码

已修改 `web/src/api/client.js`，使用空字符串作为 `API_BASE_URL`（相对路径）。

### 2. 更新 K8s 部署配置

已修改 `deployment/kubernetes/web-deployment.yaml`，将 `VITE_API_BASE_URL` 设置为空字符串。

### 3. 重新构建 Web 镜像

```bash
cd web

# 构建镜像（使用空的 API_BASE_URL）
docker build -t vehicle-iot-gateway-web:latest .

# 如果使用镜像仓库，推送镜像
docker tag vehicle-iot-gateway-web:latest <registry>/vehicle-iot-gateway-web:latest
docker push <registry>/vehicle-iot-gateway-web:latest
```

### 4. 重新部署 Web 服务

```bash
# 应用更新的部署配置
kubectl apply -f deployment/kubernetes/web-deployment.yaml

# 重启 Web Pod（强制拉取新镜像）
kubectl rollout restart deployment/web -n vehicle-iot-gateway

# 查看部署状态
kubectl get pods -n vehicle-iot-gateway -l app=web
```

### 5. 验证修复

```bash
# 获取 Web 服务的 NodePort
kubectl get svc web-service -n vehicle-iot-gateway

# 访问 Web 界面
# http://<节点IP>:30080
```

## 工作原理

### 修复前（错误）

```
浏览器 → 前端代码（API_BASE_URL=http://gateway-service:8000）
         ↓
         ❌ 浏览器无法解析 gateway-service（K8s 内部服务名）
```

### 修复后（正确）

```
浏览器 → 前端代码（API_BASE_URL=""，相对路径）
         ↓
         /api/vehicles/online
         ↓
      Nginx 代理
         ↓
         http://gateway-service:8000/api/vehicles/online
         ↓
      网关服务 ✅
```

## 架构说明

```
┌─────────────────────────────────────────────────────────┐
│ 用户浏览器                                               │
│                                                         │
│  http://<节点IP>:30080                                  │
│         ↓                                               │
│  前端代码（React + Vite）                               │
│  API 调用：/api/vehicles/online（相对路径）             │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ K8s - Web Pod (Nginx)                                   │
│                                                         │
│  location /api/ {                                       │
│    proxy_pass http://gateway-service:8000;              │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ K8s - Gateway Pod (FastAPI)                             │
│                                                         │
│  /api/vehicles/online                                   │
│  /api/certificates/issue                                │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

## 常见问题

### Q1: 为什么不能直接使用 gateway-service:8000？

A: 因为前端代码在**用户浏览器**中运行，浏览器无法解析 K8s 内部的服务名。只有 K8s 集群内部的 Pod 才能使用服务名。

### Q2: 本地开发怎么办？

A: 本地开发时，可以设置环境变量：

```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TOKEN=dev-token-12345
```

### Q3: 如何验证 Nginx 代理是否工作？

A: 进入 Web Pod 测试：

```bash
# 进入 Web Pod
kubectl exec -it -n vehicle-iot-gateway <web-pod-name> -- sh

# 测试 Nginx 代理
curl http://localhost/api/vehicles/online -H "Authorization: Bearer dev-token-12345"
```

### Q4: 还是显示 Network Error？

A: 检查以下几点：

1. **网关服务是否正常运行**：
```bash
kubectl get pods -n vehicle-iot-gateway -l app=gateway
kubectl logs -n vehicle-iot-gateway <gateway-pod-name>
```

2. **网关服务是否可访问**：
```bash
kubectl exec -it -n vehicle-iot-gateway <web-pod-name> -- \
  curl http://gateway-service:8000/api/vehicles/online \
  -H "Authorization: Bearer dev-token-12345"
```

3. **浏览器控制台错误**：
   - 打开浏览器开发者工具（F12）
   - 查看 Console 和 Network 标签
   - 检查具体的错误信息

4. **API Token 是否正确**：
```bash
kubectl get secret gateway-secrets -n vehicle-iot-gateway -o jsonpath='{.data.API_TOKEN}' | base64 -d
```

## 相关文档

- [Web 部署指南](../web/KUBERNETES_DEPLOYMENT.md)
- [Nginx 配置](../web/nginx.conf)
- [API 客户端配置](../web/src/api/client.js)
