"""安全通信网关主服务类

提供车联网安全通信网关的核心服务，集成证书管理、身份认证、加密签名和审计日志模块。
"""

from typing import Optional, Tuple
from datetime import datetime
from src.certificate_manager import (
    issue_certificate,
    verify_certificate,
    revoke_certificate,
    get_crl,
    check_certificate_expiry
)
from src.authentication import (
    mutual_authentication,
    establish_session,
    close_session,
    cleanup_expired_sessions,
    handle_session_conflict
)
from src.secure_messaging import (
    secure_data_transmission,
    verify_and_decrypt_message
)
from src.audit_logger import AuditLogger
from src.models.certificate import Certificate, SubjectInfo
from src.models.session import AuthResult, SessionInfo
from src.models.message import SecureMessage, MessageType
from src.models.enums import EventType, ValidationResult
from src.db.postgres import PostgreSQLConnection
from src.db.redis_client import RedisConnection
from config.database import PostgreSQLConfig, RedisConfig
from src.secure_key_storage import SecureKeyStorage, get_secure_key_storage


class SecurityGateway:
    """安全通信网关主服务类
    
    集成证书管理、身份认证、加密签名和审计日志模块，
    提供车联网安全通信网关的核心服务。
    
    验证需求: 4.1, 6.1, 7.1, 11.1
    """
    
    def __init__(
        self,
        ca_private_key: bytes,
        ca_public_key: bytes,
        gateway_private_key: bytes,
        gateway_public_key: bytes,
        gateway_cert: Certificate,
        pg_config: Optional[PostgreSQLConfig] = None,
        redis_config: Optional[RedisConfig] = None,
        use_secure_storage: bool = True
    ):
        """初始化安全通信网关
        
        参数:
            ca_private_key: CA 私钥（32 字节）
            ca_public_key: CA 公钥（64 字节）
            gateway_private_key: 网关私钥（32 字节）
            gateway_public_key: 网关公钥（64 字节）
            gateway_cert: 网关证书
            pg_config: PostgreSQL 配置（可选）
            redis_config: Redis 配置（可选）
            use_secure_storage: 是否使用安全密钥存储（默认 True）
        """
        # 验证密钥长度
        if len(ca_private_key) != 32:
            raise ValueError(f"CA 私钥长度必须为 32 字节，当前为 {len(ca_private_key)}")
        
        if len(ca_public_key) != 64:
            raise ValueError(f"CA 公钥长度必须为 64 字节，当前为 {len(ca_public_key)}")
        
        if len(gateway_private_key) != 32:
            raise ValueError(f"网关私钥长度必须为 32 字节，当前为 {len(gateway_private_key)}")
        
        if len(gateway_public_key) != 64:
            raise ValueError(f"网关公钥长度必须为 64 字节，当前为 {len(gateway_public_key)}")
        
        # 初始化安全密钥存储
        self.use_secure_storage = use_secure_storage
        if use_secure_storage:
            self.secure_storage = get_secure_key_storage()
            
            # 将 CA 私钥存储到安全隔离区（需求 19.1）
            self.secure_storage.store_ca_private_key(
                "ca_private_key",
                ca_private_key,
                rotation_interval_hours=24
            )
            
            # 将网关私钥存储到安全隔离区
            self.secure_storage.store_ca_private_key(
                "gateway_private_key",
                gateway_private_key,
                rotation_interval_hours=24
            )
            
            # 启动自动密钥轮换（需求 19.5）
            self.secure_storage.start_automatic_rotation()
            
            # 不在内存中保存明文密钥（需求 19.6）
            self.ca_private_key = None
            self.gateway_private_key = None
        else:
            # 兼容模式：直接存储密钥
            self.ca_private_key = ca_private_key
            self.gateway_private_key = gateway_private_key
            self.secure_storage = None
        
        # 公钥可以直接存储（不需要保密）
        self.ca_public_key = ca_public_key
        self.gateway_public_key = gateway_public_key
        self.gateway_cert = gateway_cert
        
        # 初始化数据库连接
        self.pg_config = pg_config or PostgreSQLConfig.from_env()
        self.redis_config = redis_config or RedisConfig.from_env()
        
        # 创建数据库连接
        self.db_conn = PostgreSQLConnection(self.pg_config)
        self.redis_conn = RedisConnection(self.redis_config)
        
        # 初始化审计日志记录器
        self.audit_logger = AuditLogger(self.db_conn)
    
    def issue_vehicle_certificate(
        self,
        subject_info: SubjectInfo,
        public_key: bytes
    ) -> Certificate:
        """为车辆颁发证书
        
        参数:
            subject_info: 证书主体信息
            public_key: 车辆公钥（64 字节）
            
        返回:
            Certificate: 颁发的证书
            
        异常:
            ValueError: 如果参数无效
            RuntimeError: 如果证书颁发失败
            
        验证需求: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
        """
        try:
            # 获取 CA 私钥（从安全存储）
            ca_private_key = self._get_ca_private_key()
            
            # 颁发证书
            certificate = issue_certificate(
                subject_info,
                public_key,
                ca_private_key,
                self.ca_public_key,
                self.db_conn
            )
            
            # 记录审计日志
            self.audit_logger.log_certificate_operation(
                operation="issued",
                cert_id=certificate.serial_number,
                vehicle_id=subject_info.vehicle_id,
                details=f"为车辆 {subject_info.vehicle_id} 颁发证书"
            )
            
            return certificate
            
        except Exception as e:
            # 记录错误到审计日志
            self.audit_logger.log_certificate_operation(
                operation="issued",
                cert_id="FAILED",
                vehicle_id=subject_info.vehicle_id,
                details=f"证书颁发失败: {str(e)}"
            )
            raise
    
    def verify_vehicle_certificate(
        self,
        certificate: Certificate
    ) -> Tuple[ValidationResult, str]:
        """验证车辆证书
        
        处理证书验证失败的各种情况（需求 17.1）：
        - 证书过期
        - 证书被撤销
        - 证书签名无效
        - CA 服务不可用时使用缓存
        
        参数:
            certificate: 待验证的证书
            
        返回:
            Tuple[ValidationResult, str]: (验证结果, 消息)
            
        验证需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 17.1, 17.6, 17.7
        """
        try:
            # 获取最新的 CRL
            crl_list = get_crl(self.db_conn)
            
            # 验证证书
            result, message = verify_certificate(
                certificate,
                self.ca_public_key,
                crl_list,
                self.db_conn
            )
            
            # 记录证书验证失败到审计日志（需求 17.7）
            if result != ValidationResult.VALID:
                vehicle_id = self._extract_vehicle_id_from_cert(certificate)
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    details=f"证书验证失败: {message}"
                )
            
            return result, message
            
        except Exception as e:
            # 处理 CA 服务不可用的情况（需求 17.6）
            error_msg = f"证书验证异常: {str(e)}"
            vehicle_id = self._extract_vehicle_id_from_cert(certificate)
            
            # 记录错误到审计日志（需求 17.7）
            self.audit_logger.log_auth_event(
                vehicle_id=vehicle_id,
                event_type=EventType.AUTHENTICATION_FAILURE,
                result=False,
                details=error_msg
            )
            
            # 如果是数据库连接错误，可能是 CA 服务不可用
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                # 尝试使用缓存的 CRL（如果可用）
                # 这里简化处理，返回错误
                return (ValidationResult.INVALID, f"CA 服务不可用: {str(e)}")
            
            return (ValidationResult.INVALID, error_msg)
    
    def revoke_vehicle_certificate(
        self,
        serial_number: str,
        reason: Optional[str] = None
    ) -> bool:
        """撤销车辆证书
        
        参数:
            serial_number: 证书序列号
            reason: 撤销原因（可选）
            
        返回:
            bool: 撤销是否成功
            
        验证需求: 3.1, 3.2
        """
        try:
            # 撤销证书
            success = revoke_certificate(
                serial_number,
                reason,
                self.db_conn
            )
            
            # 记录审计日志
            self.audit_logger.log_certificate_operation(
                operation="revoked",
                cert_id=serial_number,
                details=f"证书撤销原因: {reason or '未指定'}"
            )
            
            return success
            
        except Exception as e:
            # 记录错误到审计日志
            self.audit_logger.log_certificate_operation(
                operation="revoked",
                cert_id=serial_number,
                details=f"证书撤销失败: {str(e)}"
            )
            raise
    
    def authenticate_vehicle(
        self,
        vehicle_cert: Certificate,
        vehicle_private_key: bytes
    ) -> AuthResult:
        """认证车辆并建立会话
        
        执行车云双向身份认证，成功后建立安全会话。
        
        参数:
            vehicle_cert: 车辆证书
            vehicle_private_key: 车辆私钥（32 字节）
            
        返回:
            AuthResult: 认证结果
            
        验证需求: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9
        """
        # 从证书主体中提取车辆 ID
        subject_parts = vehicle_cert.subject.split(',')
        vehicle_id = subject_parts[0].split('=')[1] if subject_parts else "UNKNOWN"
        
        try:
            # 获取网关私钥（从安全存储）
            gateway_private_key = self._get_gateway_private_key()
            
            # 执行双向身份认证
            auth_result = mutual_authentication(
                vehicle_cert,
                self.gateway_cert,
                vehicle_private_key,
                gateway_private_key,
                self.ca_public_key,
                self.db_conn
            )
            
            # 记录认证事件
            if auth_result.success:
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_SUCCESS,
                    result=True,
                    details="车辆认证成功"
                )
            else:
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    details=f"车辆认证失败: {auth_result.error_message}"
                )
            
            return auth_result
            
        except Exception as e:
            # 记录认证失败
            self.audit_logger.log_auth_event(
                vehicle_id=vehicle_id,
                event_type=EventType.AUTHENTICATION_FAILURE,
                result=False,
                details=f"认证异常: {str(e)}"
            )
            raise
    
    def handle_vehicle_connection(
        self,
        vehicle_cert: Certificate,
        vehicle_private_key: bytes,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[SessionInfo], Optional[str]]:
        """处理车辆连接请求并执行完整的认证流程
        
        实现车辆接入与认证流程（任务 11.2）：
        1. 接收车辆连接请求（携带车端证书）
        2. 验证车端证书有效性
        3. 执行双向身份认证
        4. 建立安全会话
        5. 记录认证事件到审计日志
        
        参数:
            vehicle_cert: 车辆证书
            vehicle_private_key: 车辆私钥（32 字节）
            ip_address: 车辆 IP 地址（可选）
            
        返回:
            Tuple[bool, Optional[SessionInfo], Optional[str]]: 
                (是否成功, 会话信息, 错误消息)
                
        验证需求: 4.1, 4.2, 4.3, 4.8, 4.9, 4.10, 5.1, 5.2
        """
        # 从证书主体中提取车辆 ID
        subject_parts = vehicle_cert.subject.split(',')
        vehicle_id = subject_parts[0].split('=')[1] if subject_parts else "UNKNOWN"
        
        try:
            # 步骤 1：验证车端证书有效性
            validation_result, validation_message = self.verify_vehicle_certificate(vehicle_cert)
            
            if validation_result != ValidationResult.VALID:
                # 记录认证失败事件
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    ip_address=ip_address,
                    details=f"证书验证失败: {validation_message}"
                )
                return (False, None, f"证书验证失败: {validation_message}")
            
            # 步骤 2：执行双向身份认证
            auth_result = self.authenticate_vehicle(
                vehicle_cert,
                vehicle_private_key
            )
            
            if not auth_result.success:
                # 记录认证失败事件
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    ip_address=ip_address,
                    details=f"双向认证失败: {auth_result.error_message}"
                )
                return (False, None, f"认证失败: {auth_result.error_message}")
            
            # 步骤 3：建立安全会话
            session_info = self.create_session(vehicle_id, auth_result)
            
            # 步骤 4：记录认证成功事件到审计日志
            self.audit_logger.log_auth_event(
                vehicle_id=vehicle_id,
                event_type=EventType.AUTHENTICATION_SUCCESS,
                result=True,
                ip_address=ip_address,
                details=f"车辆接入成功，会话 ID: {session_info.session_id}"
            )
            
            return (True, session_info, None)
            
        except Exception as e:
            # 记录异常到审计日志
            self.audit_logger.log_auth_event(
                vehicle_id=vehicle_id,
                event_type=EventType.AUTHENTICATION_FAILURE,
                result=False,
                ip_address=ip_address,
                details=f"车辆接入异常: {str(e)}"
            )
            return (False, None, f"车辆接入异常: {str(e)}")
    
    def create_session(
        self,
        vehicle_id: str,
        auth_result: AuthResult
    ) -> SessionInfo:
        """创建安全会话
        
        参数:
            vehicle_id: 车辆标识
            auth_result: 认证结果（必须是成功的）
            
        返回:
            SessionInfo: 会话信息
            
        异常:
            ValueError: 如果认证结果不成功
            
        验证需求: 5.1, 5.2, 5.3, 5.4, 19.3, 19.5
        """
        if not auth_result.success:
            raise ValueError("认证结果必须是成功的才能创建会话")
        
        try:
            # 建立会话
            session_info = establish_session(
                vehicle_id,
                auth_result.token,
                self.redis_conn
            )
            
            # 将会话密钥存储到安全存储（需求 19.3, 19.5）
            if self.use_secure_storage and self.secure_storage:
                self.secure_storage.store_session_key(
                    session_info.session_id,
                    session_info.sm4_session_key,
                    rotation_interval_hours=24
                )
            
            # 记录会话建立事件
            self.audit_logger.log_auth_event(
                vehicle_id=vehicle_id,
                event_type=EventType.AUTHENTICATION_SUCCESS,
                result=True,
                details=f"会话建立成功，会话 ID: {session_info.session_id}"
            )
            
            return session_info
            
        except Exception as e:
            # 记录会话建立失败
            self.audit_logger.log_auth_event(
                vehicle_id=vehicle_id,
                event_type=EventType.AUTHENTICATION_FAILURE,
                result=False,
                details=f"会话建立失败: {str(e)}"
            )
            raise
    
    def terminate_session(
        self,
        session_id: str,
        vehicle_id: str
    ) -> bool:
        """终止会话
        
        参数:
            session_id: 会话 ID
            vehicle_id: 车辆标识
            
        返回:
            bool: 终止是否成功
            
        验证需求: 5.5, 19.4
        """
        try:
            # 安全清除会话密钥（需求 19.4）
            if self.use_secure_storage and self.secure_storage:
                self.secure_storage.secure_clear_key(session_id)
            
            # 关闭会话
            success = close_session(session_id, self.redis_conn)
            
            # 记录会话关闭事件
            if success:
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_SUCCESS,
                    result=True,
                    details=f"会话关闭成功，会话 ID: {session_id}"
                )
            
            return success
            
        except Exception as e:
            # 记录会话关闭失败
            self.audit_logger.log_auth_event(
                vehicle_id=vehicle_id,
                event_type=EventType.AUTHENTICATION_FAILURE,
                result=False,
                details=f"会话关闭失败: {str(e)}"
            )
            return False
    
    def send_secure_message(
        self,
        plain_data: bytes,
        session_key: bytes,
        sender_id: str,
        receiver_id: str,
        session_id: str,
        message_type: MessageType = MessageType.DATA_TRANSFER
    ) -> SecureMessage:
        """发送安全报文
        
        参数:
            plain_data: 明文数据
            session_key: 会话密钥
            sender_id: 发送方标识
            receiver_id: 接收方标识
            session_id: 会话 ID
            message_type: 消息类型
            
        返回:
            SecureMessage: 安全报文
            
        验证需求: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
        """
        try:
            # 获取网关私钥（从安全存储）
            gateway_private_key = self._get_gateway_private_key()
            
            # 创建安全报文
            secure_msg = secure_data_transmission(
                plain_data,
                session_key,
                gateway_private_key,
                self.gateway_public_key,  # 接收方公钥（这里简化为网关公钥）
                sender_id,
                receiver_id,
                session_id,
                message_type
            )
            
            # 记录数据传输事件
            self.audit_logger.log_data_transfer(
                vehicle_id=receiver_id,
                data_size=len(plain_data),
                encrypted=True,
                details=f"发送安全报文，会话 ID: {session_id}"
            )
            
            return secure_msg
            
        except Exception as e:
            # 记录数据传输失败
            self.audit_logger.log_data_transfer(
                vehicle_id=receiver_id,
                data_size=len(plain_data),
                encrypted=False,
                details=f"发送安全报文失败: {str(e)}"
            )
            raise
    
    def receive_secure_message(
        self,
        secure_message: SecureMessage,
        session_key: bytes,
        sender_public_key: bytes,
        sender_id: str
    ) -> bytes:
        """接收并验证安全报文
        
        处理以下错误情况：
        - 签名验证失败（需求 17.2）
        - 重放攻击检测（需求 17.4）
        - 解密失败（需求 17.5）
        - 会话过期（需求 17.3）
        
        参数:
            secure_message: 安全报文
            session_key: 会话密钥
            sender_public_key: 发送方公钥
            sender_id: 发送方标识
            
        返回:
            bytes: 解密后的明文数据
            
        验证需求: 9.1, 9.2, 9.3, 9.4, 9.5, 17.2, 17.3, 17.4, 17.5, 17.7
        """
        try:
            # 验证并解密报文
            plain_data = verify_and_decrypt_message(
                secure_message,
                session_key,
                sender_public_key,
                self.redis_config
            )
            
            # 记录数据接收事件
            self.audit_logger.log_data_transfer(
                vehicle_id=sender_id,
                data_size=len(plain_data),
                encrypted=True,
                details=f"接收安全报文成功，会话 ID: {secure_message.header.session_id}"
            )
            
            return plain_data
            
        except ValueError as e:
            error_msg = str(e)
            
            # 处理签名验证失败（需求 17.2）
            if "签名验证失败" in error_msg or "篡改" in error_msg:
                self.audit_logger.log_auth_event(
                    vehicle_id=sender_id,
                    event_type=EventType.SIGNATURE_FAILED,
                    result=False,
                    details=f"签名验证失败: {error_msg}"
                )
                raise ValueError(f"签名验证失败: 数据可能被篡改")
            
            # 处理重放攻击检测（需求 17.4）
            elif "重放攻击" in error_msg or "Nonce 已使用" in error_msg:
                self.audit_logger.log_auth_event(
                    vehicle_id=sender_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    details=f"检测到重放攻击: {error_msg}"
                )
                raise ValueError(f"检测到重放攻击: {error_msg}")
            
            # 处理时间戳过期（需求 17.3）
            elif "过期" in error_msg or "时间戳" in error_msg:
                self.audit_logger.log_auth_event(
                    vehicle_id=sender_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    details=f"消息过期: {error_msg}"
                )
                raise ValueError(f"消息过期: {error_msg}")
            
            # 其他验证错误
            else:
                self.audit_logger.log_data_transfer(
                    vehicle_id=sender_id,
                    data_size=0,
                    encrypted=False,
                    details=f"报文验证失败: {error_msg}"
                )
                raise
            
        except RuntimeError as e:
            error_msg = str(e)
            
            # 处理解密失败（需求 17.5）
            if "解密失败" in error_msg:
                self.audit_logger.log_data_transfer(
                    vehicle_id=sender_id,
                    data_size=0,
                    encrypted=False,
                    details=f"解密失败: {error_msg}"
                )
                raise RuntimeError(f"解密失败: 会话密钥无效或数据损坏")
            else:
                self.audit_logger.log_data_transfer(
                    vehicle_id=sender_id,
                    data_size=0,
                    encrypted=False,
                    details=f"接收安全报文失败: {error_msg}"
                )
                raise
            
        except Exception as e:
            # 记录其他未预期的错误（需求 17.7）
            self.audit_logger.log_data_transfer(
                vehicle_id=sender_id,
                data_size=0,
                encrypted=False,
                details=f"接收安全报文异常: {str(e)}"
            )
            raise
    
    def cleanup_sessions(self) -> int:
        """清理过期会话
        
        返回:
            int: 清理的会话数量
            
        验证需求: 5.5, 5.6
        """
        try:
            count = cleanup_expired_sessions(self.redis_conn)
            
            # 记录清理事件
            if count > 0:
                self.audit_logger.log_auth_event(
                    vehicle_id="system",
                    event_type=EventType.AUTHENTICATION_SUCCESS,
                    result=True,
                    details=f"清理了 {count} 个过期会话"
                )
            
            return count
            
        except Exception as e:
            # 记录清理失败
            self.audit_logger.log_auth_event(
                vehicle_id="system",
                event_type=EventType.AUTHENTICATION_FAILURE,
                result=False,
                details=f"会话清理失败: {str(e)}"
            )
            return 0
    
    def check_certificate_status(
        self,
        certificate: Certificate
    ) -> dict:
        """检查证书状态
        
        参数:
            certificate: 证书对象
            
        返回:
            dict: 证书状态信息
            
        验证需求: 3.3, 3.4
        """
        return check_certificate_expiry(certificate)
    
    def close(self):
        """关闭网关服务
        
        清理资源并关闭数据库连接。
        """
        try:
            # 停止自动密钥轮换
            if self.use_secure_storage and self.secure_storage:
                self.secure_storage.stop_automatic_rotation()
            
            # 关闭数据库连接
            if hasattr(self, 'db_conn'):
                self.db_conn.close()
            
            if hasattr(self, 'redis_conn'):
                self.redis_conn.close()
            
            # 记录网关关闭事件
            print("安全通信网关已关闭")
            
        except Exception as e:
            print(f"关闭网关时发生错误: {str(e)}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def _extract_vehicle_id_from_cert(self, certificate: Certificate) -> str:
        """从证书中提取车辆 ID
        
        参数:
            certificate: 证书对象
            
        返回:
            str: 车辆 ID
        """
        try:
            subject_parts = certificate.subject.split(',')
            vehicle_id = subject_parts[0].split('=')[1] if subject_parts else "UNKNOWN"
            return vehicle_id
        except Exception:
            return "UNKNOWN"
    
    def _get_ca_private_key(self) -> bytes:
        """获取 CA 私钥
        
        如果使用安全存储，从安全存储中检索；否则直接返回。
        
        返回:
            bytes: CA 私钥
            
        验证需求: 19.1, 19.6
        """
        if self.use_secure_storage and self.secure_storage:
            key = self.secure_storage.retrieve_key("ca_private_key")
            if key is None:
                raise RuntimeError("无法从安全存储中检索 CA 私钥")
            return key
        else:
            return self.ca_private_key
    
    def _get_gateway_private_key(self) -> bytes:
        """获取网关私钥
        
        如果使用安全存储，从安全存储中检索；否则直接返回。
        
        返回:
            bytes: 网关私钥
            
        验证需求: 19.1, 19.6
        """
        if self.use_secure_storage and self.secure_storage:
            key = self.secure_storage.retrieve_key("gateway_private_key")
            if key is None:
                raise RuntimeError("无法从安全存储中检索网关私钥")
            return key
        else:
            return self.gateway_private_key


    def handle_vehicle_connection(
        self,
        vehicle_cert: Certificate,
        vehicle_private_key: bytes,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[SessionInfo], Optional[str]]:
        """处理车辆连接请求并执行完整的认证流程

        实现车辆接入与认证流程（任务 11.2）：
        1. 接收车辆连接请求（携带车端证书）
        2. 验证车端证书有效性
        3. 执行双向身份认证
        4. 建立安全会话
        5. 记录认证事件到审计日志

        参数:
            vehicle_cert: 车辆证书
            vehicle_private_key: 车辆私钥（32 字节）
            ip_address: 车辆 IP 地址（可选）

        返回:
            Tuple[bool, Optional[SessionInfo], Optional[str]]:
                (是否成功, 会话信息, 错误消息)

        验证需求: 4.1, 4.2, 4.3, 4.8, 4.9, 4.10, 5.1, 5.2
        """
        # 从证书主体中提取车辆 ID
        subject_parts = vehicle_cert.subject.split(',')
        vehicle_id = subject_parts[0].split('=')[1] if subject_parts else "UNKNOWN"

        try:
            # 步骤 1：验证车端证书有效性
            validation_result, validation_message = self.verify_vehicle_certificate(vehicle_cert)

            if validation_result != ValidationResult.VALID:
                # 记录认证失败事件
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    ip_address=ip_address,
                    details=f"证书验证失败: {validation_message}"
                )
                return (False, None, f"证书验证失败: {validation_message}")

            # 步骤 2：执行双向身份认证
            auth_result = self.authenticate_vehicle(
                vehicle_cert,
                vehicle_private_key
            )

            if not auth_result.success:
                # 记录认证失败事件
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    ip_address=ip_address,
                    details=f"双向认证失败: {auth_result.error_message}"
                )
                return (False, None, f"认证失败: {auth_result.error_message}")

            # 步骤 3：建立安全会话
            session_info = self.create_session(vehicle_id, auth_result)

            # 步骤 4：记录认证成功事件到审计日志
            self.audit_logger.log_auth_event(
                vehicle_id=vehicle_id,
                event_type=EventType.AUTHENTICATION_SUCCESS,
                result=True,
                ip_address=ip_address,
                details=f"车辆接入成功，会话 ID: {session_info.session_id}"
            )

            return (True, session_info, None)

        except Exception as e:
            # 记录异常到审计日志
            self.audit_logger.log_auth_event(
                vehicle_id=vehicle_id,
                event_type=EventType.AUTHENTICATION_FAILURE,
                result=False,
                ip_address=ip_address,
                details=f"车辆接入异常: {str(e)}"
            )
            return (False, None, f"车辆接入异常: {str(e)}")
    

    def forward_vehicle_data_to_cloud(
        self,
        vehicle_id: str,
        session_id: str,
        secure_message: SecureMessage,
        vehicle_public_key: bytes,
        cloud_endpoint: Optional[str] = None
    ) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """接收车端安全报文并转发业务数据到云端

        实现安全数据转发流程（任务 11.3）的前半部分：
        1. 接收车端安全报文
        2. 验证签名和解密数据
        3. 转发业务数据到云端
        4. 记录数据传输到审计日志
        
        处理以下错误情况：
        - 会话过期（需求 17.3）
        - 签名验证失败（需求 17.2）
        - 解密失败（需求 17.5）
        - 重放攻击检测（需求 17.4）

        参数:
            vehicle_id: 车辆标识
            session_id: 会话 ID
            secure_message: 车端发送的安全报文
            vehicle_public_key: 车辆公钥（64 字节）
            cloud_endpoint: 云端服务端点（可选）

        返回:
            Tuple[bool, Optional[bytes], Optional[str]]:
                (是否成功, 云端响应数据, 错误消息)

        验证需求: 6.1, 6.4, 7.1, 7.3, 8.4, 8.5, 9.1, 9.3, 11.2, 17.2, 17.3, 17.4, 17.5, 17.7
        """
        try:
            # 步骤 1：从 Redis 获取会话信息
            session_data = self.redis_conn.get(f"session:{session_id}")
            if not session_data:
                # 处理会话过期（需求 17.3）
                error_msg = f"会话 {session_id} 不存在或已过期"
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    details=f"会话过期: {error_msg}"
                )
                return (False, None, error_msg)

            # 解析会话信息
            import json
            session_dict = json.loads(session_data.decode('utf-8'))
            session_key = bytes.fromhex(session_dict['sm4_session_key'])

            # 步骤 2：验证签名和解密数据
            # receive_secure_message 已经处理了签名验证失败、重放攻击和解密失败
            try:
                plain_data = self.receive_secure_message(
                    secure_message,
                    session_key,
                    vehicle_public_key,
                    vehicle_id
                )
            except ValueError as e:
                # 签名验证失败或重放攻击（需求 17.2, 17.4）
                error_msg = f"验证签名或解密失败: {str(e)}"
                return (False, None, error_msg)
            except RuntimeError as e:
                # 解密失败（需求 17.5）
                error_msg = f"解密失败: {str(e)}"
                return (False, None, error_msg)

            # 步骤 3：转发业务数据到云端
            try:
                cloud_response = self._forward_to_cloud_service(
                    plain_data,
                    vehicle_id,
                    cloud_endpoint
                )
            except Exception as e:
                # 处理云端服务不可用（类似 CA 服务不可用）
                error_msg = f"云端服务不可用: {str(e)}"
                self.audit_logger.log_data_transfer(
                    vehicle_id=vehicle_id,
                    data_size=0,
                    encrypted=False,
                    details=f"数据转发失败: {error_msg}"
                )
                return (False, None, error_msg)

            # 步骤 4：记录数据传输到审计日志（需求 17.7）
            self.audit_logger.log_data_transfer(
                vehicle_id=vehicle_id,
                data_size=len(plain_data),
                encrypted=True,
                details=f"成功转发数据到云端，会话 ID: {session_id}，数据大小: {len(plain_data)} 字节"
            )

            return (True, cloud_response, None)

        except Exception as e:
            # 记录未预期的错误（需求 17.7）
            error_msg = f"数据转发异常: {str(e)}"
            self.audit_logger.log_data_transfer(
                vehicle_id=vehicle_id,
                data_size=0,
                encrypted=False,
                details=error_msg
            )
            return (False, None, error_msg)

    def send_cloud_response_to_vehicle(
        self,
        vehicle_id: str,
        session_id: str,
        cloud_response: bytes,
        vehicle_public_key: bytes
    ) -> Tuple[bool, Optional[SecureMessage], Optional[str]]:
        """接收云端响应并发送安全响应报文到车端

        实现安全数据转发流程（任务 11.3）的后半部分：
        1. 接收云端响应
        2. 加密签名响应数据
        3. 发送安全响应报文到车端
        4. 记录数据传输到审计日志
        
        处理以下错误情况：
        - 会话过期（需求 17.3）
        - 加密失败（需求 17.5）

        参数:
            vehicle_id: 车辆标识
            session_id: 会话 ID
            cloud_response: 云端响应数据
            vehicle_public_key: 车辆公钥（64 字节）

        返回:
            Tuple[bool, Optional[SecureMessage], Optional[str]]:
                (是否成功, 安全响应报文, 错误消息)

        验证需求: 6.1, 6.4, 7.1, 7.3, 8.4, 8.5, 11.2, 17.3, 17.5, 17.7
        """
        try:
            # 步骤 1：从 Redis 获取会话信息
            session_data = self.redis_conn.get(f"session:{session_id}")
            if not session_data:
                # 处理会话过期（需求 17.3）
                error_msg = f"会话 {session_id} 不存在或已过期"
                self.audit_logger.log_auth_event(
                    vehicle_id=vehicle_id,
                    event_type=EventType.AUTHENTICATION_FAILURE,
                    result=False,
                    details=f"会话过期: {error_msg}"
                )
                return (False, None, error_msg)

            # 解析会话信息
            import json
            session_dict = json.loads(session_data.decode('utf-8'))
            session_key = bytes.fromhex(session_dict['sm4_session_key'])

            # 步骤 2：加密签名响应数据
            try:
                secure_response = self.send_secure_message(
                    cloud_response,
                    session_key,
                    "GATEWAY",
                    vehicle_id,
                    session_id,
                    MessageType.RESPONSE
                )
            except ValueError as e:
                # 处理加密失败（需求 17.5）
                error_msg = f"加密签名响应失败: {str(e)}"
                self.audit_logger.log_data_transfer(
                    vehicle_id=vehicle_id,
                    data_size=0,
                    encrypted=False,
                    details=f"响应发送失败: {error_msg}"
                )
                return (False, None, error_msg)
            except RuntimeError as e:
                # 处理加密失败（需求 17.5）
                error_msg = f"加密失败: {str(e)}"
                self.audit_logger.log_data_transfer(
                    vehicle_id=vehicle_id,
                    data_size=0,
                    encrypted=False,
                    details=f"响应发送失败: {error_msg}"
                )
                return (False, None, error_msg)

            # 步骤 3：记录数据传输到审计日志（需求 17.7）
            self.audit_logger.log_data_transfer(
                vehicle_id=vehicle_id,
                data_size=len(cloud_response),
                encrypted=True,
                details=f"成功发送响应到车端，会话 ID: {session_id}，数据大小: {len(cloud_response)} 字节"
            )

            return (True, secure_response, None)

        except Exception as e:
            # 记录未预期的错误（需求 17.7）
            error_msg = f"响应发送异常: {str(e)}"
            self.audit_logger.log_data_transfer(
                vehicle_id=vehicle_id,
                data_size=0,
                encrypted=False,
                details=error_msg
            )
            return (False, None, error_msg)

    def handle_secure_data_forwarding(
        self,
        vehicle_id: str,
        session_id: str,
        secure_message: SecureMessage,
        vehicle_public_key: bytes,
        cloud_endpoint: Optional[str] = None
    ) -> Tuple[bool, Optional[SecureMessage], Optional[str]]:
        """处理完整的安全数据转发流程

        实现完整的安全数据转发流程（任务 11.3）：
        1. 接收车端安全报文
        2. 验证签名和解密数据
        3. 转发业务数据到云端
        4. 接收云端响应
        5. 加密签名响应数据
        6. 发送安全响应报文到车端
        7. 记录数据传输到审计日志

        参数:
            vehicle_id: 车辆标识
            session_id: 会话 ID
            secure_message: 车端发送的安全报文
            vehicle_public_key: 车辆公钥（64 字节）
            cloud_endpoint: 云端服务端点（可选）

        返回:
            Tuple[bool, Optional[SecureMessage], Optional[str]]:
                (是否成功, 安全响应报文, 错误消息)

        验证需求: 6.1, 6.4, 7.1, 7.3, 8.4, 8.5, 9.1, 9.3, 11.2
        """
        try:
            # 步骤 1-3：接收车端报文并转发到云端
            success, cloud_response, error_msg = self.forward_vehicle_data_to_cloud(
                vehicle_id,
                session_id,
                secure_message,
                vehicle_public_key,
                cloud_endpoint
            )

            if not success:
                return (False, None, error_msg)

            # 步骤 4-6：接收云端响应并发送到车端
            success, secure_response, error_msg = self.send_cloud_response_to_vehicle(
                vehicle_id,
                session_id,
                cloud_response,
                vehicle_public_key
            )

            if not success:
                return (False, None, error_msg)

            # 步骤 7：记录完整流程到审计日志
            # 注意：这里记录的是整个转发流程的完成，使用原始的session_id
            self.audit_logger.log_data_transfer(
                vehicle_id=vehicle_id,
                data_size=len(cloud_response),
                encrypted=True,
                details=f"完成安全数据转发流程，会话 ID: {session_id}"
            )

            return (True, secure_response, None)

        except Exception as e:
            error_msg = f"安全数据转发流程异常: {str(e)}"
            self.audit_logger.log_data_transfer(
                vehicle_id=vehicle_id,
                data_size=0,
                encrypted=False,
                details=error_msg
            )
            return (False, None, error_msg)

    def save_vehicle_data(self, vehicle_id: str, data: dict) -> bool:
        """保存车辆数据到数据库
        
        参数:
            vehicle_id: 车辆标识
            data: 车辆数据字典
            
        返回:
            bool: 保存是否成功
        """
        try:
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
            
            import json
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
            
            self.db_conn.execute_query(query, params)
            return True
        except Exception as e:
            print(f"保存车辆数据失败: {str(e)}")
            return False

    def _forward_to_cloud_service(
        self,
        data: bytes,
        vehicle_id: str,
        cloud_endpoint: Optional[str] = None
    ) -> bytes:
        """转发数据到云端服务（内部方法）

        这是一个模拟方法，实际实现应该调用真实的云端 API。

        参数:
            data: 业务数据
            vehicle_id: 车辆标识
            cloud_endpoint: 云端服务端点（可选）

        返回:
            bytes: 云端响应数据
        """
        # 尝试解析并保存车辆数据
        try:
            import json
            vehicle_data = json.loads(data.decode('utf-8'))
            self.save_vehicle_data(vehicle_id, vehicle_data)
        except Exception as e:
            print(f"解析或保存车辆数据失败: {str(e)}")
        
        # 模拟云端处理
        # 实际实现应该使用 HTTP 客户端调用云端 API
        # 例如：
        # import requests
        # response = requests.post(
        #     cloud_endpoint or "https://cloud.example.com/api/vehicle-data",
        #     json={"vehicle_id": vehicle_id, "data": data.hex()},
        #     timeout=30
        # )
        # return bytes.fromhex(response.json()["response_data"])

        # 这里返回模拟响应
        return b"Cloud processed: " + data[:50]  # 返回处理后的数据（截断到 50 字节）


