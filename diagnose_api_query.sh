#!/bin/bash

# 诊断审计日志API查询问题

echo "========================================="
echo "诊断审计日志API查询问题"
echo "========================================="
echo ""

GATEWAY_URL="http://8.160.179.59:32677"
TOKEN="dev-token-12345"

# 1. 直接查询数据库
echo "1. 数据库中的审计日志（最近5条）"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT id, event_type, vehicle_id, timestamp, operation_result FROM audit_logs ORDER BY timestamp DESC LIMIT 5;"
echo ""

# 2. 查询API（不带任何过滤条件）
echo "2. API查询（不带过滤条件）"
echo "----------------------------------------"
echo "请求: GET ${GATEWAY_URL}/api/audit/logs?limit=100"
RESPONSE=$(curl -s -X GET "${GATEWAY_URL}/api/audit/logs?limit=100" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json")
echo "响应:"
echo "$RESPONSE"
echo ""

# 3. 检查响应中的total字段
TOTAL=$(echo "$RESPONSE" | grep -o '"total":[0-9]*' | grep -o '[0-9]*')
echo "返回的日志数量: ${TOTAL}"
echo ""

if [ "$TOTAL" = "0" ] || [ -z "$TOTAL" ]; then
    echo "⚠ API返回空数据，但数据库中有数据"
    echo ""
    
    # 4. 检查Gateway日志
    echo "3. 检查Gateway日志（查看是否有错误）"
    echo "----------------------------------------"
    kubectl logs deployment/gateway -n vehicle-iot-gateway --tail=30 | grep -i -E "audit|error|exception"
    echo ""
    
    # 5. 直接在Gateway Pod中测试数据库连接
    echo "4. 在Gateway Pod中测试数据库查询"
    echo "----------------------------------------"
    POD_NAME=$(kubectl get pods -n vehicle-iot-gateway -l app=gateway -o jsonpath='{.items[0].metadata.name}')
    
    kubectl exec -n vehicle-iot-gateway $POD_NAME -- python3 -c "
from src.db.postgres import PostgreSQLConnection
from config.database import PostgreSQLConfig

try:
    db = PostgreSQLConnection(PostgreSQLConfig.from_env())
    result = db.execute_query('SELECT COUNT(*) as count FROM audit_logs', ())
    print(f'数据库查询成功，审计日志数量: {result[0][\"count\"]}')
    db.close()
except Exception as e:
    print(f'数据库查询失败: {e}')
"
    echo ""
    
    # 6. 检查audit.py中的查询逻辑
    echo "5. 检查audit.py中的查询逻辑"
    echo "----------------------------------------"
    kubectl exec -n vehicle-iot-gateway $POD_NAME -- \
      grep -A 10 "def query_audit_logs" /app/src/api/routes/audit.py | head -20
    echo ""
    
else
    echo "✓ API返回了数据"
    echo ""
    echo "审计日志列表:"
    echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for log in data.get('logs', [])[:5]:
        print(f\"  - [{log['timestamp']}] {log['event_type']} - {log['vehicle_id']} - {'成功' if log['operation_result'] else '失败'}\")
except:
    print('  无法解析JSON')
"
fi

echo ""
echo "========================================="
echo "诊断完成"
echo "========================================="
echo ""

if [ "$TOTAL" = "0" ] || [ -z "$TOTAL" ]; then
    echo "问题：数据库有数据，但API返回空"
    echo ""
    echo "可能原因："
    echo "1. 查询逻辑有bug"
    echo "2. 时间过滤问题"
    echo "3. 数据库连接问题"
    echo ""
    echo "建议："
    echo "1. 查看Gateway日志中的错误信息"
    echo "2. 检查audit_logger.py中的query_audit_logs方法"
    echo "3. 尝试重启Gateway Pod"
else
    echo "✓ 问题已解决！API正常返回数据"
    echo ""
    echo "现在可以在Web界面查看审计日志："
    echo "  访问: http://8.160.179.59:32678"
    echo "  进入审计日志页面"
fi
echo ""
