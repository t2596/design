#!/bin/bash

# 测试安全配置 API 脚本
# 用于验证问题3的修复

GATEWAY_URL="http://8.147.67.31:32620"
TOKEN="dev-token-12345"

echo "=========================================="
echo "测试安全配置 API"
echo "=========================================="
echo ""

# 1. 获取当前安全配置
echo "1. 获取当前安全配置..."
curl -X GET "${GATEWAY_URL}/api/config/security" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo ""
echo "=========================================="
echo ""

# 2. 更新安全配置
echo "2. 更新安全配置..."
curl -X PUT "${GATEWAY_URL}/api/config/security" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 7200,
    "certificate_validity": 180,
    "timestamp_tolerance": 600,
    "concurrent_session_strategy": "terminate_old",
    "max_auth_failures": 3,
    "auth_failure_lockout_duration": 600
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo ""
echo "=========================================="
echo ""

# 3. 再次获取配置，验证是否更新成功
echo "3. 验证配置更新..."
curl -X GET "${GATEWAY_URL}/api/config/security" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo ""
echo "=========================================="
echo ""

# 4. 检查数据库中的配置
echo "4. 检查数据库中的配置..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM security_policy ORDER BY updated_at DESC LIMIT 3;"

echo ""
echo "=========================================="
echo ""

# 5. 恢复默认配置
echo "5. 恢复默认配置..."
curl -X PUT "${GATEWAY_URL}/api/config/security" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 86400,
    "certificate_validity": 365,
    "timestamp_tolerance": 300,
    "concurrent_session_strategy": "reject_new",
    "max_auth_failures": 5,
    "auth_failure_lockout_duration": 300
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo ""
echo "=========================================="
echo ""

# 6. 测试认证失败锁定功能
echo "6. 测试认证失败锁定功能..."
echo "注册一个测试车辆（应该成功）..."
curl -X POST "${GATEWAY_URL}/api/auth/register" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "VIN_LOCK_TEST_001",
    "public_key": "'$(printf '0%.0s' {1..128})'"
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo ""
echo "=========================================="
echo ""

# 7. 检查认证失败记录表
echo "7. 检查认证失败记录表..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM auth_failure_records;"

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "验证要点："
echo "1. 配置能够成功更新并持久化到数据库"
echo "2. 更新后的配置能够正确读取"
echo "3. 数据库中有多条配置记录（历史记录）"
echo "4. 认证失败记录功能正常工作"
