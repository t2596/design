#!/bin/bash

# 直接测试审计日志API
# 用于诊断Web端审计日志查询失效问题

GATEWAY_URL="http://8.147.67.31:32620"
TOKEN="dev-token-12345"

echo "========================================="
echo "测试审计日志API"
echo "========================================="
echo ""

# 测试1：查询所有审计日志
echo "测试1：查询所有审计日志"
echo "----------------------------------------"
curl -X GET "${GATEWAY_URL}/api/audit/logs" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  2>/dev/null | jq '.'

echo ""
echo ""

# 测试2：查询最近的审计日志（限制10条）
echo "测试2：查询最近10条审计日志"
echo "----------------------------------------"
curl -X GET "${GATEWAY_URL}/api/audit/logs?limit=10" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  2>/dev/null | jq '.'

echo ""
echo ""

# 测试3：检查数据库中的审计日志数量
echo "测试3：检查数据库中的审计日志数量"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) as total_logs FROM audit_logs;" 2>/dev/null

echo ""
echo ""

# 测试4：查看最近的5条审计日志
echo "测试4：查看数据库中最近的5条审计日志"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT event_type, vehicle_id, operation_result, timestamp, details FROM audit_logs ORDER BY timestamp DESC LIMIT 5;" 2>/dev/null

echo ""
echo ""

# 测试5：测试车辆注册（会生成审计日志）
echo "测试5：测试车辆注册（会生成审计日志）"
echo "----------------------------------------"
curl -X POST "${GATEWAY_URL}/api/auth/register" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "TEST-VEHICLE-001",
    "certificate_serial": "TEST-CERT-001"
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  2>/dev/null | jq '.'

echo ""
echo ""

# 测试6：再次查询审计日志，看是否有新记录
echo "测试6：再次查询审计日志（应该有新记录）"
echo "----------------------------------------"
curl -X GET "${GATEWAY_URL}/api/audit/logs?limit=5" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  2>/dev/null | jq '.'

echo ""
echo ""
echo "========================================="
echo "测试完成"
echo "========================================="
