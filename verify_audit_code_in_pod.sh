#!/bin/bash

# 验证Gateway Pod中的代码是否包含审计日志功能

echo "========================================="
echo "验证Gateway Pod中的审计日志代码"
echo "========================================="
echo ""

# 1. 获取Gateway Pod名称
POD_NAME=$(kubectl get pods -n vehicle-iot-gateway -l app=gateway -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "错误：找不到Gateway Pod"
    exit 1
fi

echo "Gateway Pod: $POD_NAME"
echo ""

# 2. 检查auth.py文件中是否有audit_logger
echo "1. 检查auth.py中是否有audit_logger导入"
echo "----------------------------------------"
kubectl exec -n vehicle-iot-gateway $POD_NAME -- \
  grep -n "from src.audit_logger import AuditLogger" /app/src/api/routes/auth.py 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ 找到audit_logger导入"
else
    echo "✗ 没有找到audit_logger导入 - 这是问题所在！"
fi
echo ""

# 3. 检查是否有log_auth_event调用
echo "2. 检查auth.py中是否有log_auth_event调用"
echo "----------------------------------------"
kubectl exec -n vehicle-iot-gateway $POD_NAME -- \
  grep -n "log_auth_event" /app/src/api/routes/auth.py 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ 找到log_auth_event调用"
else
    echo "✗ 没有找到log_auth_event调用 - 这是问题所在！"
fi
echo ""

# 4. 检查是否有log_data_transfer调用
echo "3. 检查auth.py中是否有log_data_transfer调用"
echo "----------------------------------------"
kubectl exec -n vehicle-iot-gateway $POD_NAME -- \
  grep -n "log_data_transfer" /app/src/api/routes/auth.py 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ 找到log_data_transfer调用"
else
    echo "✗ 没有找到log_data_transfer调用"
fi
echo ""

# 5. 查看register_vehicle函数的部分代码
echo "4. 查看register_vehicle函数中的审计日志代码"
echo "----------------------------------------"
kubectl exec -n vehicle-iot-gateway $POD_NAME -- \
  grep -A 5 "记录认证成功事件到审计日志" /app/src/api/routes/auth.py 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ 找到审计日志记录代码"
else
    echo "✗ 没有找到审计日志记录代码 - Pod中的代码是旧版本！"
fi
echo ""

# 6. 检查audit_logger.py文件是否存在
echo "5. 检查audit_logger.py文件"
echo "----------------------------------------"
kubectl exec -n vehicle-iot-gateway $POD_NAME -- \
  ls -lh /app/src/audit_logger.py 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ audit_logger.py文件存在"
else
    echo "✗ audit_logger.py文件不存在"
fi
echo ""

# 7. 检查Gateway镜像信息
echo "6. Gateway镜像信息"
echo "----------------------------------------"
kubectl get deployment gateway -n vehicle-iot-gateway -o jsonpath='{.spec.template.spec.containers[0].image}'
echo ""
echo ""

kubectl describe pod $POD_NAME -n vehicle-iot-gateway | grep "Image:"
echo ""

echo "========================================="
echo "验证完成"
echo "========================================="
echo ""

echo "结论："
echo "如果上面显示'没有找到'，说明Gateway Pod中运行的是旧代码"
echo ""
echo "解决方案："
echo "1. 重新构建Gateway镜像（包含审计日志代码）"
echo "2. 推送到镜像仓库"
echo "3. 更新Kubernetes部署"
echo ""
echo "或者简单地重启Pod（如果镜像已更新）："
echo "  kubectl rollout restart deployment/gateway -n vehicle-iot-gateway"
echo ""
