#!/bin/bash
# 数据流诊断脚本

echo "=========================================="
echo "车辆数据流诊断"
echo "=========================================="

# 获取车辆 ID（从参数或使用默认值）
VEHICLE_ID=${1:-"VIN1234"}

echo -e "\n1. 检查数据库中是否有数据..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "SELECT vehicle_id, timestamp, state, motion_speed, gps_latitude, gps_longitude FROM vehicle_data WHERE vehicle_id='$VEHICLE_ID' ORDER BY timestamp DESC LIMIT 5;"

echo -e "\n2. 检查数据库总记录数..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "SELECT COUNT(*) as total_records FROM vehicle_data;"

echo -e "\n3. 检查最新数据视图..."
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d gateway_db -c \
  "SELECT * FROM latest_vehicle_data WHERE vehicle_id='$VEHICLE_ID';"

echo -e "\n4. 测试 API 查询最新数据..."
GATEWAY_POD=$(kubectl get pods -n vehicle-iot-gateway -l app=gateway -o jsonpath='{.items[0].metadata.name}')
echo "Gateway Pod: $GATEWAY_POD"

kubectl exec -it $GATEWAY_POD -n vehicle-iot-gateway -- \
  curl -s "http://localhost:8000/api/vehicles/$VEHICLE_ID/data/latest" \
  -H "Authorization: Bearer dev-token-12345" | python3 -m json.tool

echo -e "\n5. 检查 Gateway 日志（最近 20 行）..."
kubectl logs -n vehicle-iot-gateway -l app=gateway --tail=20

echo -e "\n=========================================="
echo "诊断完成"
echo "=========================================="
