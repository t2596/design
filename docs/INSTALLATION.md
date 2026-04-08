# 安装指南

## 前置要求

### 系统要求
- 操作系统: Linux (Ubuntu 20.04+), macOS, Windows 10+
- Python: 3.8 或以上
- 内存: 至少 4GB
- 磁盘空间: 至少 10GB

### 依赖软件
- PostgreSQL 12+
- Redis 6+
- Docker 20.10+ (可选)
- Git

## 快速安装（Docker Compose）

### 1. 克隆项目

```bash
git clone <repository-url>
cd vehicle-iot-security-gateway
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，设置密码和配置
```

### 3. 生成 CA 密钥

```bash
mkdir -p keys
# 使用 GmSSL 生成密钥对
gmssl sm2keygen -pass 1234567890 -out keys/ca_private.pem -pubout keys/ca_public.pem
```

### 4. 启动服务

```bash
docker-compose up -d
```

### 5. 验证安装

```bash
# 检查服务状态
docker-compose ps

# 测试 API
curl http://localhost:8000/health
```

## 手动安装

### 1. 安装 Python 依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 安装 PostgreSQL

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

#### macOS
```bash
brew install postgresql
brew services start postgresql
```

#### Windows
下载并安装 PostgreSQL: https://www.postgresql.org/download/windows/

### 3. 安装 Redis

#### Ubuntu/Debian
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

#### macOS
```bash
brew install redis
brew services start redis
```

#### Windows
下载并安装 Redis: https://github.com/microsoftarchive/redis/releases

### 4. 初始化数据库

```bash
# 创建数据库用户
sudo -u postgres createuser gateway_user -P

# 创建数据库
sudo -u postgres createdb vehicle_iot_gateway -O gateway_user

# 执行初始化脚本
python scripts/init_database.py
```

### 5. 配置环境变量

编辑 `.env` 文件：

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=vehicle_iot_gateway
POSTGRES_USER=gateway_user
POSTGRES_PASSWORD=your_secure_password

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

CA_PRIVATE_KEY_PATH=./keys/ca_private.pem
SESSION_TIMEOUT=3600
TIMESTAMP_TOLERANCE=300
```

### 6. 启动服务

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

## 验证安装

### 1. 检查 API 服务

```bash
curl http://localhost:8000/health
```

预期响应:
```json
{"status": "healthy"}
```

### 2. 访问 API 文档

打开浏览器访问: http://localhost:8000/docs

### 3. 运行测试

```bash
pytest tests/ -v
```

## 下一步

- 阅读 [部署指南](DEPLOYMENT.md)
- 阅读 [运维手册](OPERATIONS.md)
- 阅读 [API 文档](API.md)
