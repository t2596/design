"""安全策略配置 API

提供安全策略查询和更新功能。

验证需求: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from src.api.main import verify_token
from src.db.postgres import PostgreSQLConnection
from config.database import PostgreSQLConfig
from src.security_policy_manager import SecurityPolicyManager, SecurityPolicy as PolicyModel

router = APIRouter()


class SecurityPolicy(BaseModel):
    """安全策略模型"""
    session_timeout: int = Field(
        default=86400,
        description="会话超时时间（秒），默认 24 小时",
        ge=300,
        le=604800
    )
    certificate_validity: int = Field(
        default=365,
        description="证书有效期（天），默认 1 年",
        ge=30,
        le=1825
    )
    timestamp_tolerance: int = Field(
        default=300,
        description="时间戳容差范围（秒），默认 5 分钟",
        ge=60,
        le=600
    )
    concurrent_session_strategy: str = Field(
        default="reject_new",
        description="并发会话处理策略（reject_new 或 terminate_old）"
    )
    max_auth_failures: int = Field(
        default=5,
        description="最大认证失败次数（超过后暂时阻止）",
        ge=3,
        le=10
    )
    auth_failure_lockout_duration: int = Field(
        default=300,
        description="认证失败锁定时长（秒），默认 5 分钟",
        ge=60,
        le=3600
    )


class SecurityPolicyResponse(BaseModel):
    """安全策略响应"""
    policy: SecurityPolicy
    message: str


@router.get("/security", response_model=SecurityPolicyResponse)
async def get_security_policy(
    user: str = Depends(verify_token)
):
    """获取当前安全策略
    
    返回当前系统的安全策略配置（从数据库加载）。
    
    返回:
        SecurityPolicyResponse: 安全策略
        
    验证需求: 16.1
    """
    try:
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        policy_manager = SecurityPolicyManager(db_conn)
        
        # 从数据库加载策略
        policy_model = policy_manager.get_policy()
        
        # 转换为API响应模型
        policy = SecurityPolicy(
            session_timeout=policy_model.session_timeout,
            certificate_validity=policy_model.certificate_validity,
            timestamp_tolerance=policy_model.timestamp_tolerance,
            concurrent_session_strategy=policy_model.concurrent_session_strategy,
            max_auth_failures=policy_model.max_auth_failures,
            auth_failure_lockout_duration=policy_model.auth_failure_lockout_duration
        )
        
        db_conn.close()
        
        return SecurityPolicyResponse(
            policy=policy,
            message="成功获取安全策略"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取安全策略失败: {str(e)}"
        )


@router.put("/security", response_model=SecurityPolicyResponse)
async def update_security_policy(
    policy: SecurityPolicy,
    user: str = Depends(verify_token)
):
    """更新安全策略
    
    更新系统的安全策略配置并持久化到数据库。
    
    参数:
        policy: 新的安全策略
        
    返回:
        SecurityPolicyResponse: 更新后的安全策略
        
    验证需求: 16.2, 16.3, 16.4, 16.5, 16.6
    """
    try:
        # 验证并发会话策略
        if policy.concurrent_session_strategy not in ["reject_new", "terminate_old"]:
            raise HTTPException(
                status_code=400,
                detail="无效的并发会话策略，必须是 reject_new 或 terminate_old"
            )
        
        # 验证参数范围（Pydantic 已经通过 Field 验证了）
        # 这里可以添加额外的业务逻辑验证
        
        # 持久化到数据库
        db_conn = PostgreSQLConnection(PostgreSQLConfig.from_env())
        policy_manager = SecurityPolicyManager(db_conn)
        
        # 转换为内部模型
        policy_model = PolicyModel(
            session_timeout=policy.session_timeout,
            certificate_validity=policy.certificate_validity,
            timestamp_tolerance=policy.timestamp_tolerance,
            concurrent_session_strategy=policy.concurrent_session_strategy,
            max_auth_failures=policy.max_auth_failures,
            auth_failure_lockout_duration=policy.auth_failure_lockout_duration
        )
        
        # 保存到数据库
        success = policy_manager.update_policy(policy_model, updated_by=user)
        
        db_conn.close()
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="保存安全策略到数据库失败"
            )
        
        return SecurityPolicyResponse(
            policy=policy,
            message="安全策略更新成功并已持久化，立即生效"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新安全策略失败: {str(e)}"
        )
