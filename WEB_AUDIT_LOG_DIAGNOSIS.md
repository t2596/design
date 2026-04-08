# Web端审计日志查询失效问题诊断

## 问题描述

用户反馈：修复完成后，Web端审计日志查询仍然不工作。

## 可能的原因

### 1. 数据库中没有审计日志数据

虽然代码中已经添加了审计日志记录，但可能：
- Gateway Pod没有重启，仍在运行旧代码
- 没有触发过会生成审计日志的操作
- 审计日志记录失败但没有报错

### 2. Web前端API调用问题

可能的问题：
- API路径不正确
- Authorization header缺失或错误
- Nginx代理配置问题
- CORS问题

### 3. Gateway API问题

可能的问题：
- 路由没有正确注册
- 数据库连接失败
- 查询逻辑错误

## 诊断步骤

### 步骤1：运行诊断脚本

```bash
bash diagnose_web_audit_issue.sh
```

这个脚本会：
1. 检查Pod状态
2. 检查数据库中的审计日志
3. 测试Gateway API
4. 测试Web代理
5. 生成测试数据
6. 查看日志

### 步骤2：检查数据库

```bash
# 连接到PostgreSQL
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway

# 查询审计日志数量
SELECT COUNT(*) FROM audit_logs;

# 查看最近的审计日志
SELECT event_type, vehicle_id, operation_result, timestamp, details 
FROM audit_logs 
ORDER BY timestamp DESC 
LIMIT 10;

# 退出
\q
```

### 步骤3：测试Gateway API

```bash
# 直接测试Gateway API
curl -X GET "http://8.147.67.31:32620/api/audit/logs" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" | jq '.'
```

### 步骤4：测试Web代理

```bash
# 通过Web服务测试
curl -X GET "http://8.147.67.31:32621/api/audit/logs" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" | jq '.'
```

### 步骤5：浏览器测试

1. 打开浏览器访问 `http://8.147.67.31:32621`
2. 打开开发者工具（F12）
3. 切换到 Network 标签
4. 访问审计日志页面
5. 查看 `/api/audit/logs` 请求
6. 检查：
   - 请求URL
   - 请求Headers（特别是Authorization）
   - 响应状态码
   - 响应内容

## 常见问题和解决方案

### 问题1：数据库中没有审计日志

**症状：**
```sql
SELECT COUNT(*) FROM audit_logs;
-- 返回 0 或很少的记录
```

**原因：**
- Gateway Pod没有重启，仍在运行旧代码
- 没有触发过会生成审计日志的操作

**解决方案：**

```bash
# 1. 重启Gateway Pod
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 2. 等待Pod就绪
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s

# 3. 生成测试数据
curl -X POST "http://8.147.67.31:32620/api/auth/register" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "TEST-VEHICLE-001",
    "certificate_serial": "TEST-CERT-001"
  }'

# 4. 再次检查数据库
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) FROM audit_logs;"
```

### 问题2：Gateway API返回空数组

**症状：**
```json
{
  "total": 0,
  "logs": []
}
```

**原因：**
- 数据库中确实没有数据
- 查询条件过滤掉了所有记录

**解决方案：**

```bash
# 不带任何过滤条件查询
curl -X GET "http://8.147.67.31:32620/api/audit/logs?limit=100" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" | jq '.'
```

### 问题3：Gateway API返回401/403

**症状：**
```json
{
  "detail": "Unauthorized"
}
```

**原因：**
- Authorization header缺失或错误
- Token验证失败

**解决方案：**

检查Web前端的API客户端配置：

```javascript
// web/src/api/client.js
const API_TOKEN = import.meta.env.VITE_API_TOKEN || 'dev-token-12345';
```

确保环境变量正确设置。

### 问题4：Web代理返回404

**症状：**
```
404 Not Found
```

**原因：**
- Nginx配置错误
- Gateway服务不可达

**解决方案：**

```bash
# 1. 检查Nginx配置
kubectl exec -it deployment/web -n vehicle-iot-gateway -- \
  cat /etc/nginx/conf.d/default.conf

# 2. 检查Gateway服务
kubectl get svc gateway-service -n vehicle-iot-gateway

# 3. 测试从Web Pod到Gateway的连接
kubectl exec -it deployment/web -n vehicle-iot-gateway -- \
  wget -O- http://gateway-service:8000/health
```

### 问题5：CORS错误

**症状：**
浏览器控制台显示：
```
Access to XMLHttpRequest at 'http://...' from origin 'http://...' has been blocked by CORS policy
```

**原因：**
- Gateway没有正确配置CORS

**解决方案：**

检查Gateway的CORS配置（在 `src/api/main.py`）：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 问题6：Web前端显示"暂无日志记录"

**症状：**
- API返回200
- 但前端显示"暂无日志记录"

**原因：**
- API返回的数据格式不匹配
- 前端解析错误

**解决方案：**

1. 在浏览器控制台查看实际的API响应：

```javascript
// 在浏览器控制台执行
fetch('/api/audit/logs', {
  headers: {
    'Authorization': 'Bearer dev-token-12345',
    'Content-Type': 'application/json'
  }
})
.then(r => r.json())
.then(data => console.log(data))
```

2. 检查响应格式是否为：

```json
{
  "total": 10,
  "logs": [
    {
      "log_id": "...",
      "timestamp": "...",
      "event_type": "...",
      "vehicle_id": "...",
      "operation_result": true,
      "details": "...",
      "ip_address": "..."
    }
  ]
}
```

## 快速修复流程

如果上述诊断发现问题，按以下步骤修复：

### 修复1：重新部署Gateway（确保使用最新代码）

```bash
# 1. 重新构建镜像
docker build -t your-username/vehicle-iot-gateway:v1.1 .
docker push your-username/vehicle-iot-gateway:v1.1

# 2. 更新K8s配置
# 编辑 deployment/kubernetes/gateway-deployment.yaml
# 修改镜像版本为 v1.1

# 3. 应用更新
kubectl apply -f deployment/kubernetes/gateway-deployment.yaml

# 4. 等待Pod就绪
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s
```

### 修复2：生成测试数据

```bash
# 运行测试脚本生成审计日志
bash test_audit_api_direct.sh
```

### 修复3：验证修复

```bash
# 1. 检查数据库
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) FROM audit_logs;"

# 2. 测试API
curl -X GET "http://8.147.67.31:32620/api/audit/logs" \
  -H "Authorization: Bearer dev-token-12345" | jq '.total'

# 3. 浏览器测试
# 访问 http://8.147.67.31:32621
# 进入审计日志页面
# 应该能看到日志记录
```

## 检查清单

使用以下清单确认所有组件正常：

- [ ] Gateway Pod运行正常
- [ ] Web Pod运行正常
- [ ] PostgreSQL Pod运行正常
- [ ] 数据库中有audit_logs表
- [ ] 数据库中有审计日志数据
- [ ] Gateway API `/api/audit/logs` 返回200
- [ ] Gateway API返回的数据格式正确
- [ ] Web代理 `/api/audit/logs` 返回200
- [ ] 浏览器可以访问Web界面
- [ ] 浏览器Network标签显示API请求成功
- [ ] Web界面显示审计日志列表

## 联系支持

如果以上步骤都无法解决问题，请提供以下信息：

1. 诊断脚本的完整输出
2. Gateway Pod日志
3. Web Pod日志
4. 浏览器控制台的错误信息
5. 浏览器Network标签的请求详情

```bash
# 收集诊断信息
bash diagnose_web_audit_issue.sh > diagnosis_output.txt 2>&1
kubectl logs deployment/gateway -n vehicle-iot-gateway > gateway_logs.txt
kubectl logs deployment/web -n vehicle-iot-gateway > web_logs.txt
```

## 总结

Web端审计日志查询失效的最常见原因是：

1. **Gateway Pod没有重启** - 仍在运行旧代码
2. **数据库中没有数据** - 没有触发过审计日志记录
3. **API路径或认证问题** - 前端配置错误

按照本文档的诊断步骤，可以快速定位和解决问题。
