-- 迁移脚本 001: 初始数据库架构
-- 创建时间: 2026-03-21
-- 描述: 创建证书、CRL 和审计日志表

BEGIN;

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

-- 证书索引
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

COMMIT;
