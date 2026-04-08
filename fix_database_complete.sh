#!/bin/bash

# 车辆数据存储问题 - 完整修复脚本
# 解决数据库名称不一致和初始化失败问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
NAMESPACE="vehicle-iot-gateway"
DB_NAME="vehicle_iot_gateway"  # 正确的数据库名（来自 ConfigMap）
DB_USER="gateway_user"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}车辆数据存储问题 - 完整修复${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 步骤 1: 检查当前状态
echo -e "${YELLOW}步骤 1: 检查当前状态${NC}"
echo "检查 PostgreSQL Pod 状态..."
kubectl get pods -n $NAMESPACE -l app=postgres

echo -e "\n检查当前数据库..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U postgres -c "\l" 2>/dev/null || echo "数据库连接失败或数据库不存在"

# 步骤 2: 备份重要数据（如果有）
echo -e "\n${YELLOW}步骤 2: 备份数据（如果存在）${NC}"
echo "尝试备份现有数据..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  pg_dump -U $DB_USER -d $DB_NAME > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql 2>/dev/null \
  && echo "✓ 数据已备份到 /tmp/backup_*.sql" \
  || echo "⚠ 无法备份（数据库可能不存在）"

# 步骤 3: 删除 PostgreSQL 部署
echo -e "\n${YELLOW}步骤 3: 删除 PostgreSQL 部署${NC}"
echo "删除 PostgreSQL Deployment..."
kubectl delete deployment postgres -n $NAMESPACE --ignore-not-found=true

echo "等待 Pod 完全删除..."
kubectl wait --for=delete pod -l app=postgres -n $NAMESPACE --timeout=60s 2>/dev/null || true

sleep 5

# 步骤 4: 重新应用 ConfigMap
echo -e "\n${YELLOW}步骤 4: 重新应用 ConfigMap${NC}"
echo "应用 postgres-init-configmap.yaml..."
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml

echo "应用 configmap.yaml..."
kubectl apply -f deployment/kubernetes/configmap.yaml

echo "应用 secrets.yaml..."
kubectl apply -f deployment/kubernetes/secrets.yaml

# 步骤 5: 重新部署 PostgreSQL
echo -e "\n${YELLOW}步骤 5: 重新部署 PostgreSQL${NC}"
echo "部署 PostgreSQL..."
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml

echo "等待 PostgreSQL Pod 就绪..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=120s

sleep 10

# 步骤 6: 检查初始化日志
echo -e "\n${YELLOW}步骤 6: 检查初始化日志${NC}"
echo "PostgreSQL 初始化日志（最后 50 行）："
kubectl logs -n $NAMESPACE -l app=postgres --tail=50 | grep -i "init\|database\|creating\|ready" || true

# 步骤 7: 验证数据库
echo -e "\n${YELLOW}步骤 7: 验证数据库${NC}"

echo "检查数据库是否存在..."
DB_EXISTS=$(kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | tr -d '\r')

if [ "$DB_EXISTS" = "1" ]; then
    echo -e "${GREEN}✓ 数据库 $DB_NAME 存在${NC}"
else
    echo -e "${RED}✗ 数据库 $DB_NAME 不存在，尝试手动创建...${NC}"
    
    # 手动创建数据库
    kubectl exec -it deployment/postgres -n $NAMESPACE -- \
      psql -U postgres -c "CREATE DATABASE $DB_NAME;"
    
    kubectl exec -it deployment/postgres -n $NAMESPACE -- \
      psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    
    echo "手动执行初始化脚本..."
    kubectl exec -i deployment/postgres -n $NAMESPACE -- \
      psql -U $DB_USER -d $DB_NAME < <(kubectl get configmap postgres-init-scripts -n $NAMESPACE -o jsonpath='{.data.01-schema\.sql}')
fi

# 步骤 8: 检查表
echo -e "\n${YELLOW}步骤 8: 检查表结构${NC}"
echo "检查表是否存在..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U $DB_USER -d $DB_NAME -c "\dt"

echo -e "\n检查视图是否存在..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U $DB_USER -d $DB_NAME -c "\dv"

# 步骤 9: 测试数据写入
echo -e "\n${YELLOW}步骤 9: 测试数据写入${NC}"
echo "插入测试数据..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U $DB_USER -d $DB_NAME -c \
  "INSERT INTO vehicle_data (vehicle_id, timestamp, state, motion_speed, gps_latitude, gps_longitude) 
   VALUES ('TEST_FIX', NOW(), '测试', 99, 39.9042, 116.4074) 
   ON CONFLICT (vehicle_id, timestamp) DO NOTHING;"

echo "查询测试数据..."
kubectl exec -it deployment/postgres -n $NAMESPACE -- \
  psql -U $DB_USER -d $DB_NAME -c \
  "SELECT vehicle_id, timestamp, state, motion_speed, gps_latitude, gps_longitude 
   FROM vehicle_data WHERE vehicle_id='TEST_FIX';"

# 步骤 10: 重启 Gateway
echo -e "\n${YELLOW}步骤 10: 重启 Gateway${NC}"
echo "重启 Gateway Deployment..."
kubectl rollout restart deployment/gateway -n $NAMESPACE

echo "等待 Gateway Pod 就绪..."
kubectl wait --for=condition=ready pod -l app=gateway -n $NAMESPACE --timeout=120s

sleep 5

# 步骤 11: 检查 Gateway 环境变量
echo -e "\n${YELLOW}步骤 11: 检查 Gateway 配置${NC}"
echo "Gateway 的 PostgreSQL 配置："
kubectl exec -it deployment/gateway -n $NAMESPACE -- env | grep POSTGRES || true

# 步骤 12: 检查 Gateway 日志
echo -e "\n${YELLOW}步骤 12: 检查 Gateway 日志${NC}"
echo "Gateway 最新日志（最后 20 行）："
kubectl logs -n $NAMESPACE -l app=gateway --tail=20

# 步骤 13: 测试 API
echo -e "\n${YELLOW}步骤 13: 测试 Gateway API${NC}"
echo "获取 Gateway Service 信息..."
kubectl get svc -n $NAMESPACE gateway-service

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}修复完成！${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo "下一步操作："
echo "1. 运行客户端发送测试数据："
echo "   cd client && python vehicle_client.py --gateway-host <GATEWAY_IP> --gateway-port <PORT> --mode continuous --iterations 5"
echo ""
echo "2. 检查数据是否写入数据库："
echo "   kubectl exec -it deployment/postgres -n $NAMESPACE -- \\"
echo "     psql -U $DB_USER -d $DB_NAME -c \\"
echo "     \"SELECT vehicle_id, timestamp, state, motion_speed FROM vehicle_data ORDER BY timestamp DESC LIMIT 10;\""
echo ""
echo "3. 访问 Web 界面查看数据"
echo ""
echo "4. 如果仍有问题，查看详细日志："
echo "   kubectl logs -n $NAMESPACE -l app=gateway --tail=100"
echo ""
