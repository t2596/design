#!/bin/bash

# 运行多个车辆客户端连接到云端Gateway
# 
# 使用方法：
#   bash run-multiple-clients.sh 5                    # 启动5个客户端
#   bash run-multiple-clients.sh 10 --interval 5      # 启动10个客户端，每5秒发送一次
#   bash run-multiple-clients.sh 3 --mode once        # 启动3个客户端，只发送一次

set -e

# 默认配置
GATEWAY_HOST="${GATEWAY_HOST:-8.160.179.59}"
GATEWAY_PORT="${GATEWAY_PORT:-32677}"
NUM_CLIENTS="${1:-3}"
MODE="continuous"
INTERVAL="10"
VEHICLE_ID_PREFIX="CLOUD-VIN"

# 解析命令行参数
shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --gateway)
            GATEWAY_HOST="$2"
            shift 2
            ;;
        --port)
            GATEWAY_PORT="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --prefix)
            VEHICLE_ID_PREFIX="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}启动多个车辆客户端${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "配置信息:"
echo "  Gateway地址: ${GATEWAY_HOST}:${GATEWAY_PORT}"
echo "  客户端数量: ${NUM_CLIENTS}"
echo "  运行模式: ${MODE}"
echo "  发送间隔: ${INTERVAL}秒"
echo "  车辆ID前缀: ${VEHICLE_ID_PREFIX}"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误：未安装Docker${NC}"
    exit 1
fi

# 构建客户端镜像
echo -e "${YELLOW}构建客户端镜像...${NC}"
cd "$(dirname "$0")/.."
docker build -f client/Dockerfile -t vehicle-client:latest .
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

# 启动客户端容器
echo -e "${YELLOW}启动 ${NUM_CLIENTS} 个客户端...${NC}"
echo ""

for i in $(seq 1 $NUM_CLIENTS); do
    VEHICLE_ID="${VEHICLE_ID_PREFIX}-$(printf "%03d" $i)"
    CONTAINER_NAME="vehicle-client-${i}"
    
    # 停止并删除已存在的容器
    docker rm -f ${CONTAINER_NAME} 2>/dev/null || true
    
    # 启动新容器
    docker run -d \
        --name ${CONTAINER_NAME} \
        --network host \
        -e GATEWAY_HOST=${GATEWAY_HOST} \
        -e GATEWAY_PORT=${GATEWAY_PORT} \
        vehicle-client:latest \
        --vehicle-id ${VEHICLE_ID} \
        --mode ${MODE} \
        --interval ${INTERVAL}
    
    echo -e "${GREEN}✓${NC} 启动客户端 ${i}: ${VEHICLE_ID} (容器: ${CONTAINER_NAME})"
    
    # 避免同时启动太多，稍微延迟
    sleep 0.5
done

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}所有客户端已启动${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

echo "管理命令:"
echo "  查看所有客户端: docker ps | grep vehicle-client"
echo "  查看客户端日志: docker logs -f vehicle-client-1"
echo "  停止所有客户端: docker stop \$(docker ps -q --filter name=vehicle-client)"
echo "  删除所有客户端: docker rm -f \$(docker ps -aq --filter name=vehicle-client)"
echo ""

echo "监控命令:"
echo "  实时查看日志: docker logs -f vehicle-client-1"
echo "  查看所有客户端状态: docker ps --filter name=vehicle-client --format 'table {{.Names}}\t{{.Status}}'"
echo ""
