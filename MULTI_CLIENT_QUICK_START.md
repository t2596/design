# 多客户端快速启动指南

## 🚀 快速开始

### 最简单的方式（推荐）

```bash
cd client
python3 run_clients.py --num 5
```

就这么简单！这会启动5个客户端连接到云端Gateway（8.160.179.59:32677）。

## 📋 常用命令

### 启动客户端

```bash
# 启动3个客户端（默认）
python3 run_clients.py

# 启动10个客户端
python3 run_clients.py --num 10

# 启动5个客户端，每5秒发送一次
python3 run_clients.py --num 5 --interval 5

# 指定不同的Gateway地址
python3 run_clients.py --num 3 --gateway 192.168.1.100 --port 8000
```

### 管理客户端

```bash
# 查看状态
python3 run_clients.py --status

# 查看日志
python3 run_clients.py --logs 1

# 停止所有
python3 run_clients.py --stop

# 删除所有
python3 run_clients.py --remove
```

## 🎯 使用场景

### 场景1：功能测试

启动少量客户端测试功能：

```bash
python3 run_clients.py --num 3 --interval 10
```

### 场景2：压力测试

启动大量客户端进行压力测试：

```bash
python3 run_clients.py --num 50 --interval 5
```

### 场景3：演示

启动客户端进行演示，只发送一次数据：

```bash
python3 run_clients.py --num 5 --mode once
```

## 📊 监控

### 查看客户端状态

```bash
python3 run_clients.py --status
```

输出示例：
```
📊 客户端状态:

NAMES              STATUS              PORTS
vehicle-client-1   Up 2 minutes        
vehicle-client-2   Up 2 minutes        
vehicle-client-3   Up 2 minutes        

运行中的客户端: 3
```

### 查看Gateway审计日志

```bash
curl -X GET "http://8.160.179.59:32677/api/audit/logs?limit=10" \
  -H "Authorization: Bearer dev-token-12345"
```

### 查看实时指标

```bash
curl -X GET "http://8.160.179.59:32677/api/metrics/realtime" \
  -H "Authorization: Bearer dev-token-12345"
```

## 🔧 配置说明

### 默认配置

| 参数 | 默认值 | 说明 |
|-----|--------|------|
| Gateway地址 | 8.160.179.59 | 你的云端Gateway IP |
| Gateway端口 | 32677 | Gateway的NodePort |
| 客户端数量 | 3 | 启动的客户端数量 |
| 发送间隔 | 10秒 | 数据发送间隔 |
| 运行模式 | continuous | 持续发送数据 |

### 修改配置

在 `run_clients.py` 文件开头修改默认值：

```python
DEFAULT_GATEWAY_HOST = "8.160.179.59"  # 修改为你的Gateway地址
DEFAULT_GATEWAY_PORT = "32677"         # 修改为你的Gateway端口
DEFAULT_NUM_CLIENTS = 3                # 默认客户端数量
DEFAULT_INTERVAL = 10                  # 默认发送间隔
```

## 🐛 故障排除

### 问题1：无法连接到Gateway

```bash
# 测试Gateway连接
curl http://8.160.179.59:32677/health

# 如果失败，检查Gateway是否运行
kubectl get pods -n vehicle-iot-gateway -l app=gateway
```

### 问题2：客户端启动失败

```bash
# 查看容器日志
docker logs vehicle-client-1

# 重新构建镜像
python3 run_clients.py --rebuild
```

### 问题3：找不到Python

使用Bash脚本代替：

```bash
chmod +x run-multiple-clients.sh
bash run-multiple-clients.sh 5
```

## 📚 更多信息

详细文档请查看：
- `client/MULTI_CLIENT_GUIDE.md` - 完整使用指南
- `client/README.md` - 客户端说明

## 💡 提示

1. **首次使用**需要构建Docker镜像，可能需要几分钟
2. **推荐使用Python脚本**，功能更完整
3. **查看日志**可以了解客户端的运行状态
4. **压力测试**时注意Gateway的资源使用情况

## 🎉 完成

现在你可以轻松启动多个客户端进行测试了！

```bash
cd client
python3 run_clients.py --num 10
```

祝测试顺利！🚗💨
