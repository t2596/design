#!/bin/bash
# 测试审计日志和安全配置 API

GATEWAY_URL="http://8.147.67.31:32620"
TOKEN="dev-token-12345"

echo "=========================================="
echo "测试 1: 检查数据库中的审计日志"
echo "=========================================="
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) as total_logs FROM audit_logs;"

echo ""
echo "=========================================="
echo "测试 2: 查看最近的审计日志"
echo "=========================================="
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT event_type, vehicle_id, operation_result, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 5;"

echo ""
echo "=========================================="
echo "测试 3: 测试审计日志 API"
echo "=========================================="
curl -s -X GET "${GATEWAY_URL}/api/audit/logs?limit=5" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.'

echo ""
echo "=========================================="
echo "测试 4: 测试获取安全配置 API"
echo "=========================================="
curl -s -X GET "${GATEWAY_URL}/api/config/security" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.'

echo ""
echo "=========================================="
echo "测试 5: 测试更新安全配置 API"
echo "=========================================="
curl -s -X PUT "${GATEWAY_URL}/api/config/security" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 7200,
    "certificate_validity": 365,
    "timestamp_tolerance": 300,
    "concurrent_session_strategy": "reject_new",
    "max_auth_failures": 5,
    "auth_failure_lockout_duration": 300
  }' | jq '.'

echo ""
echo "=========================================="
echo "测试 6: 验证配置是否更新"
echo "=========================================="
curl -s -X GET "${GATEWAY_URL}/api/config/security" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.policy.session_timeout'

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="
