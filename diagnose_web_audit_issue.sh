#!/bin/bash

# 诊断Web端审计日志查询失效问题

echo "========================================="
echo "诊断Web端审计日志查询问题"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
GATEWAY_URL="http://8.147.67.31:32620"
WEB_URL="http://8.147.67.31:32621"
TOKEN="dev-token-12345"

echo "配置信息:"
echo "  Gateway URL: ${GATEWAY_URL}"
echo "  Web URL: ${WEB_URL}"
echo ""

# 步骤1：检查Gateway Pod状态
echo -e "${YELLOW}步骤1：检查Gateway Pod状态${NC}"
echo "----------------------------------------"
kubectl get pods -n vehicle-iot-gateway -l app=gateway
echo ""

# 步骤2：检查Web Pod状态
echo -e "${YELLOW}步骤2：检查Web Pod状态${NC}"
echo "----------------------------------------"
kubectl get pods -n vehicle-iot-gateway -l app=web
echo ""

# 步骤3：检查数据库中的审计日志
echo -e "${YELLOW}步骤3：检查数据库中的审计日志${NC}"
echo "----------------------------------------"
echo "审计日志总数:"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -t -c \
  "SELECT COUNT(*) FROM audit_logs;" 2>/dev/null | tr -d ' '

echo ""
echo "最近5条审计日志:"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT event_type, vehicle_id, operation_result, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 5;" 2>/dev/null
echo ""

# 步骤4：直接测试Gateway API
echo -e "${YELLOW}步骤4：直接测试Gateway API${NC}"
echo "----------------------------------------"
echo "请求: GET ${GATEWAY_URL}/api/audit/logs"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${GATEWAY_URL}/api/audit/logs" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "HTTP状态码: ${HTTP_CODE}"
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Gateway API响应正常${NC}"
    echo "响应内容:"
    echo "$BODY" | jq '.'
else
    echo -e "${RED}✗ Gateway API响应异常${NC}"
    echo "响应内容:"
    echo "$BODY"
fi
echo ""

# 步骤5：通过Web服务测试API代理
echo -e "${YELLOW}步骤5：通过Web服务测试API代理${NC}"
echo "----------------------------------------"
echo "请求: GET ${WEB_URL}/api/audit/logs"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${WEB_URL}/api/audit/logs" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "HTTP状态码: ${HTTP_CODE}"
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Web代理API响应正常${NC}"
    echo "响应内容:"
    echo "$BODY" | jq '.'
else
    echo -e "${RED}✗ Web代理API响应异常${NC}"
    echo "响应内容:"
    echo "$BODY"
fi
echo ""

# 步骤6：检查Gateway日志
echo -e "${YELLOW}步骤6：检查Gateway日志（最近20行）${NC}"
echo "----------------------------------------"
kubectl logs deployment/gateway -n vehicle-iot-gateway --tail=20 2>/dev/null
echo ""

# 步骤7：检查Web日志
echo -e "${YELLOW}步骤7：检查Web日志（最近20行）${NC}"
echo "----------------------------------------"
kubectl logs deployment/web -n vehicle-iot-gateway --tail=20 2>/dev/null
echo ""

# 步骤8：生成测试数据
echo -e "${YELLOW}步骤8：生成测试审计日志数据${NC}"
echo "----------------------------------------"
echo "注册测试车辆（会生成审计日志）..."
curl -s -X POST "${GATEWAY_URL}/api/auth/register" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "DIAG-TEST-'$(date +%s)'",
    "certificate_serial": "DIAG-CERT-'$(date +%s)'"
  }' | jq '.'
echo ""

# 步骤9：再次查询审计日志
echo -e "${YELLOW}步骤9：再次查询审计日志${NC}"
echo "----------------------------------------"
echo "通过Gateway直接查询:"
curl -s -X GET "${GATEWAY_URL}/api/audit/logs?limit=3" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.logs[] | {event_type, vehicle_id, timestamp}'
echo ""

echo "通过Web代理查询:"
curl -s -X GET "${WEB_URL}/api/audit/logs?limit=3" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.logs[] | {event_type, vehicle_id, timestamp}'
echo ""

# 步骤10：检查浏览器控制台
echo -e "${YELLOW}步骤10：浏览器测试建议${NC}"
echo "----------------------------------------"
echo "请在浏览器中执行以下操作："
echo "1. 打开 ${WEB_URL}"
echo "2. 打开浏览器开发者工具（F12）"
echo "3. 切换到 Network 标签"
echo "4. 访问审计日志页面"
echo "5. 查看是否有 /api/audit/logs 请求"
echo "6. 检查请求的响应状态和内容"
echo ""
echo "如果看到错误，请检查："
echo "  - 请求URL是否正确"
echo "  - Authorization header是否存在"
echo "  - 响应状态码和错误信息"
echo ""

echo "========================================="
echo "诊断完成"
echo "========================================="
echo ""

# 总结
echo -e "${YELLOW}问题总结：${NC}"
echo ""
echo "如果Gateway API正常但Web代理失败："
echo "  → 检查Nginx配置和Web Pod日志"
echo ""
echo "如果两者都失败："
echo "  → 检查Gateway Pod日志和数据库连接"
echo ""
echo "如果数据库中没有审计日志："
echo "  → 审计日志功能可能没有被调用"
echo "  → 需要检查代码中的audit_logger调用"
echo ""
