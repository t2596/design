# 快速启动多客户端

## 方法1：使用Python脚本（最简单）

```bash
cd client
python3 run_clients.py --num 10
```

## 方法2：使用Docker Compose

### 步骤1：构建镜像

```bash
cd client
docker build -f Dockerfile -t vehicle-client:latest ..
```

### 步骤2：启动客户端

```bash
# 启动1个客户端
docker compose -f docker-compose-cloud.yml up -d

# 启动10个客户端
docker compose -f docker-compose-cloud.yml up -d --scale vehicle-client=10
```

### 步骤3：查看状态

```bash
# 查看运行中的容器
docker compose -f docker-compose-cloud.yml ps

# 查看日志
docker compose -f docker-compose-cloud.yml logs -f
```

### 步骤4：停止客户端

```bash
docker compose -f docker-compose-cloud.yml down
```

## 方法3：使用Bash脚本

```bash
cd client
chmod +x run-multiple-clients.sh
bash run-multiple-clients.sh 10
```

## 常见问题

### Q: 提示找不到镜像

**错误信息：**
```
Error response from daemon: No such image: client-vehicle-client:latest
```

**解决方案：**
先构建镜像：
```bash
cd client
docker build -f Dockerfile -t vehicle-client:latest ..
```

### Q: 如何修改Gateway地址

编辑 `docker-compose-cloud.yml`：
```yaml
environment:
  - GATEWAY_HOST=你的IP地址
  - GATEWAY_PORT=你的端口
```

### Q: 如何查看客户端日志

```bash
# 使用Docker Compose
docker compose -f docker-compose-cloud.yml logs -f vehicle-client

# 或直接使用Docker
docker logs -f client-vehicle-client-1
```

## 推荐方式

**最简单：** 使用Python脚本
```bash
python3 run_clients.py --num 10
```

**最灵活：** 使用Docker Compose
```bash
docker compose -f docker-compose-cloud.yml up -d --scale vehicle-client=10
```
