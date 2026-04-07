"""Web 管理平台后端 API

提供 RESTful API 接口用于：
- 车辆状态监控
- 安全指标监控
- 证书管理
- 审计日志查询
- 安全策略配置

验证需求: 13.1, 15.1
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os

# 创建 FastAPI 应用
app = FastAPI(
    title="车联网安全通信网关 API",
    description="基于国密算法的车联网安全通信网关管理平台 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Vehicle IoT Security Team",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT License"
    }
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP Bearer 认证
security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """验证 API 认证令牌
    
    参数:
        credentials: HTTP Bearer 认证凭据
        
    返回:
        str: 用户标识
        
    异常:
        HTTPException: 如果令牌无效
    """
    token = credentials.credentials
    
    # 简化实现：检查环境变量中的 API 密钥
    # 生产环境应该使用更安全的令牌验证机制（如 JWT）
    expected_token = os.getenv("API_TOKEN", "dev-token-12345")
    
    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return "admin"  # 返回用户标识


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "message": "车联网安全通信网关 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


# 导入路由模块
from src.api.routes import vehicles, metrics, certificates, audit, config, auth

# 注册路由
app.include_router(vehicles.router, prefix="/api/vehicles", tags=["车辆管理"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["安全指标"])
app.include_router(certificates.router, prefix="/api/certificates", tags=["证书管理"])
app.include_router(audit.router, prefix="/api/audit", tags=["审计日志"])
app.include_router(config.router, prefix="/api/config", tags=["配置管理"])
app.include_router(auth.router, prefix="/api/auth", tags=["车辆认证"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
