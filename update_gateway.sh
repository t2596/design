#!/bin/bash
# 更新 Gateway 代码并重新部署

set -e

echo "=========================================="
echo "步骤 1: 在所有节点上构建 Gateway 镜像"
echo "=========================================="
echo "请在每个 K8s 节点上运行以下命令："
echo "  cd /path/to/project"
echo "  docker build -t vehicle-iot-gateway:latest ."
echo ""
read -p "是否已在所有节点上构建完成？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "请先在所有节点上构建镜像，然后重新运行此脚本"
    exit 1
fi

echo ""
echo "=========================================="
echo "步骤 2: 删除现有 Gateway Pods"
echo "=========================================="
kubectl delete pods -n vehicle-iot-gateway -l app=gateway

echo ""
echo "=========================================="
echo "步骤 3: 等待新 Pods 启动"
echo "=========================================="
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s

echo ""
echo "=========================================="
echo "步骤 4: 检查 Gateway Pods 状态"
echo "=========================================="
kubectl get pods -n vehicle-iot-gateway | grep gateway

echo ""
echo "=========================================="
echo "步骤 5: 检查 Gateway 日志"
echo "=========================================="
kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=10

echo ""
echo "=========================================="
echo "完成！现在测试 API 端点..."
echo "=========================================="
sleep 5

# 测试 API
GATEWAY_PORT=$(kubectl get svc gateway-service -n vehicle-iot-gateway -o jsonpath='{.spec.ports[0].nodePort}')
GATEWAY_URL="http://localhost:${GATEWAY_PORT}"

echo "测试获取车辆最新数据..."
curl -s -X GET "${GATEWAY_URL}/api/vehicles/VIN1234/data/latest" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" | jq '.' || echo "API 调用失败"

echo ""
echo "=========================================="
echo "全部完成！刷新 Web 页面查看效果"
echo "=========================================="
