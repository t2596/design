"""证书管理 API

提供证书查询、颁发、撤销和 CRL 查询功能。

验证需求: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.db.postgres import PostgreSQLConnection
from config.database import PostgreSQLConfig
from src.certificate_manager import issue_certificate, revoke_certificate, get_crl
from src.models.certificate import SubjectInfo
from src.audit_logger import AuditLogger
from src.models.enums import EventType
from src.api.main import verify_token

router = APIRouter()


class CertificateInfo(BaseModel):
    """证书信息模型"""
    serial_number: str
    subject: str
    issuer: str
    valid_from: datetime
    valid_to: datetime
    status: str  # "valid", "expired", "revoked"


class CertificateListResponse(BaseModel):
    """证书列表响应"""
    total: int
    certificates: List[CertificateInfo]


class IssueCertificateRequest(BaseModel):
    """证书颁发请求"""
    vehicle_id: str
    organization: str = "Vehicle Manufacturer"
    country: str = "CN"
    public_key: str  # 十六进制格式的公钥


class IssueCertificateResponse(BaseModel):
    """证书颁发响应"""
    serial_number: str
    version: int
    issuer: str
    subject: str
    valid_from: str
    valid_to: str
    public_key: str
    signature: str
    signature_algorithm: str
    extensions: dict
    message: str


class RevokeCertificateRequest(BaseModel):
    """证书撤销请求"""
    serial_number: str
    reason: Optional[str] = None


class RevokeCertificateResponse(BaseModel):
    """证书撤销响应"""
    success: bool
    message: str


class CRLResponse(BaseModel):
    """CRL 响应"""
    total: int
    revoked_certificates: List[str]


@router.get("", response_model=CertificateListResponse)
async def get_certificates(
    status: Optional[str] = Query(None, description="证书状态过滤（valid/expired/revoked）"),
    user: str = Depends(verify_token)
):
    """获取证书列表
    
    返回所有已颁发的证书列表，支持按状态过滤。
    
    参数:
        status: 证书状态过滤（可选）
        
    返回:
        CertificateListResponse: 证书列表
        
    验证需求: 15.1, 15.2
    """
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        # 查询所有证书
        query = """
            SELECT serial_number, subject, issuer, valid_from, valid_to
            FROM certificates
            ORDER BY valid_from DESC
        """
        result = db_conn.execute_query(query, ())
        
        # 获取 CRL
        crl_list = get_crl(db_conn)
        
        certificates = []
        current_time = datetime.now()
        
        for row in result:
            # 确定证书状态
            if row['serial_number'] in crl_list:
                cert_status = "revoked"
            elif current_time > row['valid_to']:
                cert_status = "expired"
            elif current_time < row['valid_from']:
                cert_status = "not_yet_valid"
            else:
                cert_status = "valid"
            
            # 应用状态过滤
            if status and cert_status != status:
                continue
            
            cert_info = CertificateInfo(
                serial_number=row['serial_number'],
                subject=row['subject'],
                issuer=row['issuer'],
                valid_from=row['valid_from'],
                valid_to=row['valid_to'],
                status=cert_status
            )
            certificates.append(cert_info)
        
        db_conn.close()
        
        return CertificateListResponse(
            total=len(certificates),
            certificates=certificates
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取证书列表失败: {str(e)}"
        )


@router.post("/issue", response_model=IssueCertificateResponse)
async def issue_new_certificate(
    request: IssueCertificateRequest,
    http_request: Request,
    user: str = Depends(verify_token)
):
    """颁发新证书
    
    为车辆颁发新的 SM2 数字证书。
    
    参数:
        request: 证书颁发请求
        
    返回:
        IssueCertificateResponse: 颁发结果
        
    验证需求: 15.3, 15.4
    """
    # 获取客户端 IP 地址
    client_ip = http_request.client.host if http_request.client else "unknown"
    
    try:
        # 解析客户端提供的公钥
        try:
            public_key = bytes.fromhex(request.public_key)
            if len(public_key) != 64:
                raise HTTPException(
                    status_code=400,
                    detail=f"公钥长度必须为 64 字节，当前为 {len(public_key)}"
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="公钥格式错误，必须是十六进制字符串"
            )
        
        # 创建证书主体信息
        subject_info = SubjectInfo(
            vehicle_id=request.vehicle_id,
            organization=request.organization,
            country=request.country
        )
        
        # 从环境变量加载 CA 密钥（简化实现）
        import os
        ca_private_key_hex = os.getenv("CA_PRIVATE_KEY")
        ca_public_key_hex = os.getenv("CA_PUBLIC_KEY")
        
        if not ca_private_key_hex or not ca_public_key_hex:
            raise HTTPException(
                status_code=500,
                detail="CA 密钥未配置"
            )
        
        ca_private_key = bytes.fromhex(ca_private_key_hex)
        ca_public_key = bytes.fromhex(ca_public_key_hex)
        
        # 获取证书有效期配置
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        from src.security_policy_manager import SecurityPolicyManager
        policy_manager = SecurityPolicyManager(db_conn)
        certificate_validity_days = policy_manager.get_certificate_validity()
        
        # 颁发证书（使用配置的有效期）
        certificate = issue_certificate(
            subject_info,
            public_key,
            ca_private_key,
            ca_public_key,
            db_conn,
            validity_days=certificate_validity_days
        )
        
        # 记录证书颁发事件到审计日志
        audit_logger = AuditLogger(db_conn)
        audit_logger.log_certificate_operation(
            operation="issued",
            cert_id=certificate.serial_number,
            vehicle_id=request.vehicle_id,
            ip_address=client_ip,
            details=f"为车辆 {request.vehicle_id} 颁发证书，序列号: {certificate.serial_number}"
        )
        
        db_conn.close()
        
        return IssueCertificateResponse(
            serial_number=certificate.serial_number,
            version=certificate.version,
            issuer=certificate.issuer,
            subject=certificate.subject,
            valid_from=certificate.valid_from.isoformat(),
            valid_to=certificate.valid_to.isoformat(),
            public_key=certificate.public_key.hex(),
            signature=certificate.signature.hex(),
            signature_algorithm=certificate.signature_algorithm,
            extensions=certificate.extensions.to_dict() if certificate.extensions else {},
            message=f"证书颁发成功，序列号: {certificate.serial_number}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # 记录证书颁发失败事件到审计日志
        try:
            db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
            audit_logger = AuditLogger(db_conn)
            audit_logger.log_certificate_operation(
                operation="issued",
                cert_id="FAILED",
                vehicle_id=request.vehicle_id,
                ip_address=client_ip,
                details=f"为车辆 {request.vehicle_id} 颁发证书失败: {str(e)}"
            )
            db_conn.close()
        except:
            pass  # 避免审计日志记录失败影响主流程
        
        raise HTTPException(
            status_code=500,
            detail=f"证书颁发失败: {str(e)}"
        )


@router.post("/revoke", response_model=RevokeCertificateResponse)
async def revoke_existing_certificate(
    request: RevokeCertificateRequest,
    http_request: Request,
    user: str = Depends(verify_token)
):
    """撤销证书
    
    将指定证书添加到证书撤销列表（CRL）。
    
    参数:
        request: 证书撤销请求
        
    返回:
        RevokeCertificateResponse: 撤销结果
        
    验证需求: 15.5
    """
    # 获取客户端 IP 地址
    client_ip = http_request.client.host if http_request.client else "unknown"
    
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        
        # 查询证书信息以获取车辆ID
        query = "SELECT subject FROM certificates WHERE serial_number = %s"
        result = db_conn.execute_query(query, (request.serial_number,))
        vehicle_id = "unknown"
        if result:
            # 从 subject 中提取车辆ID（格式: CN=VIN_xxx, O=xxx, C=xxx）
            subject = result[0]['subject']
            if 'CN=' in subject:
                vehicle_id = subject.split('CN=')[1].split(',')[0].strip()
        
        success = revoke_certificate(
            request.serial_number,
            request.reason,
            db_conn
        )
        
        # 记录证书撤销事件到审计日志
        audit_logger = AuditLogger(db_conn)
        audit_logger.log_certificate_operation(
            operation="revoked",
            cert_id=request.serial_number,
            vehicle_id=vehicle_id,
            ip_address=client_ip,
            details=f"撤销证书 {request.serial_number}，原因: {request.reason or '未指定'}"
        )
        
        db_conn.close()
        
        if success:
            return RevokeCertificateResponse(
                success=True,
                message=f"证书 {request.serial_number} 已成功撤销"
            )
        else:
            return RevokeCertificateResponse(
                success=False,
                message=f"证书 {request.serial_number} 撤销失败"
            )
        
    except Exception as e:
        # 记录证书撤销失败事件到审计日志
        try:
            db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
            audit_logger = AuditLogger(db_conn)
            audit_logger.log_certificate_operation(
                operation="revoked",
                cert_id=request.serial_number,
                vehicle_id="unknown",
                ip_address=client_ip,
                details=f"撤销证书失败: {str(e)}"
            )
            db_conn.close()
        except:
            pass  # 避免审计日志记录失败影响主流程
        
        raise HTTPException(
            status_code=500,
            detail=f"证书撤销失败: {str(e)}"
        )


@router.get("/crl", response_model=CRLResponse)
async def get_certificate_revocation_list(
    user: str = Depends(verify_token)
):
    """获取证书撤销列表（CRL）
    
    返回当前的证书撤销列表。
    
    返回:
        CRLResponse: CRL 数据
        
    验证需求: 15.6
    """
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        crl_list = get_crl(db_conn)
        db_conn.close()
        
        return CRLResponse(
            total=len(crl_list),
            revoked_certificates=crl_list
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取 CRL 失败: {str(e)}"
        )
