#!/bin/bash

# 车联网安全通信网关 - Kubernetes 清理脚本
# 删除所有部署的资源

set -e

echo "=========================================="
echo "车联网安全通信网关 - 清理部署"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 确认操作
echo -e "${YELLOW}警告: 此操作将删除 vehicle-iot-gateway namespace 中的所有资源${NC}"
echo -e "${YELLOW}包括: Deployments, Services, ConfigMaps, Secrets${NC}"
echo ""
read -p "确认继续？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

echo ""
echo "开始清理..."
echo ""

# 删除 Deployments
echo "删除 Deployments..."
kubectl delete deployment --all -n vehicle-iot-gateway 2>/dev/null || echo "  (无 Deployments)"

# 删除 Services
echo "删除 Services..."
kubectl delete service --all -n vehicle-iot-gateway 2>/dev/null || echo "  (无 Services)"

# 删除 ConfigMaps
echo "删除 ConfigMaps..."
kubectl delete configmap --all -n vehicle-iot-gateway 2>/dev/null || echo "  (无 ConfigMaps)"

# 删除 Secrets
echo "删除 Secrets..."
kubectl delete secret --all -n vehicle-iot-gateway 2>/dev/null || echo "  (无 Secrets)"

# 可选：删除 Namespace
echo ""
read -p "是否删除整个 namespace？(yes/no): " delete_ns

if [ "$delete_ns" = "yes" ]; then
    echo "删除 Namespace..."
    kubectl delete namespace vehicle-iot-gateway
    echo -e "${GREEN}✓ Namespace 已删除${NC}"
else
    echo "保留 Namespace"
fi

echo ""
echo "=========================================="
echo "清理完成"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ 所有资源已清理${NC}"
echo ""
echo "验证："
echo "  kubectl get all -n vehicle-iot-gateway"
echo ""
