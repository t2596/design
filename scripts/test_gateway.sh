#!/bin/bash

# 车联网安全通信网关 - 快速测试脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 默认参数
GATEWAY_HOST="${1:-8.147.61.78}"
GATEWAY_PORT="${2:-30546}"
API_TOKEN="${3:-dev-token-12345}"

echo "=========================================="
echo "车联网安全通信网关 - 快速测试"
echo "=========================================="
echo ""
echo "网关地址: http://${GATEWAY_HOST}:${GATEWAY_PORT}"
echo "API Token: ${API_TOKEN}"
echo ""

# 测试 1: 健康检查
echo "=========================================="
echo "测试 1: 健康检查"
echo "=========================================="
echo ""

if command -v curl &> /dev/null; then
    HEALTH_RESPONSE=$(curl -s "http://${GATEWAY_HOST}:${GATEWAY_PORT}/health")
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        echo -e "${GREEN}✓ 健康检查通过${NC}"
        echo "  响应: $HEALTH_RESPONSE"
    else
        echo -e "${RED}✗ 健康检查失败${NC}"
        echo "  响应: $HEALTH_RESPONSE"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ curl 未安装，跳过健康检查${NC}"
fi

echo ""

# 测试 2: 单次数据传输
echo "=========================================="
echo "测试 2: 单次数据传输"
echo "=========================================="
echo ""

VEHICLE_ID="TEST_$(date +%s)"

python client/vehicle_client.py \
    --gateway-host "${GATEWAY_HOST}" \
    --gateway-port "${GATEWAY_PORT}" \
    --mode once \
    --vehicle-id "${VEHICLE_ID}" \
    --api-token "${API_TOKEN}"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ 单次数据传输测试通过${NC}"
else
    echo ""
    echo -e "${RED}✗ 单次数据传输测试失败${NC}"
    exit 1
fi

echo ""

# 测试 3: 连续数据传输（5 次）
echo "=========================================="
echo "测试 3: 连续数据传输（5 次）"
echo "=========================================="
echo ""

read -p "是否运行连续模式测试？(y/n): " run_continuous

if [ "$run_continuous" = "y" ] || [ "$run_continuous" = "Y" ]; then
    VEHICLE_ID="TEST_CONTINUOUS_$(date +%s)"
    
    python client/vehicle_client.py \
        --gateway-host "${GATEWAY_HOST}" \
        --gateway-port "${GATEWAY_PORT}" \
        --mode continuous \
        --vehicle-id "${VEHICLE_ID}" \
        --api-token "${API_TOKEN}" \
        --interval 3 \
        --iterations 5
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ 连续数据传输测试通过${NC}"
    else
        echo ""
        echo -e "${RED}✗ 连续数据传输测试失败${NC}"
        exit 1
    fi
else
    echo "跳过连续模式测试"
fi

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ 所有测试通过${NC}"
echo ""
echo "查看 API 文档: http://${GATEWAY_HOST}:${GATEWAY_PORT}/docs"
echo ""
