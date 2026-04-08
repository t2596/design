#!/bin/bash

# 深度诊断审计日志API问题

echo "========================================="
echo "深度诊断审计日志API"
echo "========================================="
echo ""

# 1. 检查数据库中所有event_type
echo "1. 检查数据库中所有event_type值"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT DISTINCT event_type FROM audit_logs ORDER BY event_type;"
echo ""

# 2. 查看最近的5条日志详情
echo "2. 查看最近的5条审计日志详情"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT id, log_id, event_type, vehicle_id, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 5;"
echo ""

# 3. 在Gateway Pod中直接测试audit_logger
echo "3. 在Gateway Pod中测试audit_logger.query_audit_logs"
echo "----------------------------------------"
POD_NAME=$(kubectl get pods -n vehicle-iot-gateway -l app=gateway -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n vehicle-iot-gateway $POD_NAME -- python3 -c "
import sys
sys.path.insert(0, '/app')

from src.db.postgres import PostgreSQLConnection
from config.database import PostgreSQLConfig
from src.audit_logger import AuditLogger

try:
    db = PostgreSQLConnection(PostgreSQLConfig.from_env())
    audit_logger = AuditLogger(db)
    
    # 查询所有审计日志
    logs = audit_logger.query_audit_logs()
    
    print(f'查询成功，返回 {len(logs)} 条日志')
    
    if len(logs) > 0:
        print('\\n前3条日志:')
        for i, log in enumerate(logs[:3]):
            print(f'  {i+1}. [{log.timestamp}] {log.event_type.value} - {log.vehicle_id}')
    else:
        print('\\n警告：query_audit_logs返回空列表')
        print('\\n直接查询数据库:')
        result = db.execute_query('SELECT COUNT(*) as count FROM audit_logs', ())
        print(f'数据库中有 {result[0][\"count\"]} 条记录')
    
    db.close()
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
"
echo ""

# 4. 测试API并查看详细错误
echo "4. 测试API并查看Gateway实时日志"
echo "----------------------------------------"
echo "发送API请求..."

# 在后台查看日志
kubectl logs -f deployment/gateway -n vehicle-iot-gateway --tail=0 2>/dev/null &
LOG_PID=$!

sleep 1

# 发送请求
GATEWAY_URL="http://8.160.179.59:32677"
TOKEN="dev-token-12345"

curl -s -X GET "${GATEWAY_URL}/api/audit/logs?limit=10" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" > /tmp/api_response.txt

sleep 2

# 停止日志查看
kill $LOG_PID 2>/dev/null

echo ""
echo "API响应:"
cat /tmp/api_response.txt
echo ""
echo ""

# 5. 检查是否有其他无效的event_type
echo "5. 检查是否有无效的event_type值"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "
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
  "
echo ""

# 6. 查看audit_logger.py中的代码
echo "6. 检查Pod中audit_logger.py的query_audit_logs方法"
echo "----------------------------------------"
kubectl exec -n vehicle-iot-gateway $POD_NAME -- \
  grep -A 30 "def query_audit_logs" /app/src/audit_logger.py | head -35
echo ""

echo "========================================="
echo "诊断完成"
echo "========================================="
echo ""
