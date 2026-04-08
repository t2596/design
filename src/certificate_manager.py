"""证书管理模块

提供证书颁发、验证和撤销功能。
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional
from src.models.certificate import Certificate, SubjectInfo, CertificateExtensions
from src.models.audit import AuditLog
from src.models.enums import EventType, ValidationResult
from src.crypto.sm2 import sm2_sign
from src.db.postgres import PostgreSQLConnection
from config.database import PostgreSQLConfig
from src.certificate_cache import get_certificate_cache
from src.secure_key_storage import get_secure_key_storage


# CA 识别名称常量
CA_DISTINGUISHED_NAME = "CN=Vehicle IoT Security Gateway CA,O=Security Gateway,C=CN"


def generate_unique_serial_number() -> str:
    """生成唯一的证书序列号
    
    使用 UUID4 生成唯一序列号，确保全局唯一性。
    
    返回:
        str: 64 字符的十六进制序列号
    """
    # 使用 UUID4 生成随机唯一标识符
    # 转换为十六进制字符串并移除连字符
    serial = uuid.uuid4().hex + uuid.uuid4().hex
    return serial[:64]  # 确保长度为 64 字符


def create_distinguished_name(subject_info: SubjectInfo) -> str:
    """创建证书主体识别名称
    
    参数:
        subject_info: 证书主体信息
        
    返回:
        str: 格式化的识别名称
    """
    return f"CN={subject_info.vehicle_id},O={subject_info.organization},C={subject_info.country}"


def create_certificate_extensions(subject_info: SubjectInfo) -> CertificateExtensions:
    """创建证书扩展信息
    
    参数:
        subject_info: 证书主体信息
        
    返回:
        CertificateExtensions: 证书扩展对象
    """
    return CertificateExtensions(
        key_usage="digitalSignature,keyEncipherment",
        extended_key_usage="clientAuth,serverAuth"
    )


def encode_tbs_certificate(certificate: Certificate) -> bytes:
    """编码待签名证书（TBS Certificate）
    
    将证书的关键字段编码为字节序列，用于签名。
    
    参数:
        certificate: 证书对象（不含签名）
        
    返回:
        bytes: 编码后的待签名数据
    """
    # 构造待签名的证书数据结构
    tbs_data = {
        "version": certificate.version,
        "serial_number": certificate.serial_number,
        "issuer": certificate.issuer,
        "subject": certificate.subject,
        "valid_from": certificate.valid_from.isoformat(),
        "valid_to": certificate.valid_to.isoformat(),
        "public_key": certificate.public_key.hex(),
        "signature_algorithm": certificate.signature_algorithm,
        "extensions": certificate.extensions.to_dict()
    }
    
    # 将字典转换为 JSON 字符串，然后编码为字节
    # 使用 sort_keys 确保字段顺序一致
    json_str = json.dumps(tbs_data, sort_keys=True)
    return json_str.encode('utf-8')


def store_certificate(certificate: Certificate, db_conn: PostgreSQLConnection) -> None:
    """存储证书到 PostgreSQL 数据库
    
    参数:
        certificate: 证书对象
        db_conn: 数据库连接
    """
    query = """
        INSERT INTO certificates (
            serial_number, version, issuer, subject,
            valid_from, valid_to, public_key, signature,
            signature_algorithm, extensions
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    params = (
        certificate.serial_number,
        certificate.version,
        certificate.issuer,
        certificate.subject,
        certificate.valid_from,
        certificate.valid_to,
        certificate.public_key,
        certificate.signature,
        certificate.signature_algorithm,
        json.dumps(certificate.extensions.to_dict())
    )
    
    db_conn.execute_update(query, params)


def log_certificate_operation(
    operation: EventType,
    serial_number: str,
    db_conn: PostgreSQLConnection
) -> None:
    """记录证书操作到审计日志
    
    参数:
        operation: 操作类型（CERTIFICATE_ISSUED 或 CERTIFICATE_REVOKED）
        serial_number: 证书序列号
        db_conn: 数据库连接
    """
    log_id = uuid.uuid4().hex
    timestamp = datetime.utcnow()
    
    audit_log = AuditLog(
        log_id=log_id,
        timestamp=timestamp,
        event_type=operation,
        vehicle_id="CA",  # CA 操作使用 "CA" 作为 vehicle_id
        operation_result=True,
        details=f"Certificate operation: {operation.value}, Serial: {serial_number}",
        ip_address="127.0.0.1"  # CA 本地操作
    )
    
    query = """
        INSERT INTO audit_logs (
            log_id, timestamp, event_type, vehicle_id,
            operation_result, details, ip_address
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    params = (
        audit_log.log_id,
        audit_log.timestamp,
        audit_log.event_type.value,
        audit_log.vehicle_id,
        audit_log.operation_result,
        audit_log.details,
        audit_log.ip_address
    )
    
    db_conn.execute_update(query, params)


def is_valid_certificate_format(certificate: Certificate) -> bool:
    """检查证书格式是否有效
    
    参数:
        certificate: 待检查的证书
        
    返回:
        bool: 格式是否有效
    """
    try:
        # 检查必需字段是否存在且非空
        if not certificate.serial_number:
            return False
        if not certificate.issuer:
            return False
        if not certificate.subject:
            return False
        if not certificate.public_key or len(certificate.public_key) != 64:
            return False
        if not certificate.signature or len(certificate.signature) != 64:
            return False
        if certificate.signature_algorithm != "SM2":
            return False
        if not isinstance(certificate.valid_from, datetime):
            return False
        if not isinstance(certificate.valid_to, datetime):
            return False
        if certificate.valid_from >= certificate.valid_to:
            return False
        
        return True
    except Exception:
        return False


def verify_certificate(
    certificate: Certificate,
    ca_public_key: bytes,
    crl_list: list,
    db_conn: Optional[PostgreSQLConnection] = None,
    use_cache: bool = True
) -> tuple[ValidationResult, str]:
    """验证证书
    
    根据 Algorithm 5 实现证书验证功能。
    使用 LRU 缓存提高验证性能（缓存大小：10,000，TTL：5 分钟）。
    
    前置条件:
    - certificate 必须非空且格式正确
    - ca_public_key 必须是有效的 CA 公钥
    - crl_list 必须是最新的证书撤销列表
    
    后置条件:
    - 返回的 ValidationResult 包含明确的验证状态
    - 如果验证失败，包含具体的失败原因
    - 证书对象未被修改
    - 验证过程无副作用
    
    参数:
        certificate: 待验证证书
        ca_public_key: CA 公钥（64 字节）
        crl_list: 证书撤销列表（序列号列表）
        db_conn: 数据库连接（可选）
        use_cache: 是否使用缓存（默认 True）
        
    返回:
        tuple[ValidationResult, str]: (验证结果, 消息)
        
    异常:
        ValueError: 如果输入参数无效
        
    验证需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 18.1, 18.2
    """
    # 前置条件验证
    if certificate is None:
        raise ValueError("certificate 不能为 None")
    
    if ca_public_key is None:
        raise ValueError("ca_public_key 不能为 None")
    
    if len(ca_public_key) != 64:
        raise ValueError(f"ca_public_key 长度必须为 64 字节，当前为 {len(ca_public_key)}")
    
    if crl_list is None:
        raise ValueError("crl_list 不能为 None")
    
    # 尝试从缓存获取验证结果
    if use_cache:
        cache = get_certificate_cache()
        cached_result = cache.get(certificate.serial_number)
        if cached_result is not None:
            # 缓存命中，直接返回缓存的结果
            return cached_result
    
    # 缓存未命中，执行完整的验证流程
    
    # 步骤 1：检查证书格式
    if not is_valid_certificate_format(certificate):
        result = (ValidationResult.INVALID, "证书格式错误")
        # 不缓存格式错误的结果
        return result
    
    # 步骤 2：检查证书有效期
    current_time = datetime.utcnow()
    
    if current_time < certificate.valid_from:
        result = (ValidationResult.INVALID, "证书尚未生效")
        # 不缓存未生效的证书（可能很快就会生效）
        return result
    
    if current_time > certificate.valid_to:
        result = (ValidationResult.INVALID, "证书已过期")
        # 缓存过期结果（过期状态不会改变）
        if use_cache:
            cache.put(certificate.serial_number, result[0], result[1])
        return result
    
    # 步骤 3：检查证书是否被撤销
    # 循环不变式：所有已检查的撤销证书序列号都不匹配
    for revoked_serial in crl_list:
        if revoked_serial == certificate.serial_number:
            result = (ValidationResult.REVOKED, "证书已被撤销")
            # 缓存撤销结果（撤销状态不会改变）
            if use_cache:
                cache.put(certificate.serial_number, result[0], result[1])
            return result
    
    # 步骤 4：验证证书签名
    tbs_certificate = encode_tbs_certificate(certificate)
    
    from src.crypto.sm2 import sm2_verify
    signature_valid = sm2_verify(tbs_certificate, certificate.signature, ca_public_key)
    
    if not signature_valid:
        result = (ValidationResult.INVALID, "证书签名验证失败")
        # 缓存签名验证失败结果（签名不会改变）
        if use_cache:
            cache.put(certificate.serial_number, result[0], result[1])
        return result
    
    # 步骤 5：验证证书链（如果需要）
    # 注：当前实现假设单层证书链（直接由 CA 签发）
    # 如果需要多层证书链验证，可以在此处扩展
    if certificate.issuer != CA_DISTINGUISHED_NAME:
        # 对于非 CA 直接签发的证书，需要验证证书链
        # 这里简化处理，返回无效
        result = (ValidationResult.INVALID, "证书链验证失败")
        # 缓存证书链验证失败结果
        if use_cache:
            cache.put(certificate.serial_number, result[0], result[1])
        return result
    
    # 后置条件验证
    # 验证通过
    result = (ValidationResult.VALID, "证书验证通过")
    
    # 缓存验证通过的结果（TTL = 5 分钟）
    if use_cache:
        cache.put(certificate.serial_number, result[0], result[1])
    
    return result


def revoke_certificate(
    serial_number: str,
    reason: Optional[str] = None,
    db_conn: Optional[PostgreSQLConnection] = None
) -> bool:
    """撤销证书
    
    将证书序列号添加到证书撤销列表（CRL）。
    撤销后会自动使缓存失效。
    
    前置条件:
    - serial_number 必须非空且有效
    - 证书必须存在于数据库中
    
    后置条件:
    - 证书序列号已添加到 CRL
    - 审计日志已记录撤销操作
    - 缓存已失效
    - 返回 True 表示撤销成功
    
    参数:
        serial_number: 要撤销的证书序列号
        reason: 撤销原因（可选）
        db_conn: 数据库连接（可选，如果为 None 则创建新连接）
        
    返回:
        bool: 撤销是否成功
        
    异常:
        ValueError: 如果 serial_number 无效
        RuntimeError: 如果证书不存在或撤销失败
        
    验证需求: 3.1, 3.2
    """
    # 前置条件验证
    if not serial_number:
        raise ValueError("serial_number 不能为空")
    
    if len(serial_number) > 64:
        raise ValueError(f"serial_number 长度不能超过 64 字符，当前为 {len(serial_number)}")
    
    # 创建数据库连接（如果需要）
    should_close_conn = False
    if db_conn is None:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        should_close_conn = True
    
    try:
        # 步骤 1：检查证书是否存在
        check_query = "SELECT serial_number FROM certificates WHERE serial_number = %s"
        result = db_conn.execute_query(check_query, (serial_number,))
        
        if not result:
            raise RuntimeError(f"证书不存在: {serial_number}")
        
        # 步骤 2：检查证书是否已被撤销
        check_crl_query = "SELECT serial_number FROM certificate_revocation_list WHERE serial_number = %s"
        crl_result = db_conn.execute_query(check_crl_query, (serial_number,))
        
        if crl_result:
            # 证书已在 CRL 中，无需重复撤销
            return True
        
        # 步骤 3：将证书序列号添加到 CRL
        revoke_query = """
            INSERT INTO certificate_revocation_list (serial_number, reason)
            VALUES (%s, %s)
        """
        
        revoke_params = (serial_number, reason if reason else "未指定原因")
        db_conn.execute_update(revoke_query, revoke_params)
        
        # 步骤 4：记录审计日志
        log_certificate_operation(
            EventType.CERTIFICATE_REVOKED,
            serial_number,
            db_conn
        )
        
        # 步骤 5：使缓存失效
        cache = get_certificate_cache()
        cache.invalidate(serial_number)
        
        # 后置条件验证
        # 验证证书已添加到 CRL
        verify_query = "SELECT serial_number FROM certificate_revocation_list WHERE serial_number = %s"
        verify_result = db_conn.execute_query(verify_query, (serial_number,))
        
        if not verify_result:
            raise RuntimeError("证书撤销失败：未能添加到 CRL")
        
        return True
        
    finally:
        if should_close_conn:
            db_conn.close()


def get_crl(db_conn: Optional[PostgreSQLConnection] = None) -> list:
    """获取证书撤销列表（CRL）
    
    从数据库中检索当前的证书撤销列表。
    
    前置条件:
    - 数据库连接可用
    
    后置条件:
    - 返回包含所有已撤销证书序列号的列表
    - 列表可能为空（如果没有撤销的证书）
    
    参数:
        db_conn: 数据库连接（可选，如果为 None 则创建新连接）
        
    返回:
        list: 已撤销证书的序列号列表
        
    验证需求: 3.3, 3.4
    """
    # 创建数据库连接（如果需要）
    should_close_conn = False
    if db_conn is None:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        should_close_conn = True
    
    try:
        # 查询所有已撤销的证书序列号
        query = "SELECT serial_number FROM certificate_revocation_list"
        result = db_conn.execute_query(query, ())
        
        # 提取序列号列表（result 是字典列表）
        crl_list = [row['serial_number'] for row in result]
        
        return crl_list
        
    finally:
        if should_close_conn:
            db_conn.close()


def get_certificate_chain(cert: Certificate, db_conn: Optional[PostgreSQLConnection] = None) -> list:
    """获取证书链
    
    检索从给定证书到根 CA 的完整证书链。
    当前实现假设单层证书链（证书直接由 CA 签发）。
    
    前置条件:
    - cert 必须非空且格式正确
    - 数据库连接可用
    
    后置条件:
    - 返回证书链列表，从叶证书到根证书
    - 对于单层证书链，返回 [cert]
    
    参数:
        cert: 证书对象
        db_conn: 数据库连接（可选，如果为 None 则创建新连接）
        
    返回:
        list: 证书链列表
        
    异常:
        ValueError: 如果 cert 无效
        
    验证需求: 3.3, 3.4
    """
    # 前置条件验证
    if cert is None:
        raise ValueError("cert 不能为 None")
    
    if not cert.serial_number:
        raise ValueError("证书序列号不能为空")
    
    # 当前实现：单层证书链
    # 如果证书由 CA 直接签发，证书链只包含该证书本身
    if cert.issuer == CA_DISTINGUISHED_NAME:
        return [cert]
    
    # 对于多层证书链的扩展点：
    # 1. 从数据库查询颁发者证书
    # 2. 递归构建证书链
    # 3. 验证每个证书的签名
    
    # 当前简化实现：返回单个证书
    return [cert]


def check_certificate_expiry(cert: Certificate) -> dict:
    """检查证书过期状态
    
    检查证书的有效期状态，返回详细的过期信息。
    
    前置条件:
    - cert 必须非空且格式正确
    - cert.valid_from 和 cert.valid_to 必须是有效的时间戳
    
    后置条件:
    - 返回包含过期状态和详细信息的字典
    - 不修改证书对象
    
    参数:
        cert: 证书对象
        
    返回:
        dict: 包含以下字段的字典
            - status: str - "valid", "expired", "not_yet_valid"
            - valid_from: datetime - 证书生效时间
            - valid_to: datetime - 证书过期时间
            - current_time: datetime - 当前时间
            - days_until_expiry: int - 距离过期的天数（负数表示已过期）
            - message: str - 状态描述信息
            
    异常:
        ValueError: 如果 cert 无效
        
    验证需求: 3.3, 3.4
    """
    # 前置条件验证
    if cert is None:
        raise ValueError("cert 不能为 None")
    
    if not isinstance(cert.valid_from, datetime):
        raise ValueError("cert.valid_from 必须是 datetime 对象")
    
    if not isinstance(cert.valid_to, datetime):
        raise ValueError("cert.valid_to 必须是 datetime 对象")
    
    if cert.valid_from >= cert.valid_to:
        raise ValueError("cert.valid_from 必须早于 cert.valid_to")
    
    # 获取当前时间
    current_time = datetime.utcnow()
    
    # 计算距离过期的天数
    days_until_expiry = (cert.valid_to - current_time).days
    
    # 确定证书状态
    if current_time < cert.valid_from:
        status = "not_yet_valid"
        message = f"证书尚未生效，将在 {cert.valid_from.isoformat()} 生效"
    elif current_time > cert.valid_to:
        status = "expired"
        days_expired = (current_time - cert.valid_to).days
        message = f"证书已过期 {days_expired} 天"
    else:
        status = "valid"
        if days_until_expiry <= 30:
            message = f"证书有效，但将在 {days_until_expiry} 天后过期"
        else:
            message = f"证书有效，还有 {days_until_expiry} 天过期"
    
    # 构造返回结果
    result = {
        "status": status,
        "valid_from": cert.valid_from,
        "valid_to": cert.valid_to,
        "current_time": current_time,
        "days_until_expiry": days_until_expiry,
        "message": message
    }
    
    return result


def issue_certificate(
    subject_info: SubjectInfo,
    public_key: bytes,
    ca_private_key: bytes,
    ca_public_key: bytes,
    db_conn: Optional[PostgreSQLConnection] = None,
    use_secure_storage: bool = True,
    validity_days: int = 365
) -> Certificate:
    """颁发证书
    
    根据 Algorithm 4 实现证书颁发功能。
    
    前置条件:
    - subject_info 必须包含有效的车辆标识信息
    - public_key 必须是有效的 SM2 公钥（64 字节）
    - ca_private_key 必须是 CA 的有效私钥（32 字节）
    - CA 证书必须在有效期内
    
    后置条件:
    - 返回的证书包含有效的签名
    - 证书序列号在系统中唯一
    - 证书有效期设置正确（validFrom < validTo）
    - 证书签名可通过 CA 公钥验证
    - 证书已存储到数据库
    - 审计日志已记录
    
    参数:
        subject_info: 证书主体信息
        public_key: 申请者的 SM2 公钥（64 字节）
        ca_private_key: CA 私钥（32 字节）
        ca_public_key: CA 公钥（64 字节，用于验证）
        db_conn: 数据库连接（可选，如果为 None 则创建新连接）
        use_secure_storage: 是否使用安全存储（默认 True）
        validity_days: 证书有效期（天数，默认 365 天）
        
    返回:
        Certificate: 签发的证书
        
    异常:
        ValueError: 如果输入参数无效
        RuntimeError: 如果证书颁发失败
        
    验证需求: 1.1, 1.2, 1.3, 1.4, 1.5, 19.1, 19.6
    """
    # 前置条件验证
    if subject_info is None:
        raise ValueError("subject_info 不能为 None")
    
    if not subject_info.vehicle_id:
        raise ValueError("vehicle_id 不能为空")
    
    if public_key is None:
        raise ValueError("public_key 不能为 None")
    
    if len(public_key) != 64:
        raise ValueError(f"public_key 长度必须为 64 字节，当前为 {len(public_key)}")
    
    if ca_private_key is None:
        raise ValueError("ca_private_key 不能为 None")
    
    if len(ca_private_key) != 32:
        raise ValueError(f"ca_private_key 长度必须为 32 字节，当前为 {len(ca_private_key)}")
    
    # 如果启用安全存储，将 CA 私钥存储到安全存储区
    if use_secure_storage:
        secure_storage = get_secure_key_storage()
        ca_key_id = "ca_private_key"
        
        # 检查是否已存储
        existing_key = secure_storage.retrieve_key(ca_key_id)
        if existing_key is None:
            # 首次存储 CA 私钥
            secure_storage.store_ca_private_key(ca_key_id, ca_private_key, rotation_interval_hours=24)
    
    # 步骤 1：生成唯一序列号
    serial_number = generate_unique_serial_number()
    
    # 步骤 2：设置证书有效期（使用配置的天数）
    valid_from = datetime.utcnow()
    valid_to = valid_from + timedelta(days=validity_days)
    
    # 步骤 3：构造证书主体
    certificate = Certificate(
        version=3,
        serial_number=serial_number,
        issuer=CA_DISTINGUISHED_NAME,
        subject=create_distinguished_name(subject_info),
        valid_from=valid_from,
        valid_to=valid_to,
        public_key=public_key,
        signature=b'',  # 签名稍后填充
        signature_algorithm="SM2",
        extensions=create_certificate_extensions(subject_info)
    )
    
    # 步骤 4：构造待签名数据（TBS Certificate）
    tbs_certificate = encode_tbs_certificate(certificate)
    
    # 步骤 5：使用 CA 私钥签名
    try:
        signature = sm2_sign(tbs_certificate, ca_private_key)
    except Exception as e:
        raise RuntimeError(f"证书签名失败: {str(e)}")
    
    # 步骤 6：将签名附加到证书
    certificate.signature = signature
    
    # 步骤 7：存储证书到数据库
    should_close_conn = False
    if db_conn is None:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        should_close_conn = True
    
    try:
        store_certificate(certificate, db_conn)
        
        # 步骤 8：记录审计日志
        log_certificate_operation(EventType.CERTIFICATE_ISSUED, serial_number, db_conn)
    finally:
        if should_close_conn:
            db_conn.close()
    
    # 后置条件验证
    assert certificate.signature is not None and len(certificate.signature) > 0, \
        "证书签名不能为空"
    assert len(certificate.serial_number) > 0, \
        "证书序列号不能为空"
    assert certificate.valid_from < certificate.valid_to, \
        "证书 validFrom 必须早于 validTo"
    
    # 验证签名（使用 CA 公钥）
    from src.crypto.sm2 import sm2_verify
    signature_valid = sm2_verify(tbs_certificate, certificate.signature, ca_public_key)
    assert signature_valid, "证书签名验证失败"
    
    return certificate
