#!/bin/bash

# 车联网安全通信网关 - Kubernetes 一键部署脚本
# 使用 emptyDir（无 PVC）进行快速测试部署

set -e  # 遇到错误立即退出

echo "=========================================="
echo "车联网安全通信网关 - Kubernetes 部署"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 kubectl 是否安装
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}错误: kubectl 未安装${NC}"
    echo "请先安装 kubectl: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# 检查 kubectl 连接
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}错误: 无法连接到 Kubernetes 集群${NC}"
    echo "请检查 kubeconfig 配置"
    exit 1
fi

echo -e "${GREEN}✓ kubectl 已就绪${NC}"
echo ""

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "=========================================="
echo "步骤 1/7: 创建 Namespace"
echo "=========================================="
kubectl apply -f namespace.yaml
echo -e "${GREEN}✓ Namespace 创建完成${NC}"
echo ""

echo "=========================================="
echo "步骤 2/7: 创建 ConfigMaps"
echo "=========================================="
kubectl apply -f configmap.yaml
kubectl apply -f postgres-init-configmap.yaml
echo -e "${GREEN}✓ ConfigMaps 创建完成${NC}"
echo ""

echo "=========================================="
echo "步骤 3/7: 创建 Secrets"
echo "=========================================="
kubectl apply -f secrets.yaml
echo -e "${GREEN}✓ Secrets 创建完成${NC}"
echo ""

echo "=========================================="
echo "步骤 4/7: 部署 PostgreSQL"
echo "=========================================="
kubectl apply -f postgres-deployment.yaml
echo -e "${YELLOW}等待 PostgreSQL 就绪...${NC}"
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=120s || {
    echo -e "${RED}PostgreSQL 启动超时，查看日志：${NC}"
    kubectl logs -n vehicle-iot-gateway -l app=postgres --tail=50
    exit 1
}
echo -e "${GREEN}✓ PostgreSQL 部署完成${NC}"
echo ""

echo "=========================================="
echo "步骤 5/7: 部署 Redis"
echo "=========================================="
kubectl apply -f redis-deployment.yaml
echo -e "${YELLOW}等待 Redis 就绪...${NC}"
kubectl wait --for=condition=ready pod -l app=redis -n vehicle-iot-gateway --timeout=120s || {
    echo -e "${RED}Redis 启动超时，查看日志：${NC}"
    kubectl logs -n vehicle-iot-gateway -l app=redis --tail=50
    exit 1
}
echo -e "${GREEN}✓ Redis 部署完成${NC}"
echo ""

echo "=========================================="
echo "步骤 6/8: 部署网关"
echo "=========================================="
kubectl apply -f gateway-deployment.yaml
echo -e "${YELLOW}等待网关就绪...${NC}"
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s || {
    echo -e "${RED}网关启动超时，查看日志：${NC}"
    kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=50
    exit 1
}
echo -e "${GREEN}✓ 网关部署完成${NC}"
echo ""

echo "=========================================="
echo "步骤 7/8: 部署 Web 界面"
echo "=========================================="
kubectl apply -f web-deployment.yaml
echo -e "${YELLOW}等待 Web 界面就绪...${NC}"
kubectl wait --for=condition=ready pod -l app=web -n vehicle-iot-gateway --timeout=120s || {
    echo -e "${RED}Web 界面启动超时，查看日志：${NC}"
    kubectl logs -n vehicle-iot-gateway -l app=web --tail=50
    exit 1
}
echo -e "${GREEN}✓ Web 界面部署完成${NC}"
echo ""

echo "=========================================="
echo "步骤 8/8: 验证部署"
echo "=========================================="
echo ""
echo "Pod 状态："
kubectl get pods -n vehicle-iot-gateway
echo ""
echo "Service 状态："
kubectl get svc -n vehicle-iot-gateway
echo ""

# 获取网关访问地址
GATEWAY_SERVICE=$(kubectl get svc gateway-service -n vehicle-iot-gateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$GATEWAY_SERVICE" ]; then
    GATEWAY_SERVICE=$(kubectl get svc gateway-service -n vehicle-iot-gateway -o jsonpath='{.spec.clusterIP}')
fi
GATEWAY_PORT=$(kubectl get svc gateway-service -n vehicle-iot-gateway -o jsonpath='{.spec.ports[0].port}')

# 获取 Web 访问地址
WEB_NODE_PORT=$(kubectl get svc web-service -n vehicle-iot-gateway -o jsonpath='{.spec.ports[0].nodePort}')
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
if [ -z "$NODE_IP" ]; then
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
fi

echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ 所有服务已成功部署${NC}"
echo ""
echo "网关 API 访问地址："
echo "  内部地址: http://${GATEWAY_SERVICE}:${GATEWAY_PORT}"
echo "  健康检查: http://${GATEWAY_SERVICE}:${GATEWAY_PORT}/health"
echo "  API 文档: http://${GATEWAY_SERVICE}:${GATEWAY_PORT}/docs"
echo ""
echo "Web 管理界面访问地址："
echo "  外部地址: http://${NODE_IP}:${WEB_NODE_PORT}"
echo "  (NodePort: ${WEB_NODE_PORT})"
echo ""
echo "测试命令："
echo "  # 测试网关"
echo "  curl http://${GATEWAY_SERVICE}:${GATEWAY_PORT}/health"
echo ""
echo "  # 测试 Web 界面"
echo "  curl http://${NODE_IP}:${WEB_NODE_PORT}/health"
echo ""
echo "查看日志："
echo "  kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=50"
echo "  kubectl logs -n vehicle-iot-gateway -l app=web --tail=50"
echo ""
echo "端口转发（本地访问）："
echo "  # 网关 API"
echo "  kubectl port-forward -n vehicle-iot-gateway svc/gateway-service 8000:8000"
echo ""
echo "  # Web 界面"
echo "  kubectl port-forward -n vehicle-iot-gateway svc/web-service 3000:80"
echo "  然后访问: http://localhost:3000"
echo ""
echo -e "${YELLOW}注意: 使用 emptyDir 存储，Pod 重启后数据会丢失${NC}"
echo "详细说明: docs/NO_PVC_DEPLOYMENT.md"
echo ""
