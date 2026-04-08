#!/bin/bash
# 验证部署脚本

echo "=========================================="
echo "验证部署状态"
echo "=========================================="

# 1. 检查所有 Pod 状态
echo -e "\n1. 检查 Pod 状态..."
kubectl get pods -n vehicle-iot-gateway

# 2. 检查数据库是否存在
echo -e "\n2. 检查数据库..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -c "\l" | grep gateway_db

# 3. 检查表是否存在
echo -e "\n3. 检查数据表..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c "\dt" | grep -E "vehicle_data|certificates|audit_logs"

# 4. 检查 vehicle_data 表结构
echo -e "\n4. 检查 vehicle_data 表结构..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c "\d vehicle_data"

# 5. 测试 Gateway API
echo -e "\n5. 测试 Gateway 健康检查..."
curl -s http://8.147.67.31:32620/health

# 6. 检查 Gateway 日志
echo -e "\n\n6. Gateway 日志（最近 30 行）..."
kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=30

echo -e "\n=========================================="
echo "验证完成"
echo "=========================================="
