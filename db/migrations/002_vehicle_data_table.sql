-- 车辆数据表迁移脚本
-- 用于存储车辆实时传感器数据

-- 车辆数据表
CREATE TABLE IF NOT EXISTS vehicle_data (
    id SERIAL PRIMARY KEY,
    vehicle_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 车辆状态
    state VARCHAR(32),
    
    -- GPS 数据
    gps_latitude DECIMAL(10, 6),
    gps_longitude DECIMAL(10, 6),
    gps_altitude DECIMAL(8, 2),
    gps_heading DECIMAL(5, 2),
    gps_satellites INTEGER,
    
    -- 运动数据
    motion_speed DECIMAL(6, 2),
    motion_acceleration DECIMAL(6, 2),
    motion_odometer INTEGER,
    motion_trip_distance DECIMAL(10, 2),
    
    -- 燃油数据
    fuel_level DECIMAL(5, 2),
    fuel_consumption DECIMAL(6, 2),
    fuel_range DECIMAL(8, 2),
    
    -- 温度数据
    temp_engine DECIMAL(5, 2),
    temp_cabin DECIMAL(5, 2),
    temp_outside DECIMAL(5, 2),
    
    -- 电池数据
    battery_voltage DECIMAL(5, 2),
    battery_current DECIMAL(6, 2),
    
    -- 诊断数据
    diag_engine_load DECIMAL(5, 2),
    diag_rpm INTEGER,
    diag_throttle_position DECIMAL(5, 2),
    
    -- 原始 JSON 数据（备份）
    raw_data JSONB,
    
    -- 索引
    CONSTRAINT vehicle_data_unique UNIQUE (vehicle_id, timestamp)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_vehicle_data_vehicle_id ON vehicle_data(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_data_timestamp ON vehicle_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vehicle_data_received_at ON vehicle_data(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_vehicle_data_vehicle_timestamp ON vehicle_data(vehicle_id, timestamp DESC);

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

-- 创建函数：清理旧数据（保留最近 7 天）
CREATE OR REPLACE FUNCTION cleanup_old_vehicle_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM vehicle_data
    WHERE received_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 注释
COMMENT ON TABLE vehicle_data IS '车辆实时传感器数据表';
COMMENT ON COLUMN vehicle_data.vehicle_id IS '车辆标识（VIN）';
COMMENT ON COLUMN vehicle_data.timestamp IS '数据采集时间（车端时间）';
COMMENT ON COLUMN vehicle_data.received_at IS '数据接收时间（服务器时间）';
COMMENT ON COLUMN vehicle_data.state IS '车辆状态（停车/怠速/加速/巡航/减速/刹车）';
COMMENT ON COLUMN vehicle_data.raw_data IS '原始 JSON 数据备份';
