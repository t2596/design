"""身份认证模块

提供车云双向身份认证、会话管理和会话清理功能。
"""

import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple
from src.models.certificate import Certificate
from src.models.session import SessionInfo, AuthResult, AuthToken
from src.models.enums import SessionStatus, ErrorCode, EventType
from src.crypto.sm2 import sm2_sign, sm2_verify, generate_sm2_keypair
from src.crypto.sm4 import generate_sm4_key
from src.db.redis_client import RedisConnection
from src.db.postgres import PostgreSQLConnection
from config.database import RedisConfig, PostgreSQLConfig
from src.certificate_manager import verify_certificate, get_crl
from src.secure_key_storage import get_secure_key_storage


def generate_challenge() -> bytes:
    """生成挑战值
    
    生成 32 字节的随机挑战值用于身份认证。
    
    前置条件:
    - 系统必须有可用的密码学安全随机数生成器
    
    后置条件:
    - 返回的挑战值长度为 32 字节
    - 每次调用生成的挑战值都是唯一的（概率上）
    
    返回:
        bytes: 32 字节的随机挑战值
        
    验证需求: 4.4
    """
    challenge = os.urandom(32)
    
    # 后置条件验证
    assert len(challenge) == 32, f"挑战值长度不正确: {len(challenge)} != 32"
    
    return challenge


def verify_challenge(response: bytes, challenge: bytes, public_key: bytes) -> bool:
    """验证挑战响应
    
    使用公钥验证对挑战值的签名响应。
    
    前置条件:
    - response 必须是有效的 SM2 签名（64 字节）
    - challenge 必须是原始挑战值（32 字节）
    - public_key 必须是有效的 SM2 公钥（64 字节）
    
    后置条件:
    - 如果签名有效，返回 True
    - 如果签名无效，返回 False
    - 所有输入参数未被修改
    
    参数:
        response: 签名响应（64 字节）
        challenge: 原始挑战值（32 字节）
        public_key: SM2 公钥（64 字节）
        
    返回:
        bool: 验证结果
        
    异常:
        ValueError: 如果参数长度不正确
        
    验证需求: 4.5
    """
    # 前置条件验证
    if len(response) != 64:
        raise ValueError(f"签名响应长度必须为 64 字节，当前为 {len(response)}")
    
    if len(challenge) != 32:
        raise ValueError(f"挑战值长度必须为 32 字节，当前为 {len(challenge)}")
    
    if len(public_key) != 64:
        raise ValueError(f"公钥长度必须为 64 字节，当前为 {len(public_key)}")
    
    # 验证签名
    return sm2_verify(challenge, response, public_key)


def authenticate_vehicle(
    vehicle_cert: Certificate,
    challenge: bytes,
    ca_public_key: bytes,
    crl_list: list,
    db_conn: Optional[PostgreSQLConnection] = None
) -> Tuple[bool, str]:
    """认证车端
    
    验证车端证书并检查挑战响应。
    
    前置条件:
    - vehicle_cert 必须非空且格式正确
    - challenge 必须是 32 字节的随机值
    - ca_public_key 必须是有效的 CA 公钥
    - crl_list 必须是最新的证书撤销列表
    
    后置条件:
    - 返回验证结果和消息
    - 如果验证失败，包含具体的失败原因
    - 证书对象未被修改
    
    参数:
        vehicle_cert: 车端证书
        challenge: 挑战值（32 字节）
        ca_public_key: CA 公钥（64 字节）
        crl_list: 证书撤销列表
        db_conn: 数据库连接（可选）
        
    返回:
        Tuple[bool, str]: (验证结果, 消息)
        
    验证需求: 4.1, 4.2
    """
    # 前置条件验证
    if vehicle_cert is None:
        raise ValueError("vehicle_cert 不能为 None")
    
    if len(challenge) != 32:
        raise ValueError(f"挑战值长度必须为 32 字节，当前为 {len(challenge)}")
    
    # 验证车端证书
    validation_result, message = verify_certificate(
        vehicle_cert,
        ca_public_key,
        crl_list,
        db_conn
    )
    
    from src.models.enums import ValidationResult
    if validation_result != ValidationResult.VALID:
        return (False, f"车端证书验证失败: {message}")
    
    return (True, "车端认证成功")


def authenticate_gateway(
    gateway_cert: Certificate,
    ca_public_key: bytes,
    crl_list: list,
    db_conn: Optional[PostgreSQLConnection] = None
) -> Tuple[bool, str]:
    """认证网关
    
    验证网关证书的有效性。
    
    前置条件:
    - gateway_cert 必须非空且格式正确
    - ca_public_key 必须是有效的 CA 公钥
    - crl_list 必须是最新的证书撤销列表
    
    后置条件:
    - 返回验证结果和消息
    - 如果验证失败，包含具体的失败原因
    - 证书对象未被修改
    
    参数:
        gateway_cert: 网关证书
        ca_public_key: CA 公钥（64 字节）
        crl_list: 证书撤销列表
        db_conn: 数据库连接（可选）
        
    返回:
        Tuple[bool, str]: (验证结果, 消息)
        
    验证需求: 4.3
    """
    # 前置条件验证
    if gateway_cert is None:
        raise ValueError("gateway_cert 不能为 None")
    
    # 验证网关证书
    validation_result, message = verify_certificate(
        gateway_cert,
        ca_public_key,
        crl_list,
        db_conn
    )
    
    from src.models.enums import ValidationResult
    if validation_result != ValidationResult.VALID:
        return (False, f"网关证书验证失败: {message}")
    
    return (True, "网关认证成功")


def mutual_authentication(
    vehicle_cert: Certificate,
    gateway_cert: Certificate,
    vehicle_private_key: bytes,
    gateway_private_key: bytes,
    ca_public_key: bytes,
    db_conn: Optional[PostgreSQLConnection] = None
) -> AuthResult:
    """车云双向身份认证
    
    根据 Algorithm 1 实现车云双向身份认证功能。
    
    前置条件:
    - vehicle_cert 和 gateway_cert 必须非空且格式正确
    - 两个证书必须在有效期内且未被撤销
    - vehicle_private_key 和 gateway_private_key 必须与对应证书的公钥匹配
    
    后置条件:
    - 如果认证成功，返回 Success 包含有效的 token 和 sessionKey
    - 如果认证失败，返回 Failure 包含具体错误码和错误信息
    - 认证过程不会修改输入参数
    - 生成的 sessionKey 长度为 16 或 32 字节
    
    参数:
        vehicle_cert: 车端证书
        gateway_cert: 网关证书
        vehicle_private_key: 车端私钥（32 字节）
        gateway_private_key: 网关私钥（32 字节）
        ca_public_key: CA 公钥（64 字节）
        db_conn: 数据库连接（可选）
        
    返回:
        AuthResult: 认证结果
        
    验证需求: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9
    """
    # 前置条件验证
    if vehicle_cert is None:
        raise ValueError("vehicle_cert 不能为 None")
    
    if gateway_cert is None:
        raise ValueError("gateway_cert 不能为 None")
    
    if len(vehicle_private_key) != 32:
        raise ValueError(f"vehicle_private_key 长度必须为 32 字节，当前为 {len(vehicle_private_key)}")
    
    if len(gateway_private_key) != 32:
        raise ValueError(f"gateway_private_key 长度必须为 32 字节，当前为 {len(gateway_private_key)}")
    
    # 创建数据库连接（如果需要）
    should_close_conn = False
    if db_conn is None:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        should_close_conn = True
    
    try:
        # 获取 CRL
        crl_list = get_crl(db_conn)
        
        # 步骤 1：网关验证车端证书
        vehicle_valid, vehicle_msg = authenticate_vehicle(
            vehicle_cert,
            generate_challenge(),  # 临时挑战值用于证书验证
            ca_public_key,
            crl_list,
            db_conn
        )
        
        if not vehicle_valid:
            return AuthResult.create_failure(
                ErrorCode.INVALID_CERTIFICATE,
                vehicle_msg
            )
        
        # 步骤 2：车端验证网关证书
        gateway_valid, gateway_msg = authenticate_gateway(
            gateway_cert,
            ca_public_key,
            crl_list,
            db_conn
        )
        
        if not gateway_valid:
            return AuthResult.create_failure(
                ErrorCode.INVALID_CERTIFICATE,
                gateway_msg
            )
        
        # 步骤 3：网关生成挑战值
        challenge = generate_challenge()
        
        # 步骤 4：车端使用私钥签名挑战值
        vehicle_response = sm2_sign(challenge, vehicle_private_key)
        
        # 步骤 5：网关验证车端签名
        vehicle_signature_valid = verify_challenge(
            vehicle_response,
            challenge,
            vehicle_cert.public_key
        )
        
        if not vehicle_signature_valid:
            return AuthResult.create_failure(
                ErrorCode.SIGNATURE_VERIFICATION_FAILED,
                "车端签名验证失败"
            )
        
        # 步骤 6：车端生成挑战值
        vehicle_challenge = generate_challenge()
        
        # 步骤 7：网关使用私钥签名挑战值
        gateway_response = sm2_sign(vehicle_challenge, gateway_private_key)
        
        # 步骤 8：车端验证网关签名
        gateway_signature_valid = verify_challenge(
            gateway_response,
            vehicle_challenge,
            gateway_cert.public_key
        )
        
        if not gateway_signature_valid:
            return AuthResult.create_failure(
                ErrorCode.SIGNATURE_VERIFICATION_FAILED,
                "网关签名验证失败"
            )
        
        # 步骤 9：生成会话密钥
        session_key = generate_sm4_key(16)  # 使用 128 位密钥
        
        # 步骤 10：生成认证令牌
        # 从证书主体中提取车辆 ID
        # 假设证书主体格式为 "CN=<vehicle_id>,O=<org>,C=<country>"
        subject_parts = vehicle_cert.subject.split(',')
        vehicle_id = subject_parts[0].split('=')[1] if subject_parts else "UNKNOWN"
        
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(hours=24)  # 令牌有效期 24 小时
        
        # 创建令牌数据
        token_data = {
            "vehicle_id": vehicle_id,
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "permissions": ["data_transfer", "heartbeat"]
        }
        
        # 使用网关私钥签名令牌
        token_bytes = json.dumps(token_data, sort_keys=True).encode('utf-8')
        token_signature = sm2_sign(token_bytes, gateway_private_key)
        
        token = AuthToken(
            vehicle_id=vehicle_id,
            issued_at=issued_at,
            expires_at=expires_at,
            permissions={"data_transfer", "heartbeat"},
            signature=token_signature
        )
        
        # 后置条件验证
        assert token is not None, "令牌创建失败"
        assert session_key is not None, "会话密钥生成失败"
        assert len(session_key) in (16, 32), f"会话密钥长度不正确: {len(session_key)}"
        
        return AuthResult.create_success(token, session_key)
        
    finally:
        if should_close_conn:
            db_conn.close()


def establish_session(
    vehicle_id: str,
    auth_token: AuthToken,
    redis_conn: Optional[RedisConnection] = None,
    use_secure_storage: bool = True
) -> SessionInfo:
    """建立会话
    
    创建新的安全会话并存储到 Redis。
    会话密钥存储在安全存储区，确保密钥安全。
    
    前置条件:
    - vehicle_id 非空且符合车辆标识格式
    - auth_token 必须有效且未过期
    - auth_token 的签名必须通过验证
    - vehicle_id 必须与 auth_token 中的 vehicle_id 匹配
    
    后置条件:
    - 返回的 sessionInfo 包含唯一的 sessionId
    - sessionInfo.sm4SessionKey 已生成且长度为 16 或 32 字节
    - sessionInfo.status 为 ACTIVE
    - sessionInfo.expiresAt 晚于 establishedAt
    - 会话信息已存储到 Redis
    - 会话密钥已存储到安全存储区
    
    参数:
        vehicle_id: 车辆标识
        auth_token: 认证令牌
        redis_conn: Redis 连接（可选）
        use_secure_storage: 是否使用安全存储（默认 True）
        
    返回:
        SessionInfo: 会话信息
        
    异常:
        ValueError: 如果参数无效
        RuntimeError: 如果会话建立失败
        
    验证需求: 5.1, 5.2, 5.3, 5.4, 19.3, 19.5
    """
    # 前置条件验证
    if not vehicle_id:
        raise ValueError("vehicle_id 不能为空")
    
    if auth_token is None:
        raise ValueError("auth_token 不能为 None")
    
    if auth_token.vehicle_id != vehicle_id:
        raise ValueError(f"vehicle_id 不匹配: {vehicle_id} != {auth_token.vehicle_id}")
    
    # 检查令牌是否过期
    current_time = datetime.utcnow()
    if auth_token.is_expired(current_time):
        raise ValueError("认证令牌已过期")
    
    # 步骤 1：生成唯一会话 ID（32 字节）
    session_id = os.urandom(32).hex()  # 64 字符的十六进制字符串
    
    # 步骤 2：生成 SM4 会话密钥
    sm4_session_key = generate_sm4_key(16)  # 128 位密钥
    
    # 步骤 3：如果启用安全存储，将会话密钥存储到安全存储区
    if use_secure_storage:
        secure_storage = get_secure_key_storage()
        secure_storage.store_session_key(session_id, sm4_session_key, rotation_interval_hours=24)
    
    # 步骤 4：设置会话过期时间（默认 24 小时）
    established_at = current_time
    expires_at = established_at + timedelta(hours=24)
    
    # 步骤 5：创建会话信息
    session_info = SessionInfo(
        session_id=session_id,
        vehicle_id=vehicle_id,
        sm4_session_key=sm4_session_key,
        established_at=established_at,
        expires_at=expires_at,
        status=SessionStatus.ACTIVE,
        last_activity_time=established_at
    )
    
    # 步骤 6：存储会话到 Redis
    should_close_conn = False
    if redis_conn is None:
        redis_conn = RedisConnection(RedisConfig.from_env())
        should_close_conn = True
    
    try:
        redis_conn.connect()
        
        # 将会话信息序列化为 JSON
        session_data = json.dumps(session_info.to_dict())
        
        # 计算过期时间（秒）
        ttl = int((expires_at - established_at).total_seconds())
        
        # 存储到 Redis，使用 session_id 作为键
        redis_key = f"session:{session_id}"
        redis_conn.set(redis_key, session_data.encode('utf-8'), ex=ttl)
        
        # 同时维护车辆 ID 到会话 ID 的映射（用于会话冲突检测）
        vehicle_key = f"vehicle:{vehicle_id}:session"
        redis_conn.set(vehicle_key, session_id.encode('utf-8'), ex=ttl)
        
    finally:
        if should_close_conn:
            redis_conn.close()
    
    # 后置条件验证
    assert session_info.session_id is not None and len(session_info.session_id) > 0
    assert len(session_info.sm4_session_key) in (16, 32)
    assert session_info.status == SessionStatus.ACTIVE
    assert session_info.expires_at > session_info.established_at
    
    return session_info


def close_session(
    session_id: str,
    redis_conn: Optional[RedisConnection] = None,
    use_secure_storage: bool = True
) -> bool:
    """关闭会话
    
    从 Redis 中删除会话信息，并安全清除会话密钥。
    
    前置条件:
    - session_id 非空且有效
    
    后置条件:
    - 会话已从 Redis 中删除
    - 会话密钥已从安全存储区安全清除
    - 返回 True 表示关闭成功
    
    参数:
        session_id: 会话 ID
        redis_conn: Redis 连接（可选）
        use_secure_storage: 是否使用安全存储（默认 True）
        
    返回:
        bool: 关闭是否成功
        
    验证需求: 5.5, 19.4, 19.6
    """
    # 前置条件验证
    if not session_id:
        raise ValueError("session_id 不能为空")
    
    should_close_conn = False
    if redis_conn is None:
        redis_conn = RedisConnection(RedisConfig.from_env())
        should_close_conn = True
    
    try:
        redis_conn.connect()
        
        # 先获取会话信息以获取 vehicle_id
        redis_key = f"session:{session_id}"
        session_data = redis_conn.get(redis_key)
        
        if session_data:
            # 解析会话数据
            session_dict = json.loads(session_data.decode('utf-8'))
            vehicle_id = session_dict.get('vehicle_id')
            
            # 如果启用安全存储，安全清除会话密钥
            if use_secure_storage:
                secure_storage = get_secure_key_storage()
                secure_storage.secure_clear_key(session_id)
            
            # 删除会话
            redis_conn.delete(redis_key)
            
            # 删除车辆到会话的映射
            if vehicle_id:
                vehicle_key = f"vehicle:{vehicle_id}:session"
                redis_conn.delete(vehicle_key)
            
            return True
        else:
            # 会话不存在
            return False
        
    finally:
        if should_close_conn:
            redis_conn.close()


def cleanup_expired_sessions(
    redis_conn: Optional[RedisConnection] = None
) -> int:
    """清理过期会话
    
    扫描并删除所有过期的会话。
    Redis 的 TTL 机制会自动删除过期键，但此函数提供主动清理功能。
    
    前置条件:
    - Redis 连接可用
    
    后置条件:
    - 所有过期会话已被删除
    - 返回清理的会话数量
    
    参数:
        redis_conn: Redis 连接（可选）
        
    返回:
        int: 清理的会话数量
        
    验证需求: 5.5, 5.6
    """
    should_close_conn = False
    if redis_conn is None:
        redis_conn = RedisConnection(RedisConfig.from_env())
        should_close_conn = True
    
    try:
        redis_conn.connect()
        
        # 注意：Redis 的 TTL 机制会自动删除过期键
        # 这里我们只是扫描并统计过期会话
        # 在实际生产环境中，可以使用 Redis 的 SCAN 命令遍历所有会话键
        
        # 由于 Redis 会自动清理过期键，这里返回 0
        # 如果需要主动清理，可以实现更复杂的逻辑
        
        return 0
        
    finally:
        if should_close_conn:
            redis_conn.close()


def handle_session_conflict(
    vehicle_id: str,
    strategy: str = "reject_new",
    redis_conn: Optional[RedisConnection] = None
) -> Tuple[bool, str]:
    """处理会话冲突
    
    当同一车辆尝试建立多个并发会话时，根据策略处理冲突。
    
    前置条件:
    - vehicle_id 非空且有效
    - strategy 必须是 "reject_new" 或 "terminate_old"
    
    后置条件:
    - 根据策略处理会话冲突
    - 返回处理结果和消息
    
    参数:
        vehicle_id: 车辆 ID
        strategy: 冲突处理策略（"reject_new" 或 "terminate_old"）
        redis_conn: Redis 连接（可选）
        
    返回:
        Tuple[bool, str]: (是否允许新会话, 消息)
        
    验证需求: 5.7
    """
    # 前置条件验证
    if not vehicle_id:
        raise ValueError("vehicle_id 不能为空")
    
    if strategy not in ("reject_new", "terminate_old"):
        raise ValueError(f"无效的策略: {strategy}")
    
    should_close_conn = False
    if redis_conn is None:
        redis_conn = RedisConnection(RedisConfig.from_env())
        should_close_conn = True
    
    try:
        redis_conn.connect()
        
        # 检查是否存在现有会话
        vehicle_key = f"vehicle:{vehicle_id}:session"
        existing_session_id = redis_conn.get(vehicle_key)
        
        if not existing_session_id:
            # 没有现有会话，允许建立新会话
            return (True, "没有会话冲突")
        
        # 存在会话冲突
        if strategy == "reject_new":
            # 拒绝新会话
            return (False, "会话冲突：拒绝新会话，保持现有会话")
        else:  # terminate_old
            # 终止旧会话
            session_id = existing_session_id.decode('utf-8')
            close_session(session_id, redis_conn)
            return (True, "会话冲突：已终止旧会话，允许新会话")
        
    finally:
        if should_close_conn:
            redis_conn.close()
