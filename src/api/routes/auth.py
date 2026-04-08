"""车辆认证 API

提供车辆认证和会话管理功能。
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import uuid

from src.db.redis_client import RedisConnection
from src.db.postgres import PostgreSQLConnection
from config.database import RedisConfig, PostgreSQLConfig
from src.audit_logger import AuditLogger
from src.models.enums import EventType
from src.api.main import verify_token

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """获取客户端真实IP地址
    
    优先级：
    1. X-Forwarded-For 头（代理/负载均衡器设置）
    2. X-Real-IP 头（Nginx等设置）
    3. 直接连接的客户端IP
    
    Args:
        request: FastAPI Request对象
        
    Returns:
        客户端IP地址字符串
    """
    # X-Forwarded-For 可能包含多个IP，取第一个（真实客户端IP）
    x_forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    
    # X-Real-IP 通常由Nginx等设置
    x_real_ip = request.headers.get("X-Real-IP", "").strip()
    if x_real_ip:
        return x_real_ip
    
    # 直接连接的客户端IP（可能是Pod IP或Service IP）
    if request.client:
        return request.client.host
    
    return "unknown"


class VehicleRegisterRequest(BaseModel):
    """车辆注册请求"""
    vehicle_id: str
    certificate_serial: Optional[str] = None
    public_key: Optional[str] = None  # 车辆 SM2 公钥（hex 格式）


class VehicleRegisterResponse(BaseModel):
    """车辆注册响应"""
    success: bool
    session_id: str
    session_key: str  # SM4 会话密钥（hex 格式）
    gateway_public_key: str  # 网关 SM2 公钥（hex 格式）
    message: str


@router.post("/register", response_model=VehicleRegisterResponse)
async def register_vehicle(
    request: VehicleRegisterRequest,
    http_request: Request,
    user: str = Depends(verify_token)
):
    """注册车辆为在线状态
    
    简化的车辆注册接口，用于测试环境。
    在生产环境中应该使用完整的双向认证流程。
    
    参数:
        request: 车辆注册请求
        
    返回:
        VehicleRegisterResponse: 注册响应
    """
    # 获取客户端真实IP地址
    client_ip = get_client_ip(http_request)
    
    try:
        from src.crypto.sm4 import generate_sm4_key
        from src.crypto.sm2 import generate_sm2_keypair
        
        redis_conn = RedisConnection(RedisConfig.from_env())
        redis_conn.connect()
        
        # 初始化审计日志记录器
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        audit_logger = AuditLogger(db_conn)
        
        # 初始化安全策略管理器
        from src.security_policy_manager import SecurityPolicyManager
        policy_manager = SecurityPolicyManager(db_conn)
        
        # 检查车辆是否被锁定
        if policy_manager.is_vehicle_locked(request.vehicle_id):
            db_conn.close()
            redis_conn.close()
            
            # 记录认证失败（被锁定）
            db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
            audit_logger = AuditLogger(db_conn)
            audit_logger.log_auth_event(
                vehicle_id=request.vehicle_id,
                event_type=EventType.AUTHENTICATION_FAILURE,
                result=False,
                ip_address=client_ip,
                details=f"车辆被锁定，拒绝注册"
            )
            db_conn.close()
            
            raise HTTPException(
                status_code=403,
                detail="车辆因多次认证失败被暂时锁定，请稍后再试"
            )
        
        # 获取会话超时配置
        session_timeout = policy_manager.get_session_timeout()
        
        # 生成会话 ID
        session_id = str(uuid.uuid4())
        
        # 生成 SM4 会话密钥（16 字节）
        session_key = generate_sm4_key(16)
        
        # 生成或获取网关密钥对
        gateway_privkey_key = "gateway:sm2:private_key"
        gateway_pubkey_key = "gateway:sm2:public_key"
        
        gateway_privkey_data = redis_conn.get(gateway_privkey_key)
        gateway_pubkey_data = redis_conn.get(gateway_pubkey_key)
        
        if gateway_privkey_data and gateway_pubkey_data:
            gateway_private_key = bytes.fromhex(gateway_privkey_data.decode('utf-8'))
            gateway_public_key = bytes.fromhex(gateway_pubkey_data.decode('utf-8'))
        else:
            # 生成新的网关密钥对
            gateway_private_key, gateway_public_key = generate_sm2_keypair()
            redis_conn.set(gateway_privkey_key, gateway_private_key.hex().encode('utf-8'), ex=86400)
            redis_conn.set(gateway_pubkey_key, gateway_public_key.hex().encode('utf-8'), ex=86400)
        
        # 保存车辆公钥（如果提供）
        if request.public_key:
            vehicle_pubkey_key = f"vehicle:{request.vehicle_id}:pubkey"
            redis_conn.set(vehicle_pubkey_key, request.public_key.encode('utf-8'), ex=86400)
        
        # 创建会话数据
        session_data = {
            "session_id": session_id,
            "vehicle_id": request.vehicle_id,
            "established_at": datetime.utcnow().isoformat(),
            "last_activity_time": datetime.utcnow().isoformat(),
            "ip_address": "unknown",
            "sm4_session_key": session_key.hex(),
            "certificate_serial": request.certificate_serial or "unknown"
        }
        
        # 保存会话到 Redis（使用配置的超时时间）
        session_key_str = f"session:{session_id}"
        redis_conn.set(session_key_str, json.dumps(session_data).encode('utf-8'), ex=session_timeout)
        
        # 保存车辆到会话的映射
        vehicle_key = f"vehicle:{request.vehicle_id}:session"
        redis_conn.set(vehicle_key, session_id.encode('utf-8'), ex=session_timeout)
        
        redis_conn.close()
        
        # 重置认证失败记录（认证成功）
        policy_manager.reset_auth_failures(request.vehicle_id)
        
        # 记录认证成功事件到审计日志
        audit_logger.log_auth_event(
            vehicle_id=request.vehicle_id,
            event_type=EventType.AUTHENTICATION_SUCCESS,
            result=True,
            ip_address=client_ip,
            details=f"车辆注册成功，会话ID: {session_id}，会话超时: {session_timeout}秒"
        )
        
        db_conn.close()
        
        return VehicleRegisterResponse(
            success=True,
            session_id=session_id,
            session_key=session_key.hex(),
            gateway_public_key=gateway_public_key.hex(),
            message=f"车辆 {request.vehicle_id} 注册成功，已建立加密会话"
        )
        
    except Exception as e:
        # 记录认证失败事件到审计日志
        try:
            db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
            audit_logger = AuditLogger(db_conn)
            
            # 记录认证失败
            from src.security_policy_manager import SecurityPolicyManager
            policy_manager = SecurityPolicyManager(db_conn)
            should_lock = policy_manager.record_auth_failure(request.vehicle_id)
            
            details = f"车辆注册失败: {str(e)}"
            if should_lock:
                details += " (已锁定)"
            
            audit_logger.log_auth_event(
                vehicle_id=request.vehicle_id,
                event_type=EventType.AUTHENTICATION_FAILURE,
                result=False,
                ip_address=client_ip,
                details=details
            )
            db_conn.close()
        except:
            pass  # 避免审计日志记录失败影响主流程
        
        raise HTTPException(
            status_code=500,
            detail=f"车辆注册失败: {str(e)}"
        )


@router.post("/heartbeat")
async def vehicle_heartbeat(
    vehicle_id: str,
    session_id: str,
    user: str = Depends(verify_token)
):
    """车辆心跳
    
    更新车辆的最后活动时间，保持在线状态。
    
    参数:
        vehicle_id: 车辆标识
        session_id: 会话 ID
        
    返回:
        dict: 心跳响应
    """
    try:
        redis_conn = RedisConnection(RedisConfig.from_env())
        redis_conn.connect()
        
        # 获取会话数据
        session_key = f"session:{session_id}"
        session_data = redis_conn.get(session_key)
        
        if not session_data:
            redis_conn.close()
            raise HTTPException(status_code=404, detail="会话不存在或已过期")
        
        # 更新最后活动时间
        session_dict = json.loads(session_data.decode('utf-8'))
        session_dict['last_activity_time'] = datetime.utcnow().isoformat()
        
        # 保存回 Redis（刷新过期时间）
        redis_conn.set(session_key, json.dumps(session_dict).encode('utf-8'), ex=1800)
        
        # 刷新车辆映射的过期时间
        vehicle_key = f"vehicle:{vehicle_id}:session"
        redis_conn.set(vehicle_key, session_id.encode('utf-8'), ex=1800)
        
        redis_conn.close()
        
        return {
            "success": True,
            "message": "心跳更新成功",
            "last_activity": session_dict['last_activity_time']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"心跳更新失败: {str(e)}"
        )


@router.post("/unregister")
async def unregister_vehicle(
    vehicle_id: str,
    session_id: str,
    user: str = Depends(verify_token)
):
    """注销车辆
    
    将车辆从在线列表中移除。
    
    参数:
        vehicle_id: 车辆标识
        session_id: 会话 ID
        
    返回:
        dict: 注销响应
    """
    try:
        redis_conn = RedisConnection(RedisConfig.from_env())
        redis_conn.connect()
        
        # 删除会话
        session_key = f"session:{session_id}"
        redis_conn.delete(session_key)
        
        # 删除车辆映射
        vehicle_key = f"vehicle:{vehicle_id}:session"
        redis_conn.delete(vehicle_key)
        
        redis_conn.close()
        
        return {
            "success": True,
            "message": f"车辆 {vehicle_id} 注销成功"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"车辆注销失败: {str(e)}"
        )


@router.post("/data/secure")
async def receive_secure_vehicle_data(
    vehicle_id: str,
    session_id: str,
    secure_msg_dict: dict,
    http_request: Request,
    user: str = Depends(verify_token)
):
    """接收加密的车辆数据（使用 SM4 解密和 SM2 验签）
    
    接收并验证加密的车辆传感器数据，然后保存到数据库。
    
    参数:
        vehicle_id: 车辆标识
        session_id: 会话 ID
        secure_msg_dict: 加密的安全报文（字典格式）
        
    返回:
        dict: 接收响应
    """
    # 获取客户端真实IP地址
    client_ip = get_client_ip(http_request)
    
    try:
        from src.db.postgres import PostgreSQLConnection
        from config.database import PostgreSQLConfig
        from src.models.message import SecureMessage, MessageHeader
        from src.secure_messaging import verify_and_decrypt_message
        from src.crypto.sm2 import generate_sm2_keypair
        
        # 验证会话是否有效
        redis_conn = RedisConnection(RedisConfig.from_env())
        redis_conn.connect()
        
        session_key_str = f"session:{session_id}"
        session_data = redis_conn.get(session_key_str)
        
        if not session_data:
            redis_conn.close()
            raise HTTPException(status_code=404, detail="会话不存在或已过期")
        
        # 更新最后活动时间（心跳）
        session_dict = json.loads(session_data.decode('utf-8'))
        session_dict['last_activity_time'] = datetime.utcnow().isoformat()
        redis_conn.set(session_key_str, json.dumps(session_dict).encode('utf-8'), ex=1800)
        
        # 获取会话密钥和车辆公钥
        session_key_hex = session_dict.get('sm4_session_key', '0' * 32)
        session_key = bytes.fromhex(session_key_hex)
        
        # 获取车辆公钥（从 Redis 或生成模拟公钥）
        vehicle_pubkey_key = f"vehicle:{vehicle_id}:pubkey"
        vehicle_pubkey_data = redis_conn.get(vehicle_pubkey_key)
        
        if vehicle_pubkey_data:
            vehicle_public_key = bytes.fromhex(vehicle_pubkey_data.decode('utf-8'))
        else:
            # 如果没有存储公钥，生成模拟公钥（测试用）
            _, vehicle_public_key = generate_sm2_keypair()
            redis_conn.set(vehicle_pubkey_key, vehicle_public_key.hex().encode('utf-8'), ex=86400)
        
        redis_conn.close()
        
        # 重构 SecureMessage 对象
        try:
            header = MessageHeader.from_dict(secure_msg_dict['header'])
            secure_msg = SecureMessage(
                header=header,
                encrypted_payload=bytes.fromhex(secure_msg_dict['encrypted_payload']),
                signature=bytes.fromhex(secure_msg_dict['signature']),
                timestamp=datetime.fromisoformat(secure_msg_dict['timestamp']),
                nonce=bytes.fromhex(secure_msg_dict['nonce'])
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"安全报文格式错误: {str(e)}"
            )
        
        # 验证并解密数据
        try:
            plain_data = verify_and_decrypt_message(
                secure_message=secure_msg,
                session_key=session_key,
                sender_public_key=vehicle_public_key,
                redis_config=RedisConfig.from_env()
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"数据验证失败: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"数据解密失败: {str(e)}"
            )
        
        # 解析解密后的 JSON 数据
        try:
            data = json.loads(plain_data.decode('utf-8'))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"数据格式错误: {str(e)}"
            )
        
        # 保存车辆数据到数据库
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        query = """
            INSERT INTO vehicle_data (
                vehicle_id, timestamp, state,
                gps_latitude, gps_longitude, gps_altitude, gps_heading, gps_satellites,
                motion_speed, motion_acceleration, motion_odometer, motion_trip_distance,
                fuel_level, fuel_consumption, fuel_range,
                temp_engine, temp_cabin, temp_outside,
                battery_voltage, battery_current,
                diag_engine_load, diag_rpm, diag_throttle_position,
                raw_data
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s
            )
            ON CONFLICT (vehicle_id, timestamp) DO UPDATE SET
                received_at = CURRENT_TIMESTAMP,
                raw_data = EXCLUDED.raw_data
        """
        
        params = (
            vehicle_id,
            data.get('timestamp'),
            data.get('state'),
            data.get('gps', {}).get('latitude'),
            data.get('gps', {}).get('longitude'),
            data.get('gps', {}).get('altitude'),
            data.get('gps', {}).get('heading'),
            data.get('gps', {}).get('satellites'),
            data.get('motion', {}).get('speed'),
            data.get('motion', {}).get('acceleration'),
            data.get('motion', {}).get('odometer'),
            data.get('motion', {}).get('trip_distance'),
            data.get('fuel', {}).get('level'),
            data.get('fuel', {}).get('consumption'),
            data.get('fuel', {}).get('range'),
            data.get('temperature', {}).get('engine'),
            data.get('temperature', {}).get('cabin'),
            data.get('temperature', {}).get('outside'),
            data.get('battery', {}).get('voltage'),
            data.get('battery', {}).get('current'),
            data.get('diagnostics', {}).get('engine_load'),
            data.get('diagnostics', {}).get('rpm'),
            data.get('diagnostics', {}).get('throttle_position'),
            json.dumps(data)
        )
        
        db_conn.execute_update(query, params)
        
        # 记录数据传输事件到审计日志
        audit_logger = AuditLogger(db_conn)
        data_size = len(json.dumps(data).encode('utf-8'))
        audit_logger.log_data_transfer(
            vehicle_id=vehicle_id,
            data_size=data_size,
            encrypted=True,
            ip_address=client_ip,
            details=f"接收加密车辆数据成功，数据大小: {data_size} 字节"
        )
        
        db_conn.close()
        
        return {
            "success": True,
            "message": "加密车辆数据接收成功",
            "vehicle_id": vehicle_id,
            "timestamp": data.get('timestamp'),
            "encryption": "SM4",
            "signature": "SM2-verified"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # 记录数据传输失败事件到审计日志
        try:
            db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
            audit_logger = AuditLogger(db_conn)
            audit_logger.log_data_transfer(
                vehicle_id=vehicle_id,
                data_size=0,
                encrypted=True,
                ip_address=client_ip,
                details=f"接收加密车辆数据失败: {str(e)}"
            )
            db_conn.close()
        except:
            pass  # 避免审计日志记录失败影响主流程
        
        raise HTTPException(
            status_code=500,
            detail=f"接收加密车辆数据失败: {str(e)}"
        )


@router.post("/data")
async def receive_vehicle_data(
    vehicle_id: str,
    session_id: str,
    data: dict,
    http_request: Request,
    user: str = Depends(verify_token)
):
    """接收车辆数据
    
    接收并保存车辆传感器数据到数据库。
    
    参数:
        vehicle_id: 车辆标识
        session_id: 会话 ID
        data: 车辆数据（JSON 格式）
        
    返回:
        dict: 接收响应
    """
    # 获取客户端真实IP地址
    client_ip = get_client_ip(http_request)
    
    try:
        from src.db.postgres import PostgreSQLConnection
        from config.database import PostgreSQLConfig
        
        # 验证会话是否有效
        redis_conn = RedisConnection(RedisConfig.from_env())
        redis_conn.connect()
        
        session_key = f"session:{session_id}"
        session_data = redis_conn.get(session_key)
        
        if not session_data:
            redis_conn.close()
            raise HTTPException(status_code=404, detail="会话不存在或已过期")
        
        # 更新最后活动时间（心跳）
        session_dict = json.loads(session_data.decode('utf-8'))
        session_dict['last_activity_time'] = datetime.utcnow().isoformat()
        redis_conn.set(session_key, json.dumps(session_dict).encode('utf-8'), ex=1800)
        redis_conn.close()
        
        # 保存车辆数据到数据库
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        query = """
            INSERT INTO vehicle_data (
                vehicle_id, timestamp, state,
                gps_latitude, gps_longitude, gps_altitude, gps_heading, gps_satellites,
                motion_speed, motion_acceleration, motion_odometer, motion_trip_distance,
                fuel_level, fuel_consumption, fuel_range,
                temp_engine, temp_cabin, temp_outside,
                battery_voltage, battery_current,
                diag_engine_load, diag_rpm, diag_throttle_position,
                raw_data
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s
            )
            ON CONFLICT (vehicle_id, timestamp) DO UPDATE SET
                received_at = CURRENT_TIMESTAMP,
                raw_data = EXCLUDED.raw_data
        """
        
        params = (
            vehicle_id,
            data.get('timestamp'),
            data.get('state'),
            data.get('gps', {}).get('latitude'),
            data.get('gps', {}).get('longitude'),
            data.get('gps', {}).get('altitude'),
            data.get('gps', {}).get('heading'),
            data.get('gps', {}).get('satellites'),
            data.get('motion', {}).get('speed'),
            data.get('motion', {}).get('acceleration'),
            data.get('motion', {}).get('odometer'),
            data.get('motion', {}).get('trip_distance'),
            data.get('fuel', {}).get('level'),
            data.get('fuel', {}).get('consumption'),
            data.get('fuel', {}).get('range'),
            data.get('temperature', {}).get('engine'),
            data.get('temperature', {}).get('cabin'),
            data.get('temperature', {}).get('outside'),
            data.get('battery', {}).get('voltage'),
            data.get('battery', {}).get('current'),
            data.get('diagnostics', {}).get('engine_load'),
            data.get('diagnostics', {}).get('rpm'),
            data.get('diagnostics', {}).get('throttle_position'),
            json.dumps(data)
        )
        
        db_conn.execute_update(query, params)
        
        # 记录数据传输事件到审计日志
        audit_logger = AuditLogger(db_conn)
        data_size = len(json.dumps(data).encode('utf-8'))
        audit_logger.log_data_transfer(
            vehicle_id=vehicle_id,
            data_size=data_size,
            encrypted=False,
            ip_address=client_ip,
            details=f"接收车辆数据成功（未加密），数据大小: {data_size} 字节"
        )
        
        db_conn.close()
        
        return {
            "success": True,
            "message": "车辆数据接收成功",
            "vehicle_id": vehicle_id,
            "timestamp": data.get('timestamp')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # 记录数据传输失败事件到审计日志
        try:
            db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
            audit_logger = AuditLogger(db_conn)
            audit_logger.log_data_transfer(
                vehicle_id=vehicle_id,
                data_size=0,
                encrypted=False,
                ip_address=client_ip,
                details=f"接收车辆数据失败: {str(e)}"
            )
            db_conn.close()
        except:
            pass  # 避免审计日志记录失败影响主流程
        
        raise HTTPException(
            status_code=500,
            detail=f"接收车辆数据失败: {str(e)}"
        )
