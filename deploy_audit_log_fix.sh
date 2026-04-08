#!/bin/bash

# 部署审计日志修复脚本
# 用于应用问题2的修复

set -e

echo "=========================================="
echo "部署审计日志修复"
echo "=========================================="
echo ""

# 检查是否在Kubernetes环境中
if ! kubectl get namespace vehicle-iot-gateway &> /dev/null; then
    echo "错误: 找不到 vehicle-iot-gateway 命名空间"
    echo "请确保Kubernetes集群正在运行"
    exit 1
fi

# 1. 重新构建Gateway镜像
echo "步骤 1: 重新构建Gateway镜像..."
docker build -t vehicle-iot-gateway:latest .

if [ $? -ne 0 ]; then
    echo "错误: 镜像构建失败"
    exit 1
fi

echo "✓ 镜像构建成功"
echo ""

# 2. 重启Gateway Pod
echo "步骤 2: 重启Gateway Pod..."
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

if [ $? -ne 0 ]; then
    echo "错误: Gateway重启失败"
    exit 1
fi

echo "✓ Gateway重启成功"
echo ""

# 3. 等待Pod就绪
echo "步骤 3: 等待Gateway Pod就绪..."
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s

if [ $? -ne 0 ]; then
    echo "警告: Gateway Pod未在120秒内就绪"
    echo "请手动检查Pod状态: kubectl get pods -n vehicle-iot-gateway"
else
    echo "✓ Gateway Pod已就绪"
fi

echo ""

# 4. 检查Pod状态
echo "步骤 4: 检查Pod状态..."
kubectl get pods -n vehicle-iot-gateway

echo ""

# 5. 查看Gateway日志（最后20行）
echo "步骤 5: 查看Gateway日志..."
kubectl logs -l app=gateway -n vehicle-iot-gateway --tail=20

echo ""
echo "=========================================="
echo "部署完成"
echo "=========================================="
echo ""
echo "下一步操作："
echo "1. 运行测试脚本生成审计日志数据："
echo "   python3 generate_audit_test_data.py"
echo ""
echo "2. 验证审计日志API："
echo "   bash test_audit_logs_api.sh"
echo ""
echo "3. 检查数据库中的审计日志："
echo "   kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \\"
echo "     psql -U postgres -d vehicle_iot_gateway -c \\"
echo "     \"SELECT COUNT(*) FROM audit_logs;\""
echo ""
