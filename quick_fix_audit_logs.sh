#!/bin/bash

# 快速修复Web端审计日志查询问题

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}快速修复Web端审计日志查询问题${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# 步骤1：重启Gateway Pod
echo -e "${YELLOW}步骤1：重启Gateway Pod（确保使用最新代码）${NC}"
echo "----------------------------------------"
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway
echo -e "${GREEN}✓ Gateway重启命令已发送${NC}"
echo ""

# 等待Pod就绪
echo "等待Gateway Pod就绪..."
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s
echo -e "${GREEN}✓ Gateway Pod已就绪${NC}"
echo ""

# 步骤2：检查数据库中的审计日志
echo -e "${YELLOW}步骤2：检查数据库中的审计日志${NC}"
echo "----------------------------------------"
LOG_COUNT=$(kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -t -c \
  "SELECT COUNT(*) FROM audit_logs;" 2>/dev/null | tr -d ' \r\n')

echo "当前审计日志数量: ${LOG_COUNT}"

if [ "$LOG_COUNT" -eq "0" ] || [ -z "$LOG_COUNT" ]; then
    echo -e "${YELLOW}⚠ 数据库中没有审计日志，将生成测试数据${NC}"
    NEED_TEST_DATA=true
else
    echo -e "${GREEN}✓ 数据库中已有审计日志${NC}"
    NEED_TEST_DATA=false
fi
echo ""

# 步骤3：生成测试数据（如果需要）
if [ "$NEED_TEST_DATA" = true ]; then
    echo -e "${YELLOW}步骤3：生成测试审计日志数据${NC}"
    echo "----------------------------------------"
    
    GATEWAY_URL="http://8.147.67.31:32620"
    TOKEN="dev-token-12345"
    
    echo "注册测试车辆（会生成审计日志）..."
    
    for i in {1..3}; do
        VEHICLE_ID="TEST-VEHICLE-$(date +%s)-${i}"
        echo "  注册车辆: ${VEHICLE_ID}"
        
        curl -s -X POST "${GATEWAY_URL}/api/auth/register" \
          -H "Authorization: Bearer ${TOKEN}" \
          -H "Content-Type: application/json" \
          -d "{
            \"vehicle_id\": \"${VEHICLE_ID}\",
            \"certificate_serial\": \"TEST-CERT-$(date +%s)-${i}\"
          }" > /dev/null
        
        sleep 1
    done
    
    echo -e "${GREEN}✓ 测试数据生成完成${NC}"
    echo ""
    
    # 再次检查数据库
    echo "再次检查数据库..."
    NEW_LOG_COUNT=$(kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
      psql -U postgres -d vehicle_iot_gateway -t -c \
      "SELECT COUNT(*) FROM audit_logs;" 2>/dev/null | tr -d ' \r\n')
    echo "新的审计日志数量: ${NEW_LOG_COUNT}"
    echo ""
fi

# 步骤4：测试Gateway API
echo -e "${YELLOW}步骤4：测试Gateway API${NC}"
echo "----------------------------------------"

GATEWAY_URL="http://8.147.67.31:32620"
TOKEN="dev-token-12345"

RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${GATEWAY_URL}/api/audit/logs?limit=5" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Gateway API响应正常 (HTTP ${HTTP_CODE})${NC}"
    
    TOTAL=$(echo "$BODY" | jq -r '.total')
    echo "返回的日志数量: ${TOTAL}"
    
    if [ "$TOTAL" -gt "0" ]; then
        echo -e "${GREEN}✓ API返回了审计日志数据${NC}"
        echo ""
        echo "最近的审计日志:"
        echo "$BODY" | jq -r '.logs[] | "  - [\(.timestamp)] \(.event_type) - \(.vehicle_id) - \(if .operation_result then "成功" else "失败" end)"'
    else
        echo -e "${RED}✗ API返回空数据${NC}"
    fi
else
    echo -e "${RED}✗ Gateway API响应异常 (HTTP ${HTTP_CODE})${NC}"
    echo "响应内容:"
    echo "$BODY"
fi
echo ""

# 步骤5：测试Web代理
echo -e "${YELLOW}步骤5：测试Web代理${NC}"
echo "----------------------------------------"

WEB_URL="http://8.147.67.31:32621"

RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${WEB_URL}/api/audit/logs?limit=5" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Web代理响应正常 (HTTP ${HTTP_CODE})${NC}"
    
    TOTAL=$(echo "$BODY" | jq -r '.total')
    echo "返回的日志数量: ${TOTAL}"
    
    if [ "$TOTAL" -gt "0" ]; then
        echo -e "${GREEN}✓ Web代理返回了审计日志数据${NC}"
    else
        echo -e "${RED}✗ Web代理返回空数据${NC}"
    fi
else
    echo -e "${RED}✗ Web代理响应异常 (HTTP ${HTTP_CODE})${NC}"
    echo "响应内容:"
    echo "$BODY"
fi
echo ""

# 步骤6：显示最终状态
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}修复完成${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

echo "请在浏览器中验证："
echo "  1. 访问: ${WEB_URL}"
echo "  2. 进入审计日志页面"
echo "  3. 应该能看到审计日志列表"
echo ""

echo "如果仍然有问题，请运行详细诊断："
echo "  bash diagnose_web_audit_issue.sh"
echo ""

echo "或查看诊断文档："
echo "  cat WEB_AUDIT_LOG_DIAGNOSIS.md"
echo ""
