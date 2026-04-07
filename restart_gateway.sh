#!/bin/bash
# 重启 Gateway 以应用代码修复

echo "重启 Gateway Pods..."
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

echo "等待 Gateway 重启完成..."
kubectl rollout status deployment/gateway -n vehicle-iot-gateway

echo ""
echo "Gateway 重启完成！"
echo "现在刷新 Web 页面应该能看到车辆数据了"
