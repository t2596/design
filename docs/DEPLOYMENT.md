# 部署指南

## 系统要求

### 硬件要求
- CPU: 4 核心或以上
- 内存: 8GB 或以上
- 磁盘: 50GB 或以上（SSD 推荐）

### 软件要求
- Python 3.8 或以上
- PostgreSQL 12 或以上
- Redis 6 或以上
- Docker 20.10 或以上（可选）
- Kubernetes 1.20 或以上（可选）

## 部署方式

### 方式 1: Docker Compose 部署（推荐）

#### 1. 准备环境

```bash
# 克隆项目
git clone <repository-url>
cd vehicle-iot-security-gateway

# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，配置密码和密钥路径
nano .env
```

#### 2. 准备 CA 密钥

```bash
# 创建密钥目录
mkdir -p keys

# 生成 CA 密钥对（使用 GmSSL）
# 注意：生产环境应使用 HSM 或安全密钥管理服务
gmssl sm2keygen -pass 1234567890 -out keys/ca_private.pem -pubout keys/ca_public.pem
```

#### 3. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f gateway
```

#### 4. 验证部署

```bash
# 检查 API 健康状态
curl http://localhost:8000/health

# 访问 API 文档
open http://localhost:8000/docs
```

#### 5. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

### 方式 2: 本地部署

#### 1. 安装依赖

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

#### 2. 配置数据库

```bash
# 安装 PostgreSQL
# Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib

# 创建数据库用户
sudo -u postgres createuser gateway_user -P

# 创建数据库
sudo -u postgres createdb vehicle_iot_gateway -O gateway_user

# 执行初始化脚本
python scripts/init_database.py
```

#### 3. 配置 Redis

```bash
# 安装 Redis
# Ubuntu/Debian:
sudo apt-get install redis-server

# 启动 Redis
sudo systemctl start redis-server

# 配置密码（编辑 /etc/redis/redis.conf）
sudo nano /etc/redis/redis.conf
# 添加: requirepass your_redis_password

# 重启 Redis
sudo systemctl restart redis-server
```

#### 4. 配置环境变量

```bash
# 编辑 .env 文件
nano .env

# 配置数据库连接
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=vehicle_iot_gateway
POSTGRES_USER=gateway_user
POSTGRES_PASSWORD=your_password

# 配置 Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# 配置 CA 密钥路径
CA_PRIVATE_KEY_PATH=./keys/ca_private.pem
```

#### 5. 启动服务

```bash
# 启动 API 服务
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式 3: Kubernetes 部署

详见 `deployment/kubernetes/README.md`

## 环境变量配置

### 数据库配置
- `POSTGRES_HOST`: PostgreSQL 主机地址（默认: localhost）
- `POSTGRES_PORT`: PostgreSQL 端口（默认: 5432）
- `POSTGRES_DB`: 数据库名称（默认: vehicle_iot_gateway）
- `POSTGRES_USER`: 数据库用户名
- `POSTGRES_PASSWORD`: 数据库密码

### Redis 配置
- `REDIS_HOST`: Redis 主机地址（默认: localhost）
- `REDIS_PORT`: Redis 端口（默认: 6379）
- `REDIS_PASSWORD`: Redis 密码

### 安全配置
- `CA_PRIVATE_KEY_PATH`: CA 私钥文件路径
- `SESSION_TIMEOUT`: 会话超时时间（秒，默认: 3600）
- `TIMESTAMP_TOLERANCE`: 时间戳容差（秒，默认: 300）

### 性能配置
- `CACHE_SIZE`: 证书缓存大小（默认: 10000）
- `CACHE_TTL`: 缓存过期时间（秒，默认: 300）

### API 配置
- `API_PORT`: API 服务端口（默认: 8000）
- `API_WORKERS`: API 工作进程数（默认: 4）

## 安全注意事项

### CA 私钥管理

**开发环境**:
- 使用本地文件存储 CA 私钥
- 确保文件权限为 600（仅所有者可读写）

**生产环境**:
- 使用硬件安全模块（HSM）存储 CA 私钥
- 或使用云密钥管理服务（如 AWS KMS、Azure Key Vault）
- 启用密钥轮换机制
- 配置密钥访问审计

### 数据库安全

- 使用强密码（至少 16 字符，包含大小写字母、数字和特殊字符）
- 启用 SSL/TLS 连接
- 限制数据库访问 IP 白名单
- 定期备份数据库
- 启用数据库审计日志

### Redis 安全

- 配置 requirepass 密码认证
- 禁用危险命令（FLUSHDB、FLUSHALL、CONFIG）
- 绑定到内网 IP，不暴露到公网
- 启用 AOF 持久化（生产环境）

### 网络安全

- 使用防火墙限制端口访问
- 启用 HTTPS/TLS 加密传输
- 配置 API 访问限流
- 部署 WAF（Web 应用防火墙）

## 监控与日志

### 日志位置
- 应用日志: `./logs/gateway.log`
- 审计日志: PostgreSQL `audit_logs` 表
- 系统日志: Docker logs 或 Kubernetes logs

### 监控指标
- 认证成功率
- 认证失败次数
- 数据传输量
- 签名验证失败次数
- 会话数量
- 缓存命中率

### 告警配置
- 认证失败率超过 10%
- 检测到重放攻击
- 证书即将过期（30 天内）
- 数据库连接失败
- Redis 连接失败

## 备份与恢复

### PostgreSQL 备份

```bash
# 备份数据库
pg_dump -U gateway_user -d vehicle_iot_gateway -F c -f backup_$(date +%Y%m%d).dump

# 恢复数据库
pg_restore -U gateway_user -d vehicle_iot_gateway backup_20260321.dump
```

### Redis 备份

```bash
# 触发 RDB 快照
redis-cli -a your_password SAVE

# 备份 RDB 文件
cp /var/lib/redis/dump.rdb backup_$(date +%Y%m%d).rdb
```

## 性能调优

### PostgreSQL 优化
- 调整 `shared_buffers`（推荐: 25% 系统内存）
- 调整 `work_mem`（推荐: 64MB）
- 启用查询计划缓存
- 定期执行 VACUUM 和 ANALYZE

### Redis 优化
- 配置 `maxmemory` 和 `maxmemory-policy`
- 使用连接池减少连接开销
- 启用 Pipeline 批量操作
- 监控慢查询日志

### 应用优化
- 启用证书验证缓存
- 使用连接池管理数据库连接
- 配置合理的工作进程数
- 启用 gzip 压缩

## 故障排查

详见 `docs/TROUBLESHOOTING.md`
