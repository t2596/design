#!/bin/bash

# 应用安全策略数据库迁移脚本

set -e

echo "=========================================="
echo "应用安全策略数据库迁移"
echo "=========================================="
echo ""

# 检查是否在Kubernetes环境中
if ! kubectl get namespace vehicle-iot-gateway &> /dev/null; then
    echo "错误: 找不到 vehicle-iot-gateway 命名空间"
    echo "请确保Kubernetes集群正在运行"
    exit 1
fi

# 应用迁移脚本
echo "步骤 1: 应用数据库迁移..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -f - < db/migrations/003_security_policy_table.sql

if [ $? -ne 0 ]; then
    echo "错误: 数据库迁移失败"
    exit 1
fi

echo "✓ 数据库迁移成功"
echo ""

# 验证表是否创建成功
echo "步骤 2: 验证表创建..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt security_policy"

kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt auth_failure_records"

echo ""

# 检查默认配置是否插入
echo "步骤 3: 检查默认配置..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM security_policy ORDER BY updated_at DESC LIMIT 1;"

echo ""
echo "=========================================="
echo "数据库迁移完成"
echo "=========================================="
echo ""
echo "下一步: 重新部署Gateway以应用代码更改"
