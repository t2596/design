# 车联网安全通信网关系统

基于国密算法（SM2/SM4）的车联网安全通信网关系统，提供证书管理、身份认证、加密签名和审计日志功能。

## 项目结构

```
.
├── config/                 # 配置模块
│   ├── __init__.py
│   └── database.py        # 数据库配置
├── db/                    # 数据库脚本
│   └── schema.sql         # PostgreSQL 表结构
├── src/                   # 源代码
│   ├── __init__.py
│   ├── db/               # 数据库连接
│   │   ├── __init__.py
│   │   ├── postgres.py   # PostgreSQL 连接
│   │   └── redis_client.py # Redis 连接
│   └── models/           # 数据模型
│       ├── __init__.py
│       ├── audit.py      # 审计日志模型
│       ├── certificate.py # 证书模型
│       ├── enums.py      # 枚举类型
│       ├── message.py    # 安全报文模型
│       └── session.py    # 会话模型
├── .env.example          # 环境变量示例
├── requirements.txt      # Python 依赖
└── README.md            # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，配置数据库连接信息
```

### 3. 初始化数据库

```bash
# 创建 PostgreSQL 数据库
createdb vehicle_iot_gateway

# 执行数据库架构脚本
psql -d vehicle_iot_gateway -f db/schema.sql
```

### 4. 启动 Redis

```bash
# 使用 Docker 启动 Redis
docker run -d -p 6379:6379 redis:latest
```

## 核心功能

### 证书管理
- 国密 SM2 证书颁发
- 证书验证（有效期、签名、撤销状态）
- 证书撤销列表（CRL）管理

### 身份认证
- 车云双向身份认证
- 基于 SM2 的挑战-响应认证
- 会话管理（Redis 存储）

### 加密签名
- SM4 对称加密/解密
- SM2 数字签名/验签
- 安全报文构造与验证

### 审计日志
- 认证事件记录
- 数据传输日志
- 证书操作审计
- 安全异常告警

## 数据模型

### Certificate（证书）
- 版本、序列号、颁发者、主体
- 有效期（valid_from, valid_to）
- SM2 公钥和签名

### SessionInfo（会话信息）
- 会话 ID（32 字节）
- SM4 会话密钥
- 过期时间和状态

### SecureMessage（安全报文）
- 消息头（发送方、接收方）
- SM4 加密的业务数据
- SM2 签名
- 时间戳和 nonce（防重放）

### AuditLog（审计日志）
- 事件类型、车辆 ID
- 操作结果、详细信息
- 时间戳、IP 地址

## 技术栈

- **Python 3.8+**: 核心实现语言
- **GmSSL**: 国密算法库（SM2/SM4）
- **PostgreSQL**: 证书和审计日志存储
- **Redis**: 会话管理和缓存
- **FastAPI**: Web API 框架
- **pytest + Hypothesis**: 测试框架

## 安全特性

- ✅ 国密算法（SM2/SM4）
- ✅ 双向身份认证
- ✅ 端到端加密
- ✅ 数字签名验证
- ✅ 防重放攻击（时间戳 + nonce）
- ✅ 证书撤销机制
- ✅ 审计日志追溯

## 开发计划

详见 `.kiro/specs/vehicle-iot-security-gateway/tasks.md`

## 许可证

本项目遵循相关开源许可证。
