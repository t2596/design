#!/bin/bash
# 修复 latest_vehicle_data 视图问题

echo "=========================================="
echo "步骤 1: 检查视图是否存在"
echo "=========================================="
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dv"

echo ""
echo "=========================================="
echo "步骤 2: 创建 latest_vehicle_data 视图"
echo "=========================================="
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway <<'EOF'
-- 创建视图：最新车辆数据
CREATE OR REPLACE VIEW latest_vehicle_data AS
SELECT DISTINCT ON (vehicle_id)
    vehicle_id,
    timestamp,
    received_at,
    state,
    gps_latitude,
    gps_longitude,
    gps_altitude,
    gps_heading,
    gps_satellites,
    motion_speed,
    motion_acceleration,
    motion_odometer,
    motion_trip_distance,
    fuel_level,
    fuel_consumption,
    fuel_range,
    temp_engine,
    temp_cabin,
    temp_outside,
    battery_voltage,
    battery_current,
    diag_engine_load,
    diag_rpm,
    diag_throttle_position,
    raw_data
FROM vehicle_data
ORDER BY vehicle_id, timestamp DESC;
EOF

echo ""
echo "=========================================="
echo "步骤 3: 授予 gateway_user 视图权限"
echo "=========================================="
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "GRANT SELECT ON latest_vehicle_data TO gateway_user;"

echo ""
echo "=========================================="
echo "步骤 4: 验证视图查询（使用 postgres 用户）"
echo "=========================================="
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT * FROM latest_vehicle_data WHERE vehicle_id='VIN1234';"

echo ""
echo "=========================================="
echo "步骤 5: 验证视图查询（使用 gateway_user）"
echo "=========================================="
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U gateway_user -d vehicle_iot_gateway -c \
  "SELECT * FROM latest_vehicle_data WHERE vehicle_id='VIN1234';"

echo ""
echo "=========================================="
echo "完成！现在刷新 Web 页面应该能看到数据了"
echo "=========================================="
