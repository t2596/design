# Web前端镜像构建指南

## 概述

Web前端使用React + Vite构建，采用多阶段Docker构建，最终使用Nginx提供静态文件服务。

## 技术栈

- **前端框架**: React 18
- **构建工具**: Vite
- **路由**: React Router
- **HTTP客户端**: Axios
- **图表**: Recharts
- **Web服务器**: Nginx (Alpine)

## 镜像构建流程

### 多阶段构建说明

Web的Dockerfile使用两阶段构建：

1. **构建阶段** (node:18-alpine)
   - 安装npm依赖
   - 使用Vite构建生产版本
   - 生成优化的静态文件

2. **运行阶段** (nginx:alpine)
   - 复制构建产物到Nginx
   - 配置Nginx反向代理
   - 提供静态文件服务

## 方式1：使用快速构建脚本

### 创建Web构建脚本

创建 `build-web.sh`：

```bash
#!/bin/bash

# Web前端镜像构建脚本

set -e

# 配置变量
REGISTRY="your-username"
IMAGE_NAME="vehicle-iot-web"
VERSION="v1.0"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}构建Web前端镜像${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 进入web目录
cd web

# 检查必要文件
echo -e "${YELLOW}检查必要文件...${NC}"
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}错误: 找不到Dockerfile${NC}"
    exit 1
fi

if [ ! -f "package.json" ]; then
    echo -e "${RED}错误: 找不到package.json${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 文件检查通过${NC}"
echo ""

# 构建镜像
echo -e "${YELLOW}构建镜像...${NC}"
docker build -t ${REGISTRY}/${IMAGE_NAME}:${VERSION} .

if [ $? -eq 0 ]; then
    docker tag ${REGISTRY}/${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:latest
    echo -e "${GREEN}✓ 镜像构建成功${NC}"
else
    echo -e "${RED}✗ 镜像构建失败${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}镜像信息:${NC}"
docker images | grep ${IMAGE_NAME}

echo ""
echo -e "${GREEN}下一步:${NC}"
echo "  1. 测试镜像: docker run --rm -p 8080:80 ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
echo "  2. 推送镜像: docker push ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
echo "  3. 更新K8s配置: deployment/kubernetes/web-deployment.yaml"
```

使用脚本：

```bash
chmod +x build-web.sh
./build-web.sh
```

## 方式2：手动构建

### 步骤1：进入web目录

```bash
cd web
```

### 步骤2：构建镜像

```bash
# 构建镜像
docker build -t your-username/vehicle-iot-web:v1.0 .

# 打标签
docker tag your-username/vehicle-iot-web:v1.0 your-username/vehicle-iot-web:latest
```

### 步骤3：测试镜像

```bash
# 运行容器
docker run --rm -p 8080:80 your-username/vehicle-iot-web:v1.0

# 访问测试
# 浏览器打开: http://localhost:8080
```

### 步骤4：推送镜像

```bash
# 登录镜像仓库
docker login

# 推送镜像
docker push your-username/vehicle-iot-web:v1.0
docker push your-username/vehicle-iot-web:latest
```

## 方式3：使用不同的镜像仓库

### Docker Hub

```bash
cd web
docker login
docker build -t username/vehicle-iot-web:v1.0 .
docker push username/vehicle-iot-web:v1.0
```

### 阿里云

```bash
cd web
docker login registry.cn-hangzhou.aliyuncs.com
docker build -t registry.cn-hangzhou.aliyuncs.com/namespace/vehicle-iot-web:v1.0 .
docker push registry.cn-hangzhou.aliyuncs.com/namespace/vehicle-iot-web:v1.0
```

### Harbor

```bash
cd web
docker login harbor.example.com
docker build -t harbor.example.com/project/vehicle-iot-web:v1.0 .
docker push harbor.example.com/project/vehicle-iot-web:v1.0
```

## 构建优化

### 使用.dockerignore

在 `web/` 目录创建 `.dockerignore`：

```
node_modules
dist
.git
.gitignore
*.md
.env
.env.local
.vscode
.idea
npm-debug.log
yarn-error.log
```

### 优化构建速度

#### 方式1：使用构建缓存

```bash
# 使用BuildKit
DOCKER_BUILDKIT=1 docker build -t vehicle-iot-web:v1.0 .
```

#### 方式2：使用国内npm镜像

修改 `web/Dockerfile`：

```dockerfile
# 阶段 1: 构建
FROM node:18-alpine AS builder

WORKDIR /app

# 设置npm镜像
RUN npm config set registry https://registry.npmmirror.com

# 复制 package 文件
COPY package.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# 阶段 2: 生产环境
FROM nginx:alpine

# 复制构建产物到 nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
```

## 更新Kubernetes配置

编辑 `deployment/kubernetes/web-deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: vehicle-iot-gateway
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: your-username/vehicle-iot-web:v1.0  # 修改这里
        imagePullPolicy: Always
        ports:
        - containerPort: 80
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
```

## 部署到Kubernetes

```bash
# 应用配置
kubectl apply -f deployment/kubernetes/web-deployment.yaml

# 查看状态
kubectl get pods -l app=web -n vehicle-iot-gateway

# 查看日志
kubectl logs -f deployment/web -n vehicle-iot-gateway
```

## 验证部署

### 1. 检查Pod状态

```bash
kubectl get pods -l app=web -n vehicle-iot-gateway

# 预期输出
NAME                   READY   STATUS    RESTARTS   AGE
web-xxx                1/1     Running   0          2m
```

### 2. 检查服务

```bash
kubectl get svc -l app=web -n vehicle-iot-gateway
```

### 3. 访问Web界面

```bash
# 获取服务地址
kubectl get svc web-service -n vehicle-iot-gateway

# 或使用端口转发
kubectl port-forward svc/web-service 8080:80 -n vehicle-iot-gateway

# 浏览器访问: http://localhost:8080
```

### 4. 测试API代理

Web的Nginx配置了API反向代理，测试是否正常：

```bash
# 通过Web访问API
curl http://localhost:8080/api/health

# 应该返回Gateway的健康检查响应
```

## 本地开发

如果需要本地开发Web前端：

```bash
cd web

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问: http://localhost:5173
```

## 环境变量配置

Web前端可以通过环境变量配置API地址。

### 创建 .env 文件

在 `web/` 目录创建 `.env`：

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 在代码中使用

```javascript
// src/api/config.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default API_BASE_URL;
```

### 构建时传入环境变量

```bash
# 构建时指定API地址
docker build --build-arg API_URL=http://api.example.com -t vehicle-iot-web:v1.0 .
```

需要修改Dockerfile：

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# 接收构建参数
ARG API_URL
ENV VITE_API_BASE_URL=$API_URL

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

# ... 其余部分不变
```

## 完整构建和部署脚本

创建 `build-and-deploy-web.sh`：

```bash
#!/bin/bash

# Web前端完整构建和部署脚本

set -e

REGISTRY="your-username"
IMAGE_NAME="vehicle-iot-web"
VERSION="v1.0"

echo "=========================================="
echo "Web前端构建和部署"
echo "=========================================="
echo ""

# 1. 构建镜像
echo "步骤1: 构建镜像..."
cd web
docker build -t ${REGISTRY}/${IMAGE_NAME}:${VERSION} .
docker tag ${REGISTRY}/${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:latest
cd ..

echo "✓ 镜像构建成功"
echo ""

# 2. 推送镜像
echo "步骤2: 推送镜像..."
read -p "是否推送镜像? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker push ${REGISTRY}/${IMAGE_NAME}:${VERSION}
    docker push ${REGISTRY}/${IMAGE_NAME}:latest
    echo "✓ 镜像推送成功"
else
    echo "跳过推送"
fi

echo ""

# 3. 更新K8s配置
echo "步骤3: 更新Kubernetes配置..."
read -p "是否更新K8s配置? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 备份原配置
    cp deployment/kubernetes/web-deployment.yaml deployment/kubernetes/web-deployment.yaml.bak
    
    # 更新镜像地址（需要sed命令）
    sed -i "s|image:.*vehicle-iot-web.*|image: ${REGISTRY}/${IMAGE_NAME}:${VERSION}|g" deployment/kubernetes/web-deployment.yaml
    
    echo "✓ 配置已更新"
else
    echo "跳过配置更新"
fi

echo ""

# 4. 部署到K8s
echo "步骤4: 部署到Kubernetes..."
read -p "是否部署到K8s? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl apply -f deployment/kubernetes/web-deployment.yaml
    
    echo "等待Pod就绪..."
    kubectl wait --for=condition=ready pod -l app=web -n vehicle-iot-gateway --timeout=120s
    
    echo "✓ 部署成功"
    
    echo ""
    echo "Pod状态:"
    kubectl get pods -l app=web -n vehicle-iot-gateway
else
    echo "跳过部署"
fi

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="
```

## 常见问题

### Q1: 构建失败，提示npm install错误

**解决方案：**
```bash
# 清理node_modules
cd web
rm -rf node_modules package-lock.json

# 使用国内镜像
npm config set registry https://registry.npmmirror.com
npm install
```

### Q2: 镜像太大

**解决方案：**
- 使用多阶段构建（已使用）
- 使用alpine基础镜像（已使用）
- 添加.dockerignore排除不必要文件

当前镜像大小约：
- 构建阶段：~500MB
- 最终镜像：~25MB（仅包含静态文件和Nginx）

### Q3: Nginx配置不生效

**解决方案：**
```bash
# 检查nginx配置
kubectl exec -it deployment/web -n vehicle-iot-gateway -- cat /etc/nginx/conf.d/default.conf

# 重新加载nginx
kubectl exec -it deployment/web -n vehicle-iot-gateway -- nginx -s reload
```

### Q4: API代理不工作

**解决方案：**
检查nginx配置中的proxy_pass地址：
```nginx
location /api/ {
    proxy_pass http://gateway-service:8000;  # 确保服务名正确
    # ...
}
```

确保Gateway服务名称正确：
```bash
kubectl get svc -n vehicle-iot-gateway | grep gateway
```

## 镜像大小对比

```bash
# 查看镜像大小
docker images | grep vehicle-iot

# 预期输出：
# vehicle-iot-web    v1.0    xxx    25MB
# vehicle-iot-gateway v1.0   xxx    200MB
```

## 快速参考

### 构建Web镜像
```bash
cd web
docker build -t username/vehicle-iot-web:v1.0 .
```

### 推送Web镜像
```bash
docker push username/vehicle-iot-web:v1.0
```

### 部署Web
```bash
kubectl apply -f deployment/kubernetes/web-deployment.yaml
```

### 查看Web日志
```bash
kubectl logs -f deployment/web -n vehicle-iot-gateway
```

### 访问Web界面
```bash
kubectl port-forward svc/web-service 8080:80 -n vehicle-iot-gateway
# 浏览器访问: http://localhost:8080
```

## 总结

Web前端镜像构建特点：

✅ **多阶段构建** - 最终镜像仅25MB
✅ **Nginx服务** - 高性能静态文件服务
✅ **API代理** - 自动代理到Gateway
✅ **SPA路由** - 支持React Router
✅ **健康检查** - 内置/health端点
✅ **静态资源缓存** - 优化加载速度

构建流程简单：
1. 进入web目录
2. 构建镜像
3. 推送镜像
4. 更新K8s配置
5. 部署

---

**提示**: Web镜像构建时间较长（需要npm install），建议使用构建缓存加速。
