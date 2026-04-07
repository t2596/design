# 车联网安全通信网关 Web 管理平台

基于 React 的 Web 管理平台前端应用，用于监控和管理车联网安全通信网关系统。

## 功能特性

### 1. 车辆状态监控
- 实时显示在线车辆列表
- 查看车辆详细状态信息
- 车辆搜索功能
- 自动刷新（每5秒）

### 2. 安全指标可视化
- 实时安全指标仪表盘
  - 在线车辆数
  - 认证成功率
  - 认证失败次数
  - 数据传输量
  - 签名失败次数
  - 安全异常次数
- 历史指标趋势图表
- 支持多种时间范围（1小时、6小时、24小时、7天）

### 3. 证书管理
- 证书列表查看
- 证书颁发功能
- 证书撤销功能
- CRL（证书撤销列表）查看
- 按状态过滤（有效、已过期、已撤销）

### 4. 审计日志查询
- 多条件过滤查询
  - 时间范围
  - 车辆标识
  - 事件类型
  - 操作结果
- 日志导出（JSON/CSV格式）

### 5. 安全策略配置
- 会话超时时间配置
- 证书有效期配置
- 时间戳容差配置
- 并发会话策略配置
- 认证失败处理配置

## 技术栈

- **React 18** - UI 框架
- **React Router 6** - 路由管理
- **Axios** - HTTP 客户端
- **Recharts** - 图表库
- **Vite** - 构建工具

## 安装与运行

### 前置要求

- Node.js >= 16
- npm 或 yarn

### 安装依赖

```bash
cd web
npm install
```

### 配置环境变量

创建 `.env` 文件：

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TOKEN=dev-token-12345
```

### 开发模式

```bash
npm run dev
```

应用将在 http://localhost:3000 启动

### 生产构建

```bash
npm run build
```

构建产物将输出到 `dist` 目录

### 预览生产构建

```bash
npm run preview
```

## 项目结构

```
web/
├── src/
│   ├── api/              # API 客户端
│   │   ├── client.js     # Axios 配置
│   │   ├── vehicles.js   # 车辆 API
│   │   ├── metrics.js    # 指标 API
│   │   ├── certificates.js # 证书 API
│   │   ├── audit.js      # 审计 API
│   │   └── config.js     # 配置 API
│   ├── pages/            # 页面组件
│   │   ├── VehicleMonitor.jsx
│   │   ├── MetricsDashboard.jsx
│   │   ├── CertificateManagement.jsx
│   │   ├── AuditLogs.jsx
│   │   └── SecurityConfig.jsx
│   ├── App.jsx           # 主应用组件
│   ├── App.css           # 应用样式
│   ├── main.jsx          # 入口文件
│   └── index.css         # 全局样式
├── index.html            # HTML 模板
├── vite.config.js        # Vite 配置
└── package.json          # 项目配置
```

## API 集成

前端通过 Axios 与后端 FastAPI 服务通信。所有 API 请求都包含 Bearer Token 认证。

### API 端点

- `GET /api/vehicles/online` - 获取在线车辆
- `GET /api/vehicles/{id}/status` - 获取车辆状态
- `GET /api/vehicles/search` - 搜索车辆
- `GET /api/metrics/realtime` - 获取实时指标
- `GET /api/metrics/history` - 获取历史指标
- `GET /api/certificates` - 获取证书列表
- `POST /api/certificates/issue` - 颁发证书
- `POST /api/certificates/revoke` - 撤销证书
- `GET /api/certificates/crl` - 获取 CRL
- `GET /api/audit/logs` - 查询审计日志
- `GET /api/audit/export` - 导出审计报告
- `GET /api/config/security` - 获取安全策略
- `PUT /api/config/security` - 更新安全策略

## 验证需求

本前端应用实现了以下需求：

- **需求 13.1-13.5**: 实时车辆状态监控
- **需求 14.1-14.6**: 安全指标可视化
- **需求 15.1-15.6**: 证书管理界面
- **需求 12.1-12.5**: 审计日志查询
- **需求 16.1-16.6**: 安全策略配置

## 浏览器支持

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

## 开发说明

### 添加新页面

1. 在 `src/pages/` 创建新组件
2. 在 `src/App.jsx` 添加路由
3. 在导航菜单添加链接

### 添加新 API

1. 在 `src/api/` 创建新的 API 模块
2. 使用 `apiClient` 发起请求
3. 在页面组件中导入使用

## 许可证

本项目为车联网安全通信网关系统的一部分。
