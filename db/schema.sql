-- 车联网安全通信网关系统数据库架构

-- 证书表
CREATE TABLE IF NOT EXISTS certificates (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(64) UNIQUE NOT NULL,
    version INTEGER NOT NULL,
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP NOT NULL,
    public_key BYTEA NOT NULL,
    signature BYTEA NOT NULL,
    signature_algorithm VARCHAR(32) NOT NULL,
    extensions JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_period CHECK (valid_from < valid_to)
);

-- 证书序列号索引
CREATE INDEX IF NOT EXISTS idx_certificates_serial_number ON certificates(serial_number);
CREATE INDEX IF NOT EXISTS idx_certificates_valid_period ON certificates(valid_from, valid_to);

-- 证书撤销列表（CRL）
CREATE TABLE IF NOT EXISTS certificate_revocation_list (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(64) NOT NULL,
    revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    CONSTRAINT fk_certificate FOREIGN KEY (serial_number) REFERENCES certificates(serial_number)
);

-- CRL 索引
CREATE INDEX IF NOT EXISTS idx_crl_serial_number ON certificate_revocation_list(serial_number);

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    log_id VARCHAR(64) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    vehicle_id VARCHAR(64) NOT NULL,
    operation_result BOOLEAN NOT NULL,
    details TEXT CHECK (LENGTH(details) <= 1024),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 审计日志索引
CREATE INDEX IF NOT EXISTS idx_audit_logs_log_id ON audit_logs(log_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_vehicle_id ON audit_logs(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);

-- 创建视图：有效证书
CREATE OR REPLACE VIEW valid_certificates AS
SELECT c.*
FROM certificates c
LEFT JOIN certificate_revocation_list crl ON c.serial_number = crl.serial_number
WHERE crl.serial_number IS NULL
  AND c.valid_from <= CURRENT_TIMESTAMP
  AND c.valid_to >= CURRENT_TIMESTAMP;

-- 安全策略配置表
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

-- 认证失败记录表
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
