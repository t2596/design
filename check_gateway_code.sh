#!/bin/bash

# 检查Gateway是否使用了最新代码

echo "========================================="
echo "检查Gateway代码版本"
echo "========================================="
echo ""

# 1. 检查Gateway Pod
echo "1. Gateway Pod信息"
echo "----------------------------------------"
kubectl get pods -n vehicle-iot-gateway -l app=gateway -o wide
echo ""

# 2. 检查Gateway镜像
echo "2. Gateway使用的镜像"
echo "----------------------------------------"
kubectl get deployment gateway -n vehicle-iot-gateway -o jsonpath='{.spec.template.spec.containers[0].image}'
echo ""
echo ""

# 3. 检查Gateway日志，看是否有审计日志相关的输出
echo "3. 检查Gateway日志（最近50行）"
echo "----------------------------------------"
kubectl logs deployment/gateway -n vehicle-iot-gateway --tail=50
echo ""

# 4. 检查数据库中的audit_logs表结构
echo "4. 检查audit_logs表结构"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\d audit_logs"
echo ""

# 5. 检查数据库中的数据
echo "5. 检查数据库中的所有表"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt"
echo ""

# 6. 尝试手动插入一条审计日志
echo "6. 尝试手动插入测试审计日志"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "
    INSERT INTO audit_logs (log_id, timestamp, event_type, vehicle_id, operation_result, details, ip_address)
    VALUES ('TEST-LOG-001', NOW(), 'TEST_EVENT', 'TEST-VEHICLE', true, '手动测试日志', '127.0.0.1')
    ON CONFLICT (log_id) DO NOTHING;
  "
echo ""

# 7. 查询刚插入的数据
echo "7. 查询审计日志"
echo "----------------------------------------"
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 5;"
echo ""

echo "========================================="
echo "检查完成"
echo "========================================="
echo ""

echo "分析："
echo "- 如果手动插入成功，说明数据库表结构正常"
echo "- 如果Gateway日志中没有审计相关输出，说明代码没有执行"
echo "- 可能原因：Gateway Pod使用的是旧镜像"
echo ""
