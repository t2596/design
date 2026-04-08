# Web 管理平台 API

基于 FastAPI 的车联网安全通信网关 Web 管理平台后端 API。

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务器

```bash
python examples/run_api_server.py
```

或直接运行：

```bash
uvicorn src.api.main:app --reload
```

### 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 车辆管理 (`/api/vehicles`)

- `GET /api/vehicles/online` - 获取在线车辆列表
- `GET /api/vehicles/{vehicle_id}/status` - 获取车辆状态
- `GET /api/vehicles/search` - 搜索车辆

### 安全指标 (`/api/metrics`)

- `GET /api/metrics/realtime` - 获取实时安全指标
- `GET /api/metrics/history` - 获取历史安全指标

### 证书管理 (`/api/certificates`)

- `GET /api/certificates` - 获取证书列表
- `POST /api/certificates/issue` - 颁发新证书
- `POST /api/certificates/revoke` - 撤销证书
- `GET /api/certificates/crl` - 获取证书撤销列表

### 审计日志 (`/api/audit`)

- `GET /api/audit/logs` - 查询审计日志
- `GET /api/audit/export` - 导出审计报告

### 配置管理 (`/api/config`)

- `GET /api/config/security` - 获取安全策略
- `PUT /api/config/security` - 更新安全策略

## 认证

所有 API 端点都需要 Bearer Token 认证：

```bash
curl -H "Authorization: Bearer your-token-here" http://localhost:8000/api/vehicles/online
```

默认开发令牌: `dev-token-12345`

## 环境变量

在 `.env` 文件中配置：

```bash
API_TOKEN=your-secure-token
CA_PRIVATE_KEY=your-ca-private-key-hex
CA_PUBLIC_KEY=your-ca-public-key-hex
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=vehicle_iot_security
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 测试

```bash
pytest tests/test_api.py -v
```

## 项目结构

```
src/api/
├── __init__.py
├── main.py              # FastAPI 应用主文件
├── README.md            # 本文件
└── routes/              # API 路由模块
    ├── __init__.py
    ├── vehicles.py      # 车辆管理 API
    ├── metrics.py       # 安全指标 API
    ├── certificates.py  # 证书管理 API
    ├── audit.py         # 审计日志 API
    └── config.py        # 配置管理 API
```

## 更多信息

详细实现文档请参考: `docs/task_13_implementation_summary.md`
