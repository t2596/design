#!/bin/bash
# 重新构建 Gateway 镜像并部署

set -e

echo "=========================================="
echo "步骤 1: 构建新的 Gateway 镜像"
echo "=========================================="
docker build -t vehicle-iot-gateway:latest .

echo ""
echo "=========================================="
echo "步骤 2: 标记镜像（如果需要推送到镜像仓库）"
echo "=========================================="
# 如果你使用私有镜像仓库，取消下面的注释并修改仓库地址
# REGISTRY="your-registry.com"
# docker tag vehicle-iot-gateway:latest ${REGISTRY}/vehicle-iot-gateway:latest
# docker push ${REGISTRY}/vehicle-iot-gateway:latest

echo ""
echo "=========================================="
echo "步骤 3: 重启 Gateway Deployment"
echo "=========================================="
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

echo ""
echo "=========================================="
echo "步骤 4: 等待 Gateway 重启完成"
echo "=========================================="
kubectl rollout status deployment/gateway -n vehicle-iot-gateway

echo ""
echo "=========================================="
echo "步骤 5: 检查 Gateway Pods 状态"
echo "=========================================="
kubectl get pods -n vehicle-iot-gateway | grep gateway

echo ""
echo "=========================================="
echo "步骤 6: 测试 API 端点"
echo "=========================================="
sleep 5  # 等待几秒让服务完全启动

# 获取 Gateway Service 的 NodePort
GATEWAY_PORT=$(kubectl get svc gateway-service -n vehicle-iot-gateway -o jsonpath='{.spec.ports[0].nodePort}')
GATEWAY_URL="http://localhost:${GATEWAY_PORT}"

echo "测试获取车辆最新数据..."
curl -X GET "${GATEWAY_URL}/api/vehicles/VIN1234/data/latest" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "=========================================="
echo "完成！"
echo "现在刷新 Web 页面应该能看到车辆数据了"
echo "=========================================="
