-- 初始化数据脚本
-- 用于开发和测试环境

BEGIN;

-- 插入示例 CA 证书（仅用于开发测试）
-- 注意：生产环境应使用真实的 CA 证书
INSERT INTO certificates (
    serial_number,
    version,
    issuer,
    subject,
    valid_from,
    valid_to,
    public_key,
    signature,
    signature_algorithm,
    extensions
) VALUES (
    'CA-ROOT-001',
    3,
    'CN=Vehicle IoT CA, O=Security Gateway, C=CN',
    'CN=Vehicle IoT CA, O=Security Gateway, C=CN',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP + INTERVAL '10 years',
    decode('0000000000000000000000000000000000000000000000000000000000000000', 'hex'),
    decode('0000000000000000000000000000000000000000000000000000000000000000', 'hex'),
    'SM2',
    '{"keyUsage": ["keyCertSign", "cRLSign"], "basicConstraints": {"ca": true}}'::jsonb
) ON CONFLICT (serial_number) DO NOTHING;

-- 注意：不再插入测试审计日志
-- 审计日志将在实际操作时自动生成
-- 有效的 event_type 值包括：
--   VEHICLE_CONNECT, VEHICLE_DISCONNECT,
--   AUTHENTICATION_SUCCESS, AUTHENTICATION_FAILURE,
--   DATA_ENCRYPTED, DATA_DECRYPTED,
--   CERTIFICATE_ISSUED, CERTIFICATE_REVOKED,
--   SIGNATURE_VERIFIED, SIGNATURE_FAILED

-- 插入默认安全策略配置
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

COMMIT;
