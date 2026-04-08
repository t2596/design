# Kubernetes 镜像构建和推送指南

## 概述

本指南介绍如何构建包含问题2和问题3修复的Docker镜像，并推送到镜像仓库供Kubernetes使用。

## 前置条件

- ✅ Docker已安装并运行
- ✅ 有权访问Docker镜像仓库（Docker Hub、阿里云、Harbor等）
- ✅ 已完成代码修改（问题2和问题3）

## 方式1：使用Docker Hub（推荐用于测试）

### 步骤1：登录Docker Hub

```bash
docker login

# 输入用户名和密码
Username: your-username
Password: your-password
```

### 步骤2：构建镜像

```bash
# 在项目根目录执行
docker build -t your-username/vehicle-iot-gateway:latest .

# 或者指定版本号
docker build -t your-username/vehicle-iot-gateway:v1.0 .
```

### 步骤3：推送镜像

```bash
# 推送latest标签
docker push your-username/vehicle-iot-gateway:latest

# 推送版本标签
docker push your-username/vehicle-iot-gateway:v1.0
```

### 步骤4：更新Kubernetes部署配置

编辑 `deployment/kubernetes/gateway-deployment.yaml`：

```yaml
spec:
  containers:
  - name: gateway
    image: your-username/vehicle-iot-gateway:latest
    imagePullPolicy: Always
```

### 步骤5：部署到Kubernetes

```bash
cd deployment/kubernetes
kubectl apply -f gateway-deployment.yaml
```

## 方式2：使用阿里云容器镜像服务

### 步骤1：登录阿里云镜像仓库

```bash
# 登录阿里云镜像仓库
docker login --username=your-aliyun-username registry.cn-hangzhou.aliyuncs.com

# 输入密码
Password: your-password
```

### 步骤2：构建镜像

```bash
# 构建镜像并打标签
docker build -t registry.cn-hangzhou.aliyuncs.com/your-namespace/vehicle-iot-gateway:latest .

# 或者先构建再打标签
docker build -t vehicle-iot-gateway:latest .
docker tag vehicle-iot-gateway:latest registry.cn-hangzhou.aliyuncs.com/your-namespace/vehicle-iot-gateway:latest
```

### 步骤3：推送镜像

```bash
docker push registry.cn-hangzhou.aliyuncs.com/your-namespace/vehicle-iot-gateway:latest
```

### 步骤4：更新Kubernetes部署配置

编辑 `deployment/kubernetes/gateway-deployment.yaml`：

```yaml
spec:
  containers:
  - name: gateway
    image: registry.cn-hangzhou.aliyuncs.com/your-namespace/vehicle-iot-gateway:latest
    imagePullPolicy: Always
```

### 步骤5：创建镜像拉取密钥（如果是私有仓库）

```bash
kubectl create secret docker-registry aliyun-registry-secret \
  --docker-server=registry.cn-hangzhou.aliyuncs.com \
  --docker-username=your-aliyun-username \
  --docker-password=your-password \
  --docker-email=your-email@example.com \
  -n vehicle-iot-gateway
```

更新deployment配置：

```yaml
spec:
  imagePullSecrets:
  - name: aliyun-registry-secret
  containers:
  - name: gateway
    image: registry.cn-hangzhou.aliyuncs.com/your-namespace/vehicle-iot-gateway:latest
```

## 方式3：使用私有Harbor仓库

### 步骤1：登录Harbor

```bash
docker login harbor.your-domain.com

# 输入用户名和密码
Username: admin
Password: your-password
```

### 步骤2：构建镜像

```bash
docker build -t harbor.your-domain.com/vehicle-iot/gateway:latest .
```

### 步骤3：推送镜像

```bash
docker push harbor.your-domain.com/vehicle-iot/gateway:latest
```

### 步骤4：创建镜像拉取密钥

```bash
kubectl create secret docker-registry harbor-registry-secret \
  --docker-server=harbor.your-domain.com \
  --docker-username=admin \
  --docker-password=your-password \
  --docker-email=admin@example.com \
  -n vehicle-iot-gateway
```

### 步骤5：更新Kubernetes部署配置

```yaml
spec:
  imagePullSecrets:
  - name: harbor-registry-secret
  containers:
  - name: gateway
    image: harbor.your-domain.com/vehicle-iot/gateway:latest
    imagePullPolicy: Always
```

## 方式4：本地镜像（仅用于单节点测试）

如果Kubernetes运行在本地（如Minikube、Kind），可以直接使用本地镜像：

### 步骤1：构建镜像

```bash
docker build -t vehicle-iot-gateway:latest .
```

### 步骤2：加载镜像到Kubernetes

#### Minikube

```bash
# 方式1：使用Minikube的Docker环境
eval $(minikube docker-env)
docker build -t vehicle-iot-gateway:latest .

# 方式2：加载已有镜像
minikube image load vehicle-iot-gateway:latest
```

#### Kind

```bash
kind load docker-image vehicle-iot-gateway:latest --name your-cluster-name
```

### 步骤3：更新Kubernetes部署配置

```yaml
spec:
  containers:
  - name: gateway
    image: vehicle-iot-gateway:latest
    imagePullPolicy: Never  # 或 IfNotPresent
```

## 完整构建脚本

创建 `build-and-push.sh`：

```bash
#!/bin/bash

# 配置变量
REGISTRY="your-username"  # Docker Hub用户名或镜像仓库地址
IMAGE_NAME="vehicle-iot-gateway"
VERSION="v1.0"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}构建和推送Docker镜像${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 步骤1：检查Docker是否运行
echo -e "${YELLOW}步骤1: 检查Docker状态...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}错误: Docker未运行，请先启动Docker${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker运行正常${NC}"
echo ""

# 步骤2：构建镜像
echo -e "${YELLOW}步骤2: 构建Docker镜像...${NC}"
docker build -t ${REGISTRY}/${IMAGE_NAME}:${VERSION} .

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 镜像构建失败${NC}"
    exit 1
fi

# 同时打上latest标签
docker tag ${REGISTRY}/${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:latest

echo -e "${GREEN}✓ 镜像构建成功${NC}"
echo ""

# 步骤3：查看镜像
echo -e "${YELLOW}步骤3: 查看构建的镜像...${NC}"
docker images | grep ${IMAGE_NAME}
echo ""

# 步骤4：推送镜像
echo -e "${YELLOW}步骤4: 推送镜像到仓库...${NC}"
read -p "是否推送镜像到仓库? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 推送版本标签
    docker push ${REGISTRY}/${IMAGE_NAME}:${VERSION}
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}错误: 镜像推送失败，请检查登录状态${NC}"
        echo "提示: 运行 'docker login' 登录镜像仓库"
        exit 1
    fi
    
    # 推送latest标签
    docker push ${REGISTRY}/${IMAGE_NAME}:latest
    
    echo -e "${GREEN}✓ 镜像推送成功${NC}"
else
    echo -e "${YELLOW}跳过推送步骤${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "镜像信息:"
echo "  名称: ${REGISTRY}/${IMAGE_NAME}"
echo "  版本: ${VERSION}, latest"
echo ""
echo "下一步:"
echo "  1. 更新 deployment/kubernetes/gateway-deployment.yaml"
echo "  2. 运行: kubectl apply -f deployment/kubernetes/gateway-deployment.yaml"
echo "  3. 运行: kubectl rollout restart deployment/gateway -n vehicle-iot-gateway"
```

使用脚本：

```bash
chmod +x build-and-push.sh
./build-and-push.sh
```

## 验证镜像

### 1. 查看本地镜像

```bash
docker images | grep vehicle-iot-gateway
```

### 2. 测试镜像

```bash
# 运行容器测试
docker run --rm -p 8000:8000 your-username/vehicle-iot-gateway:latest

# 检查容器日志
docker logs <container-id>
```

### 3. 检查镜像大小

```bash
docker images your-username/vehicle-iot-gateway:latest --format "{{.Size}}"
```

## 优化镜像大小

### 使用多阶段构建

编辑 `Dockerfile`：

```dockerfile
# 第一阶段：构建
FROM python:3.9-slim as builder

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 第二阶段：运行
FROM python:3.9-slim

WORKDIR /app

# 从构建阶段复制依赖
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY . .

# 设置环境变量
ENV PATH=/root/.local/bin:$PATH

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 使用.dockerignore

创建 `.dockerignore`：

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.gitignore
.mypy_cache
.pytest_cache
.hypothesis
*.md
docs/
tests/
*.sh
deployment/
examples/
.kiro/
.vscode/
.pytest_cache/
*.sql
db/migrations/
```

## 常见问题

### Q1: 构建失败，提示找不到文件

**解决方案：**
```bash
# 确保在项目根目录执行
cd /path/to/vehicle-iot-gateway
docker build -t vehicle-iot-gateway:latest .
```

### Q2: 推送失败，提示未授权

**解决方案：**
```bash
# 重新登录
docker login

# 或指定仓库地址
docker login registry.cn-hangzhou.aliyuncs.com
```

### Q3: Kubernetes拉取镜像失败

**解决方案：**
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

### Q4: 镜像太大

**解决方案：**
- 使用更小的基础镜像（如 `python:3.9-slim` 或 `python:3.9-alpine`）
- 使用多阶段构建
- 清理不必要的文件
- 使用 `.dockerignore` 排除不需要的文件

### Q5: 镜像版本管理

**建议：**
```bash
# 使用语义化版本
docker build -t your-username/vehicle-iot-gateway:v1.0.0 .
docker build -t your-username/vehicle-iot-gateway:v1.0.1 .

# 使用Git提交哈希
GIT_HASH=$(git rev-parse --short HEAD)
docker build -t your-username/vehicle-iot-gateway:${GIT_HASH} .

# 使用日期标签
DATE=$(date +%Y%m%d)
docker build -t your-username/vehicle-iot-gateway:${DATE} .
```

## 自动化CI/CD

### GitHub Actions示例

创建 `.github/workflows/build-and-push.yml`：

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: your-username/vehicle-iot-gateway
        tags: |
          type=ref,event=branch
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
    
    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

## 快速参考

### Docker Hub
```bash
docker login
docker build -t username/vehicle-iot-gateway:latest .
docker push username/vehicle-iot-gateway:latest
```

### 阿里云
```bash
docker login registry.cn-hangzhou.aliyuncs.com
docker build -t registry.cn-hangzhou.aliyuncs.com/namespace/vehicle-iot-gateway:latest .
docker push registry.cn-hangzhou.aliyuncs.com/namespace/vehicle-iot-gateway:latest
```

### Harbor
```bash
docker login harbor.example.com
docker build -t harbor.example.com/project/vehicle-iot-gateway:latest .
docker push harbor.example.com/project/vehicle-iot-gateway:latest
```

## 总结

选择合适的镜像仓库：

- **Docker Hub**: 适合公开项目和测试
- **阿里云**: 适合国内项目，速度快
- **Harbor**: 适合企业私有部署
- **本地镜像**: 仅适合单节点测试

推荐流程：
1. 本地构建测试
2. 推送到镜像仓库
3. 更新Kubernetes配置
4. 部署到集群
5. 验证功能

---

**提示**: 记得在推送镜像前测试镜像是否能正常运行！
