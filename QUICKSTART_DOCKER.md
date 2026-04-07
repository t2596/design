# Docker 快速启动指南

本指南帮助你快速使用 Docker 启动完整的车联网安全通信网关系统。

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+

## 快速启动

### 1. 启动网关服务

```bash
# 启动网关、数据库和 Redis
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看网关日志
docker-compose logs -f gateway
```

### 2. 初始化数据库

```bash
# 等待数据库启动（约 10 秒）
sleep 10

# 初始化数据库（如果需要）
docker-compose exec gateway python scripts/init_database.py
```

### 3. 验证网关运行

```bash
# 检查健康状态
curl http://localhost:8000/health

# 预期输出：{"status":"healthy"}
```

### 4. 启动车辆客户端

```bash
# 进入客户端目录
cd client

# 启动 3 个车辆客户端
docker-compose up -d

# 查看客户端日志
docker-compose logs -f vehicle-client-1
```

## 系统架构

启动后的系统包含以下服务：

```
┌─────────────────────────────────────────────┐
│  车辆客户端 (vehicle-client-1/2/3)          │
│  - 模拟车辆终端设备                         │
│  - 定期发送传感器数据                       │
└──────────────┬──────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────┐
│  安全通信网关 (gateway)                     │
│  - 证书管理                                 │
│  - 双向认证                                 │
│  - 安全数据传输                             │
│  - 审计日志                                 │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┐
       ↓               ↓
┌─────────────┐ ┌─────────────┐
│ PostgreSQL  │ │   Redis     │
│ (数据库)    │ │  (缓存)     │
└─────────────┘ └─────────────┘
```

## 端口映射

| 服务 | 端口 | 说明 |
|------|------|------|
| gateway | 8000 | 网关 API 服务 |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存 |

## 常用命令

### 查看所有服务状态

```bash
# 主服务
docker-compose ps

# 客户端服务
cd client && docker-compose ps
```

### 查看日志

```bash
# 网关日志
docker-compose logs -f gateway

# 客户端日志
cd client && docker-compose logs -f vehicle-client-1

# 所有服务日志
docker-compose logs -f
```

### 重启服务

```bash
# 重启网关
docker-compose restart gateway

# 重启客户端
cd client && docker-compose restart vehicle-client-1
```

### 停止服务

```bash
# 停止网关服务
docker-compose down

# 停止客户端服务
cd client && docker-compose down

# 停止所有服务并删除数据卷
docker-compose down -v
cd client && docker-compose down -v
```

## 扩展客户端数量

编辑 `client/docker-compose.yml`，添加更多客户端：

```yaml
  vehicle-client-4:
    build:
      context: ..
      dockerfile: client/Dockerfile
    container_name: vehicle-client-4
    environment:
      - GATEWAY_HOST=gateway
      - GATEWAY_PORT=8000
      # ... 其他环境变量
    command: ["--vehicle-id", "VIN000004", "--mode", "continuous", "--interval", "25"]
    networks:
      - vehicle-iot-network
    depends_on:
      - gateway
      - postgres
      - redis
    restart: unless-stopped
```

然后重启：

```bash
cd client
docker-compose up -d
```

## 性能监控

### 查看网关性能指标

```bash
# 使用 API 查询性能指标
curl -H "X-API-Key: test-api-key" http://localhost:8000/api/metrics/realtime

# 查看在线车辆
curl -H "X-API-Key: test-api-key" http://localhost:8000/api/vehicles/online
```

### 查看审计日志

```bash
# 查询最近的审计日志
curl -H "X-API-Key: test-api-key" "http://localhost:8000/api/audit/logs?limit=10"
```

## 故障排查

### 网关无法启动

```bash
# 检查数据库是否就绪
docker-compose exec postgres pg_isready -U gateway_user

# 检查 Redis 是否就绪
docker-compose exec redis redis-cli ping
```

### 客户端无法连接网关

```bash
# 检查网络连接
docker network inspect vehicle-iot-network

# 检查网关是否在运行
docker-compose ps gateway

# 查看网关日志
docker-compose logs gateway
```

### 数据库连接失败

```bash
# 检查数据库日志
docker-compose logs postgres

# 手动连接数据库测试
docker-compose exec postgres psql -U gateway_user -d vehicle_iot_gateway
```

## 清理环境

```bash
# 停止所有服务
docker-compose down
cd client && docker-compose down

# 删除所有数据卷
docker-compose down -v
cd client && docker-compose down -v

# 删除镜像
docker rmi vehicle-client:latest
docker rmi vehicle-iot-gateway:latest
```

## 下一步

- 查看 [API 文档](docs/API.md) 了解 API 使用方法
- 查看 [部署文档](docs/DEPLOYMENT.md) 了解生产环境部署
- 查看 [运维文档](docs/OPERATIONS.md) 了解日常运维操作
- 查看 [故障排查](docs/TROUBLESHOOTING.md) 了解常见问题解决方案
