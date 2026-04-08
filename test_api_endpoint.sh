#!/bin/bash
# 测试 Gateway API 端点

GATEWAY_URL="http://8.147.67.31:32620"
TOKEN="dev-token-12345"

echo "=========================================="
echo "测试 1: 检查 Gateway Pod 状态"
echo "=========================================="
kubectl get pods -n vehicle-iot-gateway | grep gateway

echo ""
echo "=========================================="
echo "测试 2: 检查 Gateway 日志（最后 20 行）"
echo "=========================================="
kubectl logs -n vehicle-iot-gateway deployment/gateway --tail=20

echo ""
echo "=========================================="
echo "测试 3: 测试 API 端点 - 获取在线车辆"
echo "=========================================="
curl -X GET "${GATEWAY_URL}/api/vehicles/online" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "=========================================="
echo "测试 4: 测试 API 端点 - 获取车辆最新数据"
echo "=========================================="
curl -X GET "${GATEWAY_URL}/api/vehicles/VIN1234/data/latest" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "=========================================="
echo "测试 5: 检查 Web Pod 状态"
echo "=========================================="
kubectl get pods -n vehicle-iot-gateway | grep web

echo ""
echo "=========================================="
echo "测试 6: 检查 Web Nginx 配置"
echo "=========================================="
kubectl exec -n vehicle-iot-gateway deployment/web -- cat /etc/nginx/nginx.conf | grep -A 10 "location /api"

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="
