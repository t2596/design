#!/bin/bash

# 快速构建脚本 - 用于本地测试

echo "=========================================="
echo "快速构建Docker镜像"
echo "=========================================="
echo ""

# 配置
IMAGE_NAME="vehicle-iot-gateway"
TAG="latest"

# 构建镜像
echo "正在构建镜像: ${IMAGE_NAME}:${TAG}"
docker build -t ${IMAGE_NAME}:${TAG} .

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ 构建成功！"
    echo ""
    echo "镜像信息:"
    docker images ${IMAGE_NAME}:${TAG}
    echo ""
    echo "测试运行:"
    echo "  docker run --rm -p 8000:8000 ${IMAGE_NAME}:${TAG}"
    echo ""
    echo "推送到Docker Hub:"
    echo "  docker tag ${IMAGE_NAME}:${TAG} your-username/${IMAGE_NAME}:${TAG}"
    echo "  docker push your-username/${IMAGE_NAME}:${TAG}"
else
    echo ""
    echo "✗ 构建失败"
    exit 1
fi
