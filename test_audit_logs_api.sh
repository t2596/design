#!/bin/bash

# 测试审计日志 API 脚本
# 用于验证问题2的修复

GATEWAY_URL="http://8.147.67.31:32620"
TOKEN="dev-token-12345"

echo "=========================================="
echo "测试审计日志 API"
echo "=========================================="
echo ""

# 1. 测试获取审计日志列表
echo "1. 获取审计日志列表..."
curl -X GET "${GATEWAY_URL}/api/audit/logs?limit=10" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo ""
echo "=========================================="
echo ""

# 2. 测试按车辆ID过滤
echo "2. 按车辆ID过滤审计日志..."
curl -X GET "${GATEWAY_URL}/api/audit/logs?vehicle_id=VIN_TEST_001&limit=5" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo ""
echo "=========================================="
echo ""

# 3. 测试按事件类型过滤
echo "3. 按事件类型过滤审计日志（认证成功）..."
curl -X GET "${GATEWAY_URL}/api/audit/logs?event_type=AUTHENTICATION_SUCCESS&limit=5" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo ""
echo "=========================================="
echo ""

# 4. 测试按操作结果过滤
echo "4. 按操作结果过滤审计日志（成功）..."
curl -X GET "${GATEWAY_URL}/api/audit/logs?operation_result=true&limit=5" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo ""
echo "=========================================="
echo ""

# 5. 测试导出审计报告（JSON格式）
echo "5. 导出审计报告（JSON格式）..."
START_TIME=$(date -u -d '1 day ago' +"%Y-%m-%dT%H:%M:%S")
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S")

curl -X GET "${GATEWAY_URL}/api/audit/export?start_time=${START_TIME}&end_time=${END_TIME}&format=json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.' | head -50

echo ""
echo "=========================================="
echo ""

# 6. 检查数据库中的审计日志数量
echo "6. 检查数据库中的审计日志数量..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) as total_logs FROM audit_logs;"

echo ""
echo "=========================================="
echo ""

# 7. 查看最近的10条审计日志
echo "7. 查看数据库中最近的10条审计日志..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT event_type, vehicle_id, operation_result, timestamp, details FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
