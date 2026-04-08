-- 安全策略配置表
-- 用于持久化系统安全配置

CREATE TABLE IF NOT EXISTS security_policy (
    id SERIAL PRIMARY KEY,
    session_timeout INTEGER NOT NULL DEFAULT 86400,
    certificate_validity INTEGER NOT NULL DEFAULT 365,
    timestamp_tolerance INTEGER NOT NULL DEFAULT 300,
    concurrent_session_strategy VARCHAR(20) NOT NULL DEFAULT 'reject_new',
    max_auth_failures INTEGER NOT NULL DEFAULT 5,
    auth_failure_lockout_duration INTEGER NOT NULL DEFAULT 300,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(64),
    CONSTRAINT valid_session_timeout CHECK (session_timeout >= 300 AND session_timeout <= 604800),
    CONSTRAINT valid_certificate_validity CHECK (certificate_validity >= 30 AND certificate_validity <= 1825),
    CONSTRAINT valid_timestamp_tolerance CHECK (timestamp_tolerance >= 60 AND timestamp_tolerance <= 600),
    CONSTRAINT valid_concurrent_strategy CHECK (concurrent_session_strategy IN ('reject_new', 'terminate_old')),
    CONSTRAINT valid_max_auth_failures CHECK (max_auth_failures >= 3 AND max_auth_failures <= 10),
    CONSTRAINT valid_lockout_duration CHECK (auth_failure_lockout_duration >= 60 AND auth_failure_lockout_duration <= 3600)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_security_policy_updated_at ON security_policy(updated_at DESC);

-- 插入默认配置
INSERT INTO security_policy (
    session_timeout,
    certificate_validity,
    timestamp_tolerance,
    concurrent_session_strategy,
    max_auth_failures,
    auth_failure_lockout_duration,
    updated_by
) VALUES (
    86400,      -- 24小时会话超时
    365,        -- 1年证书有效期
    300,        -- 5分钟时间戳容差
    'reject_new', -- 拒绝新会话策略
    5,          -- 最多5次认证失败
    300,        -- 5分钟锁定时长
    'system'
) ON CONFLICT DO NOTHING;

-- 创建认证失败记录表
CREATE TABLE IF NOT EXISTS auth_failure_records (
    id SERIAL PRIMARY KEY,
    vehicle_id VARCHAR(64) NOT NULL,
    failure_count INTEGER NOT NULL DEFAULT 1,
    first_failure_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_failure_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_until TIMESTAMP,
    CONSTRAINT unique_vehicle_id UNIQUE (vehicle_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_auth_failure_vehicle_id ON auth_failure_records(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_auth_failure_locked_until ON auth_failure_records(locked_until);

-- 添加注释
COMMENT ON TABLE security_policy IS '系统安全策略配置表';
COMMENT ON TABLE auth_failure_records IS '认证失败记录表，用于实现认证失败锁定功能';
