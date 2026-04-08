#!/bin/bash

# 检查并修复所有无效的event_type

echo "========================================="
echo "检查并修复所有无效的event_type"
echo "========================================="
echo ""

# 1. 查找所有无效的event_type
echo "1. 查找所有无效的event_type"
echo "----------------------------------------"

INVALID_EVENTS=$(kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -t -c "
    SELECT event_type, COUNT(*) as count 
    FROM audit_logs 
    WHERE event_type NOT IN (
      'VEHICLE_CONNECT',
      'VEHICLE_DISCONNECT',
      'AUTHENTICATION_SUCCESS',
      'AUTHENTICATION_FAILURE',
      'DATA_ENCRYPTED',
      'DATA_DECRYPTED',
      'CERTIFICATE_ISSUED',
      'CERTIFICATE_REVOKED',
      'SIGNATURE_VERIFIED',
      'SIGNATURE_FAILED'
    )
    GROUP BY event_type;
  " 2>/dev/null)

if [ -z "$INVALID_EVENTS" ] || [ "$INVALID_EVENTS" = "" ]; then
    echo "✓ 没有发现无效的event_type"
else
    echo "⚠ 发现无效的event_type:"
    echo "$INVALID_EVENTS"
    echo ""
    
    # 2. 删除所有无效的event_type
    echo "2. 删除所有无效的event_type"
    echo "----------------------------------------"
    
    kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
      psql -U postgres -d vehicle_iot_gateway -c "
        DELETE FROM audit_logs 
        WHERE event_type NOT IN (
          'VEHICLE_CONNECT',
          'VEHICLE_DISCONNECT',
          'AUTHENTICATION_SUCCESS',
          'AUTHENTICATION_FAILURE',
          'DATA_ENCRYPTED',
          'DATA_DECRYPTED',
          'CERTIFICATE_ISSUED',
          'CERTIFICATE_REVOKED',
          'SIGNATURE_VERIFIED',
          'SIGNATURE_FAILED'
        );
      "
    
    echo ""
    echo "✓ 无效的event_type已删除"
fi

echo ""

# 3. 查看剩余的日志
echo "3. 查看剩余的审计日志"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) as total, 
          COUNT(DISTINCT event_type) as distinct_types 
   FROM audit_logs;"

echo ""

kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT event_type, COUNT(*) as count 
   FROM audit_logs 
   GROUP BY event_type 
   ORDER BY event_type;"

echo ""

# 4. 测试API
echo "4. 测试API"
echo "----------------------------------------"
GATEWAY_URL="http://8.160.179.59:32677"
TOKEN="dev-token-12345"

RESPONSE=$(curl -s -X GET "${GATEWAY_URL}/api/audit/logs?limit=10" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json")

echo "API响应:"
echo "$RESPONSE"
echo ""

TOTAL=$(echo "$RESPONSE" | grep -o '"total":[0-9]*' | grep -o '[0-9]*')

if [ -z "$TOTAL" ]; then
    TOTAL=0
fi

if [ "$TOTAL" -gt "0" ]; then
    echo "✓ 问题已解决！API返回了 ${TOTAL} 条审计日志"
else
    echo "⚠ API仍然返回空数据"
    echo ""
    echo "可能的原因："
    echo "1. Gateway Pod中的代码仍有bug"
    echo "2. 需要重启Gateway Pod"
    echo ""
    echo "建议操作："
    echo "  kubectl rollout restart deployment/gateway -n vehicle-iot-gateway"
fi

echo ""
echo "========================================="
echo "完成"
echo "========================================="
