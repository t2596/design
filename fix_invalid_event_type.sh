#!/bin/bash

# 修复无效的event_type问题

echo "========================================="
echo "修复审计日志无效event_type问题"
echo "========================================="
echo ""

# 方案1：删除无效的测试日志（快速）
echo "方案1：删除无效的测试日志"
echo "----------------------------------------"
echo "删除event_type为TEST_EVENT的日志..."

kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "DELETE FROM audit_logs WHERE event_type = 'TEST_EVENT';"

echo ""
echo "✓ 无效日志已删除"
echo ""

# 验证
echo "验证：查询剩余的审计日志"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) as total FROM audit_logs;"

echo ""

# 测试API
echo "测试API"
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

if [ "$TOTAL" -gt "0" ]; then
    echo "✓ 问题已解决！API返回了 ${TOTAL} 条审计日志"
    echo ""
    echo "现在可以在Web界面查看审计日志："
    echo "  访问: http://8.160.179.59:32678"
    echo "  进入审计日志页面"
else
    echo "⚠ API仍然返回空数据"
    echo ""
    echo "请检查Gateway日志："
    echo "  kubectl logs deployment/gateway -n vehicle-iot-gateway --tail=20"
fi

echo ""
echo "========================================="
echo "修复完成"
echo "========================================="
echo ""

echo "说明："
echo "- 问题原因：数据库中有无效的event_type值（TEST_EVENT）"
echo "- 解决方案：删除无效的测试日志"
echo "- 长期方案：更新代码以容忍无效的枚举值（已在本地修复）"
echo ""
