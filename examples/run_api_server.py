"""运行 Web 管理平台 API 服务器

这个脚本启动 FastAPI 服务器，提供 Web 管理平台的后端 API。

使用方法:
    python examples/run_api_server.py

API 文档:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc

环境变量:
    - API_TOKEN: API 认证令牌（默认: dev-token-12345）
    - CA_PRIVATE_KEY: CA 私钥（十六进制）
    - CA_PUBLIC_KEY: CA 公钥（十六进制）
    - POSTGRES_HOST: PostgreSQL 主机
    - POSTGRES_PORT: PostgreSQL 端口
    - POSTGRES_DB: PostgreSQL 数据库名
    - POSTGRES_USER: PostgreSQL 用户名
    - POSTGRES_PASSWORD: PostgreSQL 密码
    - REDIS_HOST: Redis 主机
    - REDIS_PORT: Redis 端口
"""

import os
import sys
import uvicorn

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.main import app


def main():
    """启动 API 服务器"""
    print("=" * 60)
    print("车联网安全通信网关 - Web 管理平台 API")
    print("=" * 60)
    print()
    print("API 服务器启动中...")
    print()
    print("API 文档:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print()
    print("API 端点:")
    print("  - 车辆管理: /api/vehicles")
    print("  - 安全指标: /api/metrics")
    print("  - 证书管理: /api/certificates")
    print("  - 审计日志: /api/audit")
    print("  - 配置管理: /api/config")
    print()
    print("认证:")
    print("  使用 Bearer Token 认证")
    print(f"  默认令牌: {os.getenv('API_TOKEN', 'dev-token-12345')}")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    print()
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
