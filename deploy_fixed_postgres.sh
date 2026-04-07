#!/bin/bash

# 修复 PostgreSQL 用户配置并重新部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE="vehicle-iot-gateway"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}修复 PostgreSQL 用户配置${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${YELLOW}修复内容：${NC}"
echo "1. 将 POSTGRES_USER 从 'gateway_user' 改为 'postgres'"
echo "2. 添加初始化脚本创建 'gateway_user' 用户"
echo "3. 授予 'gateway_user' 所有必要权限"
echo ""

# 步骤 1: 删除现有 PostgreSQL
echo -e "${YELLOW}步骤 1: 删除现有 PostgreSQL 部署${NC}"
kubectl delete deployment postgres -n $NAMESPACE --ignore-not-found=true
echo "等待 Pod 完全删除..."
kubectl wait --for=delete pod -l app=postgres -n $NAMESPACE --timeout=60s 2>/dev/null || true
sleep 5

# 步骤 2: 应用修复后的配置
echo -e "\n${YELLOW}步骤 2: 应用修复后的配置${NC}"

echo "应用 Secrets..."
kubectl apply -f deployment/kubernetes/secrets.yaml

echo "应用 ConfigMap..."
kubectl apply -f deployment/kubernetes/configmap.yaml

echo "应用 PostgreSQL 初始化脚本..."
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml

# 步骤 3: 重新部署 PostgreSQL
echo -e "\n${YELLOW}步骤 3: 重新部署 PostgreSQL${NC}"
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml

echo "等待 PostgreSQL Pod 就绪..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=120s

sleep 10

# 步骤 4: 检查初始化日志
echo -e "\n${YELLOW}步骤 4: 检查初始化日志${NC}"
kubectl logs -n $NAMESPACE -l app=postgres --tail=100 | grep -A 5 -B 5 "init\|CREATE\|GRANT" || true

# 步骤 5: 验证数据库
echo -e "\n${YELLOW}步骤 5: 验证数据库${NC}"

echo "检查数据库是否存在..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U postgres -c "\l" | grep vehicle_iot_gateway

echo -e "\n检查用户是否存在..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U postgres -c "\du" | grep gateway_user

echo -e "\n检查表是否存在..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt"

# 步骤 6: 测试 gateway_user 权限
echo -e "\n${YELLOW}步骤 6: 测试 gateway_user 权限${NC}"

echo "测试 gateway_user 连接..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U gateway_user -d vehicle_iot_gateway -c "SELECT 1 as test;"

echo -e "\n测试 gateway_user 写入权限..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U gateway_user -d vehicle_iot_gateway -c \
  "INSERT INTO vehicle_data (vehicle_id, timestamp, state, motion_speed) 
   VALUES ('TEST_USER', NOW(), '测试', 99) 
   ON CONFLICT (vehicle_id, timestamp) DO NOTHING;"

echo -e "\n查询测试数据..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U gateway_user -d vehicle_iot_gateway -c \
  "SELECT vehicle_id, timestamp, state, motion_speed FROM vehicle_data WHERE vehicle_id='TEST_USER';"

# 步骤 7: 重启 Gateway
echo -e "\n${YELLOW}步骤 7: 重启 Gateway${NC}"
kubectl rollout restart deployment/gateway -n $NAMESPACE
kubectl wait --for=condition=ready pod -l app=gateway -n $NAMESPACE --timeout=120s

sleep 5

# 步骤 8: 检查 Gateway 环境变量
echo -e "\n${YELLOW}步骤 8: 检查 Gateway 配置${NC}"
echo "Gateway 的 PostgreSQL 配置："
kubectl exec -it deployment/gateway -n $NAMESPACE -- env | grep POSTGRES

# 总结
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}修复完成！${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo "验证结果："
echo "✓ PostgreSQL 使用 'postgres' 超级用户"
echo "✓ 数据库 'vehicle_iot_gateway' 已创建"
echo "✓ 用户 'gateway_user' 已创建并授权"
echo "✓ 所有表已创建"
echo "✓ Gateway 已重启"
echo ""

echo "下一步："
echo "1. 运行客户端测试："
echo "   cd client && python vehicle_client.py --gateway-host <IP> --gateway-port <PORT> --mode continuous --iterations 5"
echo ""
echo "2. 检查数据写入："
echo "   kubectl exec -it deployment/postgres -n $NAMESPACE -- \\"
echo "     psql -U gateway_user -d vehicle_iot_gateway -c \\"
echo "     \"SELECT COUNT(*) FROM vehicle_data;\""
echo ""
echo "3. 访问 Web 界面查看数据"
echo ""
