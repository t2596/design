# 快速启动指南

本指南帮助您快速启动车联网安全通信网关 Web 管理平台。

## 前置条件

### 后端服务

确保后端 API 服务已启动：

```bash
# 在项目根目录
python examples/run_api_server.py
```

后端服务将在 http://localhost:8000 启动

### Node.js 环境

- Node.js >= 16
- npm 或 yarn

## 安装步骤

### 1. 安装依赖

```bash
cd web
npm install
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件（如果需要）：

```
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TOKEN=dev-token-12345
```

### 3. 启动开发服务器

```bash
npm run dev
```

应用将在 http://localhost:3000 启动

## 访问应用

打开浏览器访问：http://localhost:3000

### 功能页面

- **车辆监控**: http://localhost:3000/
- **安全指标**: http://localhost:3000/metrics
- **证书管理**: http://localhost:3000/certificates
- **审计日志**: http://localhost:3000/audit
- **安全配置**: http://localhost:3000/config

## 测试功能

### 1. 查看在线车辆

1. 访问首页（车辆监控）
2. 查看在线车辆列表
3. 使用搜索框搜索特定车辆

### 2. 查看安全指标

1. 访问"安全指标"页面
2. 查看实时指标仪表盘
3. 选择不同时间范围查看历史趋势

### 3. 管理证书

1. 访问"证书管理"页面
2. 点击"颁发证书"按钮
3. 填写车辆信息并提交
4. 查看证书列表
5. 点击"查看CRL"查看撤销列表

### 4. 查询审计日志

1. 访问"审计日志"页面
2. 设置过滤条件（时间范围、车辆ID等）
3. 点击"查询"按钮
4. 点击"导出JSON"或"导出CSV"导出日志

### 5. 配置安全策略

1. 访问"安全配置"页面
2. 修改安全参数
3. 点击"保存配置"按钮

## 常见问题

### Q: 页面显示"错误: Network Error"

**A:** 检查后端 API 服务是否正常运行：
```bash
curl http://localhost:8000/health
```

### Q: 页面显示"错误: 401 Unauthorized"

**A:** 检查 `.env` 文件中的 `VITE_API_TOKEN` 是否与后端配置一致。

### Q: 数据不更新

**A:** 页面会每5秒自动刷新数据。如果数据仍不更新，请检查：
1. 后端服务是否正常
2. 浏览器控制台是否有错误
3. 网络连接是否正常

### Q: 图表不显示

**A:** 确保：
1. 有历史数据（运行一段时间后）
2. 选择的时间范围内有数据
3. 浏览器支持 SVG

## 生产部署

### 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录

### 使用 Nginx 部署

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /path/to/web/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 使用 Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

构建并运行：

```bash
docker build -t vehicle-iot-web .
docker run -p 80:80 vehicle-iot-web
```

## 开发建议

### 热重载

开发模式下，修改代码会自动重载页面。

### 调试

使用浏览器开发者工具：
- **Console**: 查看日志和错误
- **Network**: 查看 API 请求
- **React DevTools**: 查看组件状态

### 代码格式化

建议安装 Prettier 和 ESLint：

```bash
npm install --save-dev prettier eslint
```

## 获取帮助

- 查看 `README.md` 了解详细文档
- 查看 `docs/task_14_implementation_summary.md` 了解实现细节
- 检查浏览器控制台的错误信息
- 检查后端 API 日志

## 下一步

- 探索所有功能页面
- 尝试不同的过滤和搜索选项
- 查看实时数据更新
- 导出审计报告
- 配置安全策略

祝您使用愉快！
