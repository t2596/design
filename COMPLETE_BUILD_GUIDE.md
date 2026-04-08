# 完整镜像构建指南

## 概述

本项目包含两个Docker镜像：
1. **Gateway镜像** - 后端API服务（Python + FastAPI）
2. **Web镜像** - 前端界面（React + Nginx）

## 🚀 快速开始

### 方式1：一键构建所有镜像

```bash
# 构建Gateway和Web镜像
bash build-all-images.sh -r your-username -g v1.0 -w v1.0 -p
```

### 方式2：分别构建

```bash
# 构建Gateway镜像
bash build-and-push.sh -r your-username -v v1.0 -p

# 构建Web镜像
bash build-web.sh -r your-username -v v1.0 -p
```

### 方式3：快速构建（本地测试）

```bash
# 快速构建Gateway
bash quick-build.sh

# 快速构建Web
cd web
docker build -t vehicle-iot-web:latest .
cd ..
```

## 📦 镜像说明

### Gateway镜像

**技术栈：**
- Python 3.9
- FastAPI
- PostgreSQL客户端
- Redis客户端
- 国密算法库

**镜像大小：** ~200MB

**构建时间：** 2-3分钟

**Dockerfile位置：** `./Dockerfile`

### Web镜像

**技术栈：**
- React 18
- Vite
- Nginx Alpine

**镜像大小：** ~25MB

**构建时间：** 5-8分钟（包含npm install）

**Dockerfile位置：** `./web/Dockerfile`

## 🔧 详细构建步骤

### 构建Gateway镜像

#### 步骤1：准备

```bash
# 确保在项目根目录
pwd
# 应该显示: /path/to/vehicle-iot-gateway
```

#### 步骤2：构建

```bash
# 使用脚本（推荐）
bash build-and-push.sh -r your-username -v v1.0

# 或手动构建
docker build -t your-username/vehicle-iot-gateway:v1.0 .
docker tag your-username/vehicle-iot-gateway:v1.0 your-username/vehicle-iot-gateway:latest
```

#### 步骤3：测试

```bash
# 运行容器
docker run --rm -p 8000:8000 \
  -e POSTGRES_HOST=localhost \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=vehicle_iot_gateway \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e REDIS_HOST=localhost \
  -e REDIS_PORT=6379 \
  your-username/vehicle-iot-gateway:v1.0

# 测试API
curl http://localhost:8000/health
```

#### 步骤4：推送

```bash
docker login
docker push your-username/vehicle-iot-gateway:v1.0
docker push your-username/vehicle-iot-gateway:latest
```

### 构建Web镜像

#### 步骤1：准备

```bash
# 进入web目录
cd web
```

#### 步骤2：构建

```bash
# 使用脚本（推荐）
cd ..
bash build-web.sh -r your-username -v v1.0

# 或手动构建
cd web
docker build -t your-username/vehicle-iot-web:v1.0 .
docker tag your-username/vehicle-iot-web:v1.0 your-username/vehicle-iot-web:latest
cd ..
```

#### 步骤3：测试

```bash
# 运行容器
docker run --rm -p 8080:80 your-username/vehicle-iot-web:v1.0

# 浏览器访问
# http://localhost:8080

# 测试健康检查
curl http://localhost:8080/health
```

#### 步骤4：推送

```bash
docker login
docker push your-username/vehicle-iot-web:v1.0
docker push your-username/vehicle-iot-web:latest
```

## 🎯 使用不同的镜像仓库

### Docker Hub

```bash
# 登录
docker login

# 构建所有镜像
bash build-all-images.sh -r username -g v1.0 -w v1.0 -p
```

### 阿里云容器镜像服务

```bash
# 登录
docker login registry.cn-hangzhou.aliyuncs.com

# 构建所有镜像
bash build-all-images.sh \
  -r registry.cn-hangzhou.aliyuncs.com/your-namespace \
  -g v1.0 -w v1.0 -p
```

### Harbor私有仓库

```bash
# 登录
docker login harbor.example.com

# 构建所有镜像
bash build-all-images.sh \
  -r harbor.example.com/vehicle-iot \
  -g v1.0 -w v1.0 -p
```

## 📝 更新Kubernetes配置

### 更新Gateway配置

编辑 `deployment/kubernetes/gateway-deployment.yaml`：

```yaml
spec:
  containers:
  - name: gateway
    image: your-username/vehicle-iot-gateway:v1.0  # 修改这里
    imagePullPolicy: Always
```

### 更新Web配置

编辑 `deployment/kubernetes/web-deployment.yaml`：

```yaml
spec:
  containers:
  - name: web
    image: your-username/vehicle-iot-web:v1.0  # 修改这里
    imagePullPolicy: Always
```

## 🚀 部署到Kubernetes

### 完整部署流程

```bash
# 1. 构建所有镜像
bash build-all-images.sh -r your-username -g v1.0 -w v1.0 -p

# 2. 更新K8s配置
# 编辑 deployment/kubernetes/gateway-deployment.yaml
# 编辑 deployment/kubernetes/web-deployment.yaml

# 3. 部署
cd deployment/kubernetes
bash deploy-all.sh

# 4. 验证
kubectl get pods -n vehicle-iot-gateway
```

### 仅更新Gateway

```bash
# 1. 构建Gateway镜像
bash build-and-push.sh -r your-username -v v1.1 -p

# 2. 更新配置
# 编辑 deployment/kubernetes/gateway-deployment.yaml

# 3. 应用更新
kubectl apply -f deployment/kubernetes/gateway-deployment.yaml

# 4. 查看滚动更新状态
kubectl rollout status deployment/gateway -n vehicle-iot-gateway
```

### 仅更新Web

```bash
# 1. 构建Web镜像
bash build-web.sh -r your-username -v v1.1 -p

# 2. 更新配置
# 编辑 deployment/kubernetes/web-deployment.yaml

# 3. 应用更新
kubectl apply -f deployment/kubernetes/web-deployment.yaml

# 4. 查看滚动更新状态
kubectl rollout status deployment/web -n vehicle-iot-gateway
```

## 🔍 验证部署

### 检查镜像

```bash
# 查看本地镜像
docker images | grep vehicle-iot

# 预期输出：
# vehicle-iot-gateway  v1.0    xxx    200MB
# vehicle-iot-web      v1.0    xxx    25MB
```

### 检查Pod

```bash
# 查看所有Pod
kubectl get pods -n vehicle-iot-gateway

# 预期输出：
# NAME                        READY   STATUS    RESTARTS   AGE
# gateway-xxx                 1/1     Running   0          2m
# web-xxx                     1/1     Running   0          2m
# postgres-xxx                1/1     Running   0          5m
# redis-xxx                   1/1     Running   0          5m
```

### 测试Gateway

```bash
# 端口转发
kubectl port-forward svc/gateway-service 8000:8000 -n vehicle-iot-gateway

# 测试API
curl http://localhost:8000/health
```

### 测试Web

```bash
# 端口转发
kubectl port-forward svc/web-service 8080:80 -n vehicle-iot-gateway

# 浏览器访问
# http://localhost:8080
```

## 📊 镜像对比

| 镜像 | 基础镜像 | 大小 | 构建时间 | 说明 |
|-----|---------|------|---------|------|
| Gateway | python:3.9-slim | ~200MB | 2-3分钟 | 后端API服务 |
| Web | nginx:alpine | ~25MB | 5-8分钟 | 前端静态文件 |

## 🛠️ 可用脚本

| 脚本 | 说明 | 用途 |
|-----|------|------|
| `build-all-images.sh` | 构建所有镜像 | 一次性构建Gateway和Web |
| `build-and-push.sh` | 构建Gateway镜像 | 完整的Gateway构建流程 |
| `build-web.sh` | 构建Web镜像 | 完整的Web构建流程 |
| `quick-build.sh` | 快速构建Gateway | 本地测试用 |

## 💡 最佳实践

### 1. 版本管理

```bash
# 使用语义化版本
bash build-all-images.sh -r username -g v1.0.0 -w v1.0.0 -p

# 使用Git提交哈希
GIT_HASH=$(git rev-parse --short HEAD)
bash build-all-images.sh -r username -g ${GIT_HASH} -w ${GIT_HASH} -p
```

### 2. 构建优化

```bash
# 使用BuildKit加速
export DOCKER_BUILDKIT=1
bash build-all-images.sh -r username -g v1.0 -w v1.0 -p

# 并行构建
bash build-and-push.sh -r username -v v1.0 &
bash build-web.sh -r username -v v1.0 &
wait
```

### 3. 镜像清理

```bash
# 清理未使用的镜像
docker image prune -a

# 清理构建缓存
docker builder prune
```

## ❓ 常见问题

### Q1: Gateway镜像构建失败

**可能原因：**
- requirements.txt中的依赖安装失败
- 网络问题

**解决方案：**
```bash
# 使用国内pip镜像
docker build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple -t gateway:v1.0 .
```

### Q2: Web镜像构建失败

**可能原因：**
- npm install失败
- 网络问题

**解决方案：**
```bash
# 修改Dockerfile使用国内npm镜像
# 在RUN npm install前添加：
# RUN npm config set registry https://registry.npmmirror.com
```

### Q3: 镜像推送失败

**解决方案：**
```bash
# 重新登录
docker login

# 检查镜像名称格式
docker images | grep vehicle-iot
```

### Q4: Kubernetes拉取镜像失败

**解决方案：**
```bash
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

## 📚 相关文档

- **Gateway镜像详解**: `BUILD_AND_PUSH_IMAGE.md`
- **Web镜像详解**: `BUILD_WEB_IMAGE.md`
- **完整部署流程**: `COMPLETE_DEPLOYMENT_GUIDE.md`
- **K8s一键部署**: `K8S_ONE_CLICK_DEPLOY_README.md`

## 🎉 总结

### 最简构建流程

```bash
# 一键构建所有镜像
bash build-all-images.sh -r username -g v1.0 -w v1.0 -p

# 部署到K8s
cd deployment/kubernetes && bash deploy-all.sh
```

### 完整构建流程

```bash
# 1. 构建Gateway
bash build-and-push.sh -r username -v v1.0 -p

# 2. 构建Web
bash build-web.sh -r username -v v1.0 -p

# 3. 更新K8s配置
# 编辑 deployment/kubernetes/*.yaml

# 4. 部署
cd deployment/kubernetes && bash deploy-all.sh

# 5. 验证
kubectl get pods -n vehicle-iot-gateway
```

---

**提示**: 所有脚本都支持命令行参数，使用 `-h` 查看帮助信息。
