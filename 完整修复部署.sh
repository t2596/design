#!/bin/bash
# 完整修复和重新部署脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "完整修复和重新部署"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 步骤 1: 检查当前状态
echo -e "\n${YELLOW}步骤 1: 检查当前部署状态${NC}"
kubectl get pods -n vehicle-iot-gateway

# 步骤 2: 备份现有数据（如果有）
echo -e "\n${YELLOW}步骤 2: 尝试备份现有数据${NC}"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  pg_dumpall -U postgres > backup_$(date +%Y%m%d_%H%M%S).sql 2>/dev/null || echo "无法备份（可能数据库不存在）"

# 步骤 3: 删除 PostgreSQL 部署
echo -e "\n${YELLOW}步骤 3: 删除现有 PostgreSQL 部署${NC}"
kubectl delete -f deployment/kubernetes/postgres-deployment.yaml || true
sleep 5

# 步骤 4: 重新应用 ConfigMap
echo -e "\n${YELLOW}步骤 4: 应用 PostgreSQL 初始化 ConfigMap${NC}"
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml

# 步骤 5: 重新部署 PostgreSQL
echo -e "\n${YELLOW}步骤 5: 重新部署 PostgreSQL${NC}"
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml

# 等待 PostgreSQL 就绪
echo -e "\n${YELLOW}等待 PostgreSQL 就绪...${NC}"
kubectl wait --for=condition=ready pod -l app=postgres -n vehicle-iot-gateway --timeout=120s

# 步骤 6: 验证数据库
echo -e "\n${YELLOW}步骤 6: 验证数据库${NC}"
sleep 10  # 额外等待确保数据库完全初始化

echo "检查数据库是否存在..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -c "\l" | grep gateway_db

echo "检查表是否存在..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c "\dt"

# 步骤 7: 重新构建 Gateway 镜像
echo -e "\n${YELLOW}步骤 7: 重新构建 Gateway 镜像${NC}"
docker build -t vehicle-iot-gateway:latest .

# 如果使用远程仓库，取消注释以下行
# echo "推送镜像到远程仓库..."
# docker tag vehicle-iot-gateway:latest your-registry/vehicle-iot-gateway:latest
# docker push your-registry/vehicle-iot-gateway:latest

# 步骤 8: 重启 Gateway 部署
echo -e "\n${YELLOW}步骤 8: 重启 Gateway 部署${NC}"
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 等待 Gateway 就绪
echo -e "\n${YELLOW}等待 Gateway 就绪...${NC}"
kubectl rollout status deployment/gateway -n vehicle-iot-gateway

# 步骤 9: 验证所有服务
echo -e "\n${YELLOW}步骤 9: 验证所有服务${NC}"
kubectl get pods -n vehicle-iot-gateway

# 步骤 10: 测试数据库连接
echo -e "\n${YELLOW}步骤 10: 测试数据库连接${NC}"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c "SELECT 1 as test;"

# 步骤 11: 检查 Gateway 日志
echo -e "\n${YELLOW}步骤 11: 检查 Gateway 日志（最近 20 行）${NC}"
kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=20

echo -e "\n${GREEN}=========================================="
echo "部署完成！"
echo "==========================================${NC}"

echo -e "\n${YELLOW}下一步：${NC}"
echo "1. 运行客户端测试："
echo "   python client/vehicle_client.py --vehicle-id TEST001 --gateway-host 8.147.67.31 --gateway-port 32620 --mode continuous --interval 10"
echo ""
echo "2. 检查数据是否写入："
echo "   kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- psql -U gateway_user -d gateway_db -c \"SELECT COUNT(*) FROM vehicle_data;\""
echo ""
echo "3. 访问 Web 界面："
echo "   http://8.147.67.31:32620/"
