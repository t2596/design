# 运维手册

## 日常运维

### 服务管理

#### Docker Compose 环境

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 重启服务
docker-compose restart gateway

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f gateway
docker-compose logs -f postgres
docker-compose logs -f redis
```

#### Kubernetes 环境

```bash
# 查看 Pod 状态
kubectl get pods -n vehicle-iot-gateway

# 查看服务状态
kubectl get services -n vehicle-iot-gateway

# 查看日志
kubectl logs -f deployment/gateway -n vehicle-iot-gateway

# 重启服务
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 扩缩容
kubectl scale deployment gateway -n vehicle-iot-gateway --replicas=5
```

### 健康检查

```bash
# 检查 API 健康状态
curl http://localhost:8000/health

# 检查数据库连接
psql -U gateway_user -d vehicle_iot_gateway -c "SELECT 1"

# 检查 Redis 连接
redis-cli -a your_password ping
```

## 证书管理

### 颁发证书

```bash
# 使用 API 颁发证书
curl -X POST http://localhost:8000/api/certificates/issue \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "VIN123456789",
    "organization": "某汽车制造商",
    "country": "CN",
    "public_key": "base64_encoded_public_key"
  }'
```

### 撤销证书

```bash
# 撤销证书
curl -X POST http://localhost:8000/api/certificates/revoke \
  -H "Content-Type: application/json" \
  -d '{
    "serial_number": "CERT-001",
    "reason": "密钥泄露"
  }'
```

### 查看 CRL

```bash
# 获取证书撤销列表
curl http://localhost:8000/api/certificates/crl
```

### 证书过期检查

```bash
# 查询即将过期的证书（30 天内）
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT serial_number, subject, valid_to 
FROM certificates 
WHERE valid_to < CURRENT_TIMESTAMP + INTERVAL '30 days'
  AND valid_to > CURRENT_TIMESTAMP
ORDER BY valid_to;
"
```

## 会话管理

### 查看活跃会话

```bash
# 查看所有活跃会话
redis-cli -a your_password KEYS "session:*"

# 查看会话详情
redis-cli -a your_password GET "session:SESSION_ID"

# 查看会话数量
redis-cli -a your_password DBSIZE
```

### 清理过期会话

```bash
# 手动触发会话清理
curl -X POST http://localhost:8000/api/sessions/cleanup
```

### 强制关闭会话

```bash
# 关闭特定会话
redis-cli -a your_password DEL "session:SESSION_ID"
```

## 审计日志管理

### 查询审计日志

```bash
# 查询最近 100 条日志
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT * FROM audit_logs 
ORDER BY timestamp DESC 
LIMIT 100;
"

# 查询特定车辆的日志
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT * FROM audit_logs 
WHERE vehicle_id = 'VIN123456789'
ORDER BY timestamp DESC;
"

# 查询认证失败事件
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT * FROM audit_logs 
WHERE event_type LIKE '%AUTHENTICATION%' 
  AND operation_result = false
ORDER BY timestamp DESC;
"
```

### 导出审计报告

```bash
# 导出指定时间范围的审计报告
curl "http://localhost:8000/api/audit/export?start_time=2026-03-01T00:00:00&end_time=2026-03-31T23:59:59" \
  -o audit_report_202603.json
```

### 日志归档

```bash
# 归档 90 天前的日志
psql -U gateway_user -d vehicle_iot_gateway -c "
DELETE FROM audit_logs 
WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '90 days';
"
```

## 性能监控

### 查看实时指标

```bash
# 获取实时性能指标
curl http://localhost:8000/api/metrics/realtime

# 获取历史指标
curl "http://localhost:8000/api/metrics/history?start_time=2026-03-21T00:00:00&end_time=2026-03-21T23:59:59"
```

### 数据库性能监控

```bash
# 查看活跃连接
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT count(*) FROM pg_stat_activity;
"

# 查看慢查询
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"

# 查看表大小
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Redis 性能监控

```bash
# 查看 Redis 信息
redis-cli -a your_password INFO

# 查看内存使用
redis-cli -a your_password INFO memory

# 查看慢查询日志
redis-cli -a your_password SLOWLOG GET 10

# 监控实时命令
redis-cli -a your_password MONITOR
```

## 备份策略

### 自动备份脚本

创建 `scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份 PostgreSQL
pg_dump -U gateway_user -d vehicle_iot_gateway -F c -f "$BACKUP_DIR/postgres_$DATE.dump"

# 备份 Redis
redis-cli -a your_password SAVE
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# 删除 30 天前的备份
find $BACKUP_DIR -name "*.dump" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete

echo "备份完成: $DATE"
```

### 配置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨 2 点执行备份
0 2 * * * /path/to/scripts/backup.sh >> /var/log/gateway_backup.log 2>&1
```

## 安全运维

### 密钥轮换

```bash
# 生成新的会话密钥
# 系统会自动每 24 小时轮换会话密钥

# 更新 CA 密钥（需要重新颁发所有证书）
# 1. 生成新的 CA 密钥对
gmssl sm2keygen -pass 1234567890 -out keys/ca_private_new.pem -pubout keys/ca_public_new.pem

# 2. 更新配置
# 3. 重启服务
# 4. 重新颁发所有证书
```

### 安全审计

```bash
# 检查失败的认证尝试
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT vehicle_id, COUNT(*) as failed_attempts
FROM audit_logs
WHERE event_type = 'AUTHENTICATION_FAILURE'
  AND timestamp > CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY vehicle_id
HAVING COUNT(*) > 5
ORDER BY failed_attempts DESC;
"

# 检查重放攻击
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT * FROM audit_logs
WHERE details LIKE '%重放攻击%'
  AND timestamp > CURRENT_TIMESTAMP - INTERVAL '24 hours'
ORDER BY timestamp DESC;
"
```

### 访问控制

```bash
# 查看当前在线车辆
curl http://localhost:8000/api/vehicles/online

# 强制断开特定车辆
curl -X POST http://localhost:8000/api/sessions/close \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id": "VIN123456789"}'
```

## 升级与回滚

### 应用升级

```bash
# Docker Compose 环境
docker-compose pull
docker-compose up -d

# Kubernetes 环境
kubectl set image deployment/gateway gateway=vehicle-iot-gateway:v1.1.0 -n vehicle-iot-gateway
kubectl rollout status deployment/gateway -n vehicle-iot-gateway
```

### 数据库迁移

```bash
# 执行新的迁移脚本
psql -U gateway_user -d vehicle_iot_gateway -f db/migrations/002_new_migration.sql
```

### 回滚

```bash
# Kubernetes 回滚
kubectl rollout undo deployment/gateway -n vehicle-iot-gateway

# 查看回滚历史
kubectl rollout history deployment/gateway -n vehicle-iot-gateway
```

## 容量规划

### 数据库容量

- 证书表: 约 1KB/证书
- 审计日志: 约 500 字节/条
- 预估: 10,000 车辆 × 365 天 × 100 条日志/天 = 约 18GB/年

### Redis 容量

- 会话信息: 约 500 字节/会话
- Nonce 追踪: 约 100 字节/nonce
- 预估: 10,000 并发会话 = 约 5MB

### 网络带宽

- 单次认证: 约 5KB
- 单次数据传输: 约 2KB + 业务数据大小
- 预估: 10,000 车辆 × 10 次/分钟 = 约 2MB/s

## 灾难恢复

### 恢复流程

1. 恢复数据库备份
2. 恢复 Redis 备份（可选，会话可重建）
3. 恢复 CA 密钥
4. 重启服务
5. 验证系统功能
6. 通知车辆重新认证

### RTO/RPO 目标

- RTO（恢复时间目标）: < 1 小时
- RPO（恢复点目标）: < 24 小时
