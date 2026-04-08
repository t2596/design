#!/bin/bash

# 简单测试审计日志API（不需要jq）

GATEWAY_URL="http://8.160.179.59:32677"
TOKEN="dev-token-12345"

echo "========================================="
echo "测试审计日志API"
echo "========================================="
echo ""

# 测试1：查询审计日志（原始输出）
echo "测试1：查询审计日志"
echo "----------------------------------------"
echo "请求: GET ${GATEWAY_URL}/api/audit/logs"
echo ""

RESPONSE=$(curl -s -X GET "${GATEWAY_URL}/api/audit/logs" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json")

echo "响应内容:"
echo "$RESPONSE"
echo ""

# 检查响应是否包含 "logs"
if echo "$RESPONSE" | grep -q '"logs"'; then
    echo "✓ API响应正常，包含logs字段"
    
    # 检查是否有数据
    if echo "$RESPONSE" | grep -q '"total":0'; then
        echo "⚠ 警告：数据库中没有审计日志数据"
        echo ""
        echo "需要生成测试数据..."
        NEED_DATA=true
    else
        echo "✓ 数据库中有审计日志数据"
        NEED_DATA=false
    fi
else
    echo "✗ API响应异常"
    NEED_DATA=true
fi

echo ""
echo ""

# 如果需要，生成测试数据
if [ "$NEED_DATA" = "true" ]; then
    echo "测试2：生成测试数据"
    echo "----------------------------------------"
    
    for i in {1..3}; do
        VEHICLE_ID="TEST-VEHICLE-$(date +%s)-${i}"
        echo "注册车辆: ${VEHICLE_ID}"
        
        curl -s -X POST "${GATEWAY_URL}/api/auth/register" \
          -H "Authorization: Bearer ${TOKEN}" \
          -H "Content-Type: application/json" \
          -d "{
            \"vehicle_id\": \"${VEHICLE_ID}\",
            \"certificate_serial\": \"TEST-CERT-$(date +%s)-${i}\"
          }"
        
        echo ""
        sleep 1
    done
    
    echo ""
    echo "测试数据生成完成"
    echo ""
    echo ""
    
    # 再次查询
    echo "测试3：再次查询审计日志"
    echo "----------------------------------------"
    
    RESPONSE=$(curl -s -X GET "${GATEWAY_URL}/api/audit/logs?limit=5" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json")
    
    echo "响应内容:"
    echo "$RESPONSE"
    echo ""
fi

echo ""
echo "========================================="
echo "测试完成"
echo "========================================="
echo ""

echo "如果看到 {\"total\":X,\"logs\":[...]} 格式的响应，说明API正常工作"
echo ""
echo "下一步："
echo "1. 在浏览器中访问: ${GATEWAY_URL%:*}:32678"
echo "2. 进入审计日志页面"
echo "3. 应该能看到日志列表"
echo ""
