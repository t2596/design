# Kubernetes 一键部署指南（包含问题2和3修复）

## 🎯 概述

此部署配置已集成问题2和问题3的所有修复，支持一键部署，无需手动执行数据库迁移。

## ✅ 包含的修复

### 问题2：Web端审计日志查询
- ✅ 自动记录审计日志
- ✅ 支持审计日志查询和导出
- ✅ 记录客户端IP地址

### 问题3：Web端安全配置持久化
- ✅ 配置持久化到数据库
- ✅ 支持会话超时控制
- ✅ 支持证书有效期控制
- ✅ 支持认证失败锁定

## 🚀 一键部署

### 全新部署

```bash
cd deployment/kubernetes
bash deploy-all.sh
```

就这么简单！脚本会自动：
1. 创建命名空间
2. 创建ConfigMap和Secrets
3. 部署PostgreSQL（自动创建所有表）
4. 部署Redis
5. 部署Gateway
6. 部署Web界面

### 验证部署

```bash
# 检查Pod状态
kubectl get pods -n vehicle-iot-gateway

# 检查数据库表
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt"

# 应该看到6个表：
# - certificates
# - certificate_revocation_list
# - audit_logs
# - vehicle_data
# - security_policy (新增)
# - auth_failure_records (新增)
```

## 🔄 更新已有环境

如果你已经有一个运行中的环境：

### 快速更新

```bash
# 1. 应用数据库迁移
bash apply_security_policy_migration.sh

# 2. 重新构建和部署
docker build -t vehicle-iot-gateway:latest .
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s

# 3. 验证
bash test_audit_logs_api.sh
bash test_security_config_api.sh
```

## 📊 自动创建的数据库表

### 原有表
1. **certificates** - 证书管理
2. **certificate_revocation_list** - 证书撤销列表
3. **audit_logs** - 审计日志
4. **vehicle_data** - 车辆数据

### 新增表（自动创建）
5. **security_policy** - 安全策略配置
   - 会话超时
   - 证书有效期
   - 时间戳容差
   - 并发会话策略
   - 认证失败阈值
   - 锁定时长

6. **auth_failure_records** - 认证失败记录
   - 车辆ID
   - 失败次数
   - 锁定时间

## 🔧 默认配置

部署时会自动插入默认安全策略：

```yaml
session_timeout: 86400秒 (24小时)
certificate_validity: 365天 (1年)
timestamp_tolerance: 300秒 (5分钟)
concurrent_session_strategy: 'reject_new'
max_auth_failures: 5次
auth_failure_lockout_duration: 300秒 (5分钟)
```

## 🧪 测试验证

### 测试审计日志功能

```bash
# 生成测试数据
python3 generate_audit_test_data.py

# 测试API
bash test_audit_logs_api.sh

# 检查数据库
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT COUNT(*) FROM audit_logs;"
```

### 测试安全配置功能

```bash
# 测试配置API
bash test_security_config_api.sh

# 获取配置
curl -X GET "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" | jq '.'

# 更新配置
curl -X PUT "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 7200,
    "certificate_validity": 180,
    "timestamp_tolerance": 600,
    "concurrent_session_strategy": "terminate_old",
    "max_auth_failures": 3,
    "auth_failure_lockout_duration": 600
  }'
```

## 📋 验证清单

### 部署验证
- [ ] 所有Pod处于Running状态
- [ ] PostgreSQL包含6个表
- [ ] 默认安全策略已插入
- [ ] Gateway成功启动

### 功能验证
- [ ] 审计日志API返回数据
- [ ] 安全配置API正常工作
- [ ] 配置更新后持久化
- [ ] Pod重启后配置保持

## 🔍 查看日志

```bash
# Gateway日志
kubectl logs -f deployment/gateway -n vehicle-iot-gateway

# PostgreSQL日志
kubectl logs -f deployment/postgres -n vehicle-iot-gateway

# 查看所有Pod
kubectl get pods -n vehicle-iot-gateway -o wide
```

## 🛠️ 常见操作

### 重启服务

```bash
# 重启Gateway
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 重启PostgreSQL（会重新初始化）
kubectl delete pod -l app=postgres -n vehicle-iot-gateway
```

### 查看配置

```bash
# 查看ConfigMap
kubectl get configmap postgres-init-scripts -n vehicle-iot-gateway -o yaml

# 查看Secrets
kubectl get secrets -n vehicle-iot-gateway
```

### 清理环境

```bash
# 删除所有资源
kubectl delete namespace vehicle-iot-gateway

# 或使用清理脚本
cd deployment/kubernetes
bash cleanup.sh
```

## 📚 详细文档

| 文档 | 说明 |
|-----|------|
| `docs/K8S_DATABASE_INIT.md` | Kubernetes数据库初始化详解 |
| `DEPLOYMENT_WITH_FIXES.md` | 包含修复的完整部署指南 |
| `docs/AUDIT_LOG_FIX.md` | 问题2修复详情 |
| `docs/SECURITY_CONFIG_FIX.md` | 问题3修复详情 |
| `PROBLEMS_2_AND_3_FIXED.md` | 问题2和3修复汇总 |

## ❓ 常见问题

### Q1: 为什么不需要手动执行迁移脚本？

A: Kubernetes部署时，PostgreSQL会自动执行 `postgres-init-configmap.yaml` 中的初始化脚本，已包含所有新表的创建语句。

### Q2: 如果我已经有一个运行中的环境怎么办？

A: 需要手动执行数据库迁移脚本：
```bash
bash apply_security_policy_migration.sh
```

### Q3: 配置会在Pod重启后丢失吗？

A: 不会！配置已持久化到PostgreSQL数据库中，Pod重启后会自动从数据库加载。

### Q4: 如何修改默认配置？

A: 通过API修改：
```bash
curl -X PUT "http://8.147.67.31:32620/api/config/security" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Q5: 审计日志会一直增长吗？

A: 建议定期归档或清理旧日志。可以创建定时任务：
```sql
DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '30 days';
```

## 🎉 总结

使用Kubernetes一键部署，所有修复都会自动应用：

✅ 数据库表自动创建
✅ 默认配置自动插入  
✅ 审计日志功能自动启用
✅ 安全配置持久化自动启用

**无需手动操作，部署即可使用所有功能！**

---

**部署时间：** < 5分钟
**修复版本：** v1.0
**支持的功能：** 审计日志 + 安全配置持久化
