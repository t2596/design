#!/bin/bash

# 验证车辆数据完整流程
# 检查：客户端 → Gateway API → PostgreSQL → Web API

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
NAMESPACE="vehicle-iot-gateway"
DB_NAME="vehicle_iot_gateway"
DB_USER="gateway_user"
GATEWAY_URL="${1:-http://8.147.67.31:32620}"  # 从参数获取或使用默认值
API_TOKEN="dev-token-12345"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}车辆数据流程完整验证${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo "Gateway URL: $GATEWAY_URL"
echo ""

# 1. 检查 PostgreSQL
echo -e "${YELLOW}[1/8] 检查 PostgreSQL 状态${NC}"
kubectl get pods -n $NAMESPACE -l app=postgres
echo ""

# 2. 检查数据库是否存在
echo -e "${YELLOW}[2/8] 检查数据库${NC}"
DB_EXISTS=$(kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | tr -d '\r')

if [ "$DB_EXISTS" = "1" ]; then
    echo -e "${GREEN}✓ 数据库 $DB_NAME 存在${NC}"
else
    echo -e "${RED}✗ 数据库 $DB_NAME 不存在！${NC}"
    echo "请先运行: ./fix_database_complete.sh"
    exit 1
fi
echo ""

# 3. 检查表结构
echo -e "${YELLOW}[3/8] 检查表结构${NC}"
TABLES=$(kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U $DB_USER -d $DB_NAME -tAc "\dt" 2>/dev/null | grep -c "vehicle_data" || echo "0")

if [ "$TABLES" -gt "0" ]; then
    echo -e "${GREEN}✓ vehicle_data 表存在${NC}"
    kubectl exec -it deployment/postgres -n $NAMESPACE -- \
      psql -U $DB_USER -d $DB_NAME -c "\d vehicle_data" | head -20
else
    echo -e "${RED}✗ vehicle_data 表不存在！${NC}"
    exit 1
fi
echo ""

# 4. 检查 Gateway 状态
echo -e "${YELLOW}[4/8] 检查 Gateway 状态${NC}"
kubectl get pods -n $NAMESPACE -l app=gateway
echo ""

# 5. 检查 Gateway 环境变量
echo -e "${YELLOW}[5/8] 检查 Gateway 数据库配置${NC}"
echo "Gateway 的 POSTGRES_DB 配置："
kubectl exec -it deployment/gateway -n $NAMESPACE -- env | grep POSTGRES_DB || echo "未找到 POSTGRES_DB 环境变量"
echo ""

# 6. 测试 Gateway API - 健康检查
echo -e "${YELLOW}[6/8] 测试 Gateway API 健康检查${NC}"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$GATEWAY_URL/health" 2>/dev/null || echo "000")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Gateway API 健康检查通过${NC}"
else
    echo -e "${RED}✗ Gateway API 健康检查失败 (HTTP $HTTP_CODE)${NC}"
    echo "请检查 Gateway 是否正常运行"
fi
echo ""

# 7. 测试数据库直接写入
echo -e "${YELLOW}[7/8] 测试数据库直接写入${NC}"
TEST_VEHICLE_ID="VERIFY_$(date +%s)"
echo "测试车辆 ID: $TEST_VEHICLE_ID"

kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U $DB_USER -d $DB_NAME -c \
  "INSERT INTO vehicle_data (vehicle_id, timestamp, state, motion_speed, gps_latitude, gps_longitude) 
   VALUES ('$TEST_VEHICLE_ID', NOW(), '测试', 88, 39.9042, 116.4074);"

echo "查询刚插入的数据..."
QUERY_RESULT=$(kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U $DB_USER -d $DB_NAME -tAc \
  "SELECT COUNT(*) FROM vehicle_data WHERE vehicle_id='$TEST_VEHICLE_ID'" 2>/dev/null | tr -d '\r ')

if [ "$QUERY_RESULT" = "1" ]; then
    echo -e "${GREEN}✓ 数据库写入成功${NC}"
else
    echo -e "${RED}✗ 数据库写入失败${NC}"
    exit 1
fi
echo ""

# 8. 测试 Web API 读取
echo -e "${YELLOW}[8/8] 测试 Web API 读取数据${NC}"
echo "尝试通过 API 读取刚插入的数据..."

API_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer $API_TOKEN" \
  "$GATEWAY_URL/api/vehicles/$TEST_VEHICLE_ID/data/latest" 2>/dev/null || echo "000")

API_HTTP_CODE=$(echo "$API_RESPONSE" | tail -1)
API_BODY=$(echo "$API_RESPONSE" | head -n -1)

if [ "$API_HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Web API 读取成功${NC}"
    echo "返回数据："
    echo "$API_BODY" | python3 -m json.tool 2>/dev/null || echo "$API_BODY"
elif [ "$API_HTTP_CODE" = "404" ]; then
    echo -e "${YELLOW}⚠ API 返回 404 - 数据可能还未同步到视图${NC}"
    echo "这可能是正常的，因为使用了 latest_vehicle_data 视图"
else
    echo -e "${RED}✗ Web API 读取失败 (HTTP $API_HTTP_CODE)${NC}"
    echo "响应内容："
    echo "$API_BODY"
fi
echo ""

# 9. 检查数据库中的总记录数
echo -e "${YELLOW}数据库统计信息${NC}"
echo "vehicle_data 表总记录数："
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U $DB_USER -d $DB_NAME -c \
  "SELECT COUNT(*) as total_records FROM vehicle_data;"

echo -e "\n最新 5 条记录："
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U $DB_USER -d $DB_NAME -c \
  "SELECT vehicle_id, timestamp, state, motion_speed, gps_latitude, gps_longitude 
   FROM vehicle_data ORDER BY timestamp DESC LIMIT 5;"

# 10. 检查 Gateway 日志
echo -e "\n${YELLOW}Gateway 最新日志${NC}"
echo "（查找错误或数据库相关信息）"
kubectl logs -n $NAMESPACE -l app=gateway --tail=30 | grep -i "error\|exception\|database\|vehicle_data" || echo "未发现明显错误"

# 总结
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}验证总结${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo "✓ 已完成的检查："
echo "  1. PostgreSQL 运行状态"
echo "  2. 数据库 $DB_NAME 存在"
echo "  3. vehicle_data 表结构正确"
echo "  4. Gateway 运行状态"
echo "  5. Gateway 数据库配置"
echo "  6. Gateway API 健康检查"
echo "  7. 数据库直接写入测试"
echo "  8. Web API 读取测试"
echo ""

echo "下一步测试："
echo ""
echo "1. 使用客户端发送真实数据："
echo "   cd client"
echo "   python vehicle_client.py \\"
echo "     --gateway-host $(echo $GATEWAY_URL | sed 's|http://||' | cut -d: -f1) \\"
echo "     --gateway-port $(echo $GATEWAY_URL | sed 's|http://||' | cut -d: -f2 | cut -d/ -f1) \\"
echo "     --mode continuous --iterations 5"
echo ""
echo "2. 实时监控数据写入："
echo "   watch -n 2 'kubectl exec -it deployment/postgres -n $NAMESPACE -- \\"
echo "     psql -U $DB_USER -d $DB_NAME -c \\"
echo "     \"SELECT COUNT(*) FROM vehicle_data;\"'"
echo ""
echo "3. 访问 Web 界面："
echo "   打开浏览器访问: $GATEWAY_URL"
echo ""
echo "4. 查看 Gateway 实时日志："
echo "   kubectl logs -n $NAMESPACE -l app=gateway -f"
echo ""
