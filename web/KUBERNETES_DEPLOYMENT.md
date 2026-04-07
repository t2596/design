# Web 界面 Kubernetes 部署指南

## 概述

Web 管理平台是一个基于 React + Vite 的单页应用（SPA），提供可视化的车联网安全通信网关管理界面。

## 功能特性

- 📊 实时监控仪表板
- 🚗 车辆状态监控
- 📜 证书管理
- 📝 审计日志查询
- ⚙️ 安全配置管理
- 📈 性能指标展示

## 架构说明

```
用户浏览器
    ↓
Nginx (Web Service)
    ↓
React SPA (静态文件)
    ↓ (API 请求)
Gateway Service (后端 API)
```

## 部署步骤

### 步骤 1: 构建 Docker 镜像

```bash
cd web

# 构建镜像
docker build -t vehicle-iot-gateway-web:latest .

# 如果使用镜像仓库，推送镜像
docker tag vehicle-iot-gateway-web:latest your-registry/vehicle-iot-gateway-web:latest
docker push your-registry/vehicle-iot-gateway-web:latest
```

### 步骤 2: 更新 Secrets（如果需要）

确保 `deployment/kubernetes/secrets.yaml` 包含 `API_TOKEN`：

```yaml
stringData:
  API_TOKEN: "dev-token-12345"  # 生产环境请修改
```

应用 Secrets：

```bash
kubectl apply -f deployment/kubernetes/secrets.yaml
```

### 步骤 3: 部署 Web 服务

```bash
kubectl apply -f deployment/kubernetes/web-deployment.yaml
```

### 步骤 4: 验证部署

```bash
# 查看 Pod 状态
kubectl get pods -n vehicle-iot-gateway -l app=web

# 查看服务
kubectl get svc web-service -n vehicle-iot-gateway

# 查看日志
kubectl logs -n vehicle-iot-gateway -l app=web --tail=50
```

## 访问 Web 界面

### 方法 1: NodePort（默认配置）

Web 服务使用 NodePort 30080：

```bash
# 获取节点 IP
kubectl get nodes -o wide

# 访问 Web 界面
http://<NODE-IP>:30080
```

### 方法 2: 端口转发（本地测试）

```bash
kubectl port-forward -n vehicle-iot-gateway svc/web-service 3000:80
```

然后访问: http://localhost:3000

### 方法 3: LoadBalancer

修改 `web-deployment.yaml` 中的 Service 类型：

```yaml
spec:
  type: LoadBalancer
```

然后：

```bash
kubectl apply -f deployment/kubernetes/web-deployment.yaml

# 获取外部 IP
kubectl get svc web-service -n vehicle-iot-gateway
```

### 方法 4: Ingress（推荐用于生产）

创建 Ingress 配置：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  namespace: vehicle-iot-gateway
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: gateway.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

## 配置说明

### 环境变量

Web 容器支持以下环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `http://gateway-service:8000` |
| `VITE_API_TOKEN` | API 认证令牌 | 从 Secret 读取 |

### Nginx 配置

`nginx.conf` 提供以下功能：
- SPA 路由支持（所有路由返回 index.html）
- API 代理到后端网关
- 静态资源缓存
- Gzip 压缩
- 健康检查端点

### 资源限制

默认资源配置：

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

根据实际负载调整。

## 开发模式

### 本地开发

```bash
cd web

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问
http://localhost:3000
```

### 配置后端 API

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
VITE_API_BASE_URL=http://8.147.61.78:30546
VITE_API_TOKEN=dev-token-12345
```

## 故障排查

### 问题 1: Pod 无法启动

**检查镜像：**

```bash
kubectl describe pod -n vehicle-iot-gateway -l app=web
```

**常见原因：**
- 镜像不存在或拉取失败
- 资源不足

### 问题 2: 无法访问 API

**检查 API 代理配置：**

```bash
# 进入容器
kubectl exec -it -n vehicle-iot-gateway deployment/web -- /bin/sh

# 测试后端连接
wget -O- http://gateway-service:8000/health
```

**检查 nginx 配置：**

```bash
kubectl exec -it -n vehicle-iot-gateway deployment/web -- cat /etc/nginx/conf.d/default.conf
```

### 问题 3: 页面空白

**查看浏览器控制台：**
- 检查是否有 JavaScript 错误
- 检查 API 请求是否成功

**查看 nginx 日志：**

```bash
kubectl logs -n vehicle-iot-gateway -l app=web
```

### 问题 4: API 认证失败

**检查 API Token：**

```bash
# 查看 Secret
kubectl get secret gateway-secrets -n vehicle-iot-gateway -o yaml

# 确认 API_TOKEN 存在
```

## 更新部署

### 更新镜像

```bash
# 重新构建镜像
docker build -t vehicle-iot-gateway-web:latest web/

# 推送镜像
docker push your-registry/vehicle-iot-gateway-web:latest

# 重启 Deployment
kubectl rollout restart deployment/web -n vehicle-iot-gateway

# 查看更新状态
kubectl rollout status deployment/web -n vehicle-iot-gateway
```

### 更新配置

```bash
# 更新 Secrets
kubectl apply -f deployment/kubernetes/secrets.yaml

# 重启 Web 服务
kubectl rollout restart deployment/web -n vehicle-iot-gateway
```

## 扩缩容

```bash
# 扩展副本数
kubectl scale deployment/web -n vehicle-iot-gateway --replicas=3

# 查看副本状态
kubectl get pods -n vehicle-iot-gateway -l app=web
```

## 监控和日志

### 查看日志

```bash
# 实时日志
kubectl logs -n vehicle-iot-gateway -l app=web -f

# 最近 100 行
kubectl logs -n vehicle-iot-gateway -l app=web --tail=100

# 特定 Pod
kubectl logs -n vehicle-iot-gateway <pod-name>
```

### 查看资源使用

```bash
# CPU 和内存使用
kubectl top pods -n vehicle-iot-gateway -l app=web
```

## 安全建议

### 生产环境配置

1. **修改 API Token**：
   ```yaml
   API_TOKEN: "your-strong-random-token"
   ```

2. **启用 HTTPS**：
   - 使用 Ingress + cert-manager
   - 配置 TLS 证书

3. **限制访问**：
   - 配置 NetworkPolicy
   - 使用 IP 白名单

4. **资源限制**：
   - 设置合理的 CPU 和内存限制
   - 配置 HPA（水平自动扩缩容）

### HTTPS 配置示例

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  namespace: vehicle-iot-gateway
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - gateway.example.com
    secretName: gateway-tls
  rules:
  - host: gateway.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

## 性能优化

### 1. 启用 CDN

将静态资源部署到 CDN：

```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 2. 启用 Gzip

已在 `nginx.conf` 中配置。

### 3. 使用 HTTP/2

在 Ingress 中启用 HTTP/2：

```yaml
annotations:
  nginx.ingress.kubernetes.io/http2-push-preload: "true"
```

## 相关文档

- [Web 快速开始](QUICKSTART.md) - 本地开发指南
- [Web README](README.md) - 功能说明
- [API 文档](../docs/API.md) - 后端 API 接口
- [Kubernetes 部署](../deployment/kubernetes/README.md) - 完整部署指南

## 总结

Web 界面部署后：
- ✅ 提供可视化管理界面
- ✅ 通过 Nginx 代理 API 请求
- ✅ 支持多副本部署
- ✅ 自动健康检查
- ✅ 静态资源缓存优化
