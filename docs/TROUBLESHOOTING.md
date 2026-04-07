# 故障排查指南

## 常见问题

### 1. 数据库连接失败

**症状**:
```
psycopg2.OperationalError: could not connect to server
```

**可能原因**:
- PostgreSQL 服务未启动
- 数据库连接配置错误
- 网络连接问题
- 防火墙阻止连接

**排查步骤**:

```bash
# 1. 检查 PostgreSQL 服务状态
docker-compose ps postgres
# 或
sudo systemctl status postgresql

# 2. 检查端口是否开放
netstat -an | grep 5432

# 3. 测试数据库连接
psql -h localhost -p 5432 -U gateway_user -d vehicle_iot_gateway

# 4. 检查环境变量
cat .env | grep POSTGRES

# 5. 查看 PostgreSQL 日志
docker-compose logs postgres
# 或
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

**解决方案**:
- 确保 PostgreSQL 服务正在运行
- 验证 .env 文件中的数据库配置
- 检查防火墙规则
- 确保数据库用户有正确的权限

### 2. Redis 连接失败

**症状**:
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**可能原因**:
- Redis 服务未启动
- Redis 密码错误
- 网络连接问题

**排查步骤**:

```bash
# 1. 检查 Redis 服务状态
docker-compose ps redis
# 或
sudo systemctl status redis-server

# 2. 测试 Redis 连接
redis-cli -h localhost -p 6379 -a your_password ping

# 3. 检查 Redis 日志
docker-compose logs redis
# 或
sudo tail -f /var/log/redis/redis-server.log

# 4. 检查 Redis 配置
redis-cli -a your_password CONFIG GET requirepass
```

**解决方案**:
- 启动 Redis 服务
- 验证 REDIS_PASSWORD 环境变量
- 检查 Redis 配置文件中的 requirepass 设置

### 3. 认证失败

**症状**:
```
Authentication failed: INVALID_CERTIFICATE
```

**可能原因**:
- 证书已过期
- 证书已被撤销
- 证书签名验证失败
- CA 公钥不匹配

**排查步骤**:

```bash
# 1. 查询证书信息
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT serial_number, subject, valid_from, valid_to 
FROM certificates 
WHERE serial_number = 'CERT-001';
"

# 2. 检查证书是否在 CRL 中
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT * FROM certificate_revocation_list 
WHERE serial_number = 'CERT-001';
"

# 3. 查看认证失败日志
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT * FROM audit_logs 
WHERE event_type = 'AUTHENTICATION_FAILURE'
ORDER BY timestamp DESC 
LIMIT 10;
"

# 4. 检查 CA 密钥文件
ls -la keys/ca_*.pem
```

**解决方案**:
- 如果证书过期，重新颁发证书
- 如果证书被撤销，检查撤销原因
- 验证 CA 密钥文件路径和权限
- 检查证书格式是否正确

### 4. 签名验证失败

**症状**:
```
Signature verification failed
```

**可能原因**:
- 数据被篡改
- 使用了错误的公钥
- 签名算法不匹配

**排查步骤**:

```bash
# 1. 查看签名验证失败日志
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT * FROM audit_logs 
WHERE event_type = 'SIGNATURE_FAILED'
ORDER BY timestamp DESC 
LIMIT 10;
"

# 2. 检查车辆证书公钥
curl http://localhost:8000/api/certificates?vehicle_id=VIN123456789

# 3. 验证签名算法
# 确保使用 SM2 算法
```

**解决方案**:
- 检查数据传输过程是否完整
- 验证使用的公钥是否正确
- 确认签名算法为 SM2
- 检查是否存在中间人攻击

### 5. 重放攻击检测

**症状**:
```
Replay attack detected: nonce already used
```

**可能原因**:
- 消息被重放
- Nonce 追踪系统故障
- 时间戳异常

**排查步骤**:

```bash
# 1. 查看重放攻击日志
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT * FROM audit_logs 
WHERE details LIKE '%重放攻击%'
ORDER BY timestamp DESC 
LIMIT 10;
"

# 2. 检查 Nonce 追踪
redis-cli -a your_password --scan --pattern "nonce:*" | head -20

# 3. 检查系统时间
date
# 确保服务器时间同步
```

**解决方案**:
- 如果是真实攻击，阻止该车辆的通信
- 如果是误报，检查 Nonce 追踪逻辑
- 确保服务器时间同步（使用 NTP）
- 检查时间戳容差配置

### 6. 会话过期

**症状**:
```
Session expired
```

**可能原因**:
- 会话超时
- Redis 数据丢失
- 会话被手动清理

**排查步骤**:

```bash
# 1. 检查会话配置
echo $SESSION_TIMEOUT

# 2. 查看会话信息
redis-cli -a your_password GET "session:SESSION_ID"

# 3. 检查 Redis 内存使用
redis-cli -a your_password INFO memory

# 4. 查看会话清理日志
docker-compose logs gateway | grep "session cleanup"
```

**解决方案**:
- 车辆重新认证建立新会话
- 调整 SESSION_TIMEOUT 配置
- 检查 Redis 内存配置和驱逐策略
- 确保 Redis 持久化正常工作

### 7. 性能下降

**症状**:
- 认证延迟超过 500ms
- API 响应缓慢
- 数据库查询超时

**排查步骤**:

```bash
# 1. 检查系统资源
docker stats
# 或
top
htop

# 2. 检查数据库性能
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT * FROM pg_stat_activity WHERE state = 'active';
"

# 3. 检查 Redis 性能
redis-cli -a your_password --latency

# 4. 查看应用日志
docker-compose logs gateway | grep -i "slow\|timeout\|error"

# 5. 检查网络延迟
ping postgres
ping redis
```

**解决方案**:
- 增加服务器资源（CPU、内存）
- 优化数据库查询（添加索引）
- 启用证书验证缓存
- 增加应用实例数量（水平扩展）
- 清理过期数据

### 8. 内存泄漏

**症状**:
- 内存使用持续增长
- 服务最终崩溃或被 OOM Killer 终止

**排查步骤**:

```bash
# 1. 监控内存使用
docker stats gateway

# 2. 检查 Python 进程内存
ps aux | grep python

# 3. 查看 Redis 内存
redis-cli -a your_password INFO memory

# 4. 检查会话数量
redis-cli -a your_password DBSIZE
```

**解决方案**:
- 检查会话清理是否正常工作
- 配置 Redis maxmemory 和驱逐策略
- 检查是否有未关闭的数据库连接
- 重启服务释放内存
- 使用内存分析工具（memory_profiler）

### 9. 证书缓存问题

**症状**:
- 撤销的证书仍然被接受
- 证书更新未生效

**可能原因**:
- 缓存未过期
- 缓存更新失败

**排查步骤**:

```bash
# 1. 检查缓存配置
echo $CACHE_TTL

# 2. 清空证书缓存
redis-cli -a your_password --scan --pattern "cert_cache:*" | xargs redis-cli -a your_password DEL

# 3. 查看缓存命中率
curl http://localhost:8000/api/metrics/cache
```

**解决方案**:
- 手动清空缓存
- 调整 CACHE_TTL 配置
- 实现缓存失效通知机制

### 10. API 服务无响应

**症状**:
- API 请求超时
- 健康检查失败

**排查步骤**:

```bash
# 1. 检查服务状态
docker-compose ps gateway

# 2. 查看进程状态
docker-compose exec gateway ps aux

# 3. 检查端口监听
docker-compose exec gateway netstat -tlnp | grep 8000

# 4. 查看错误日志
docker-compose logs --tail=100 gateway

# 5. 检查资源限制
docker inspect gateway | grep -A 10 Resources
```

**解决方案**:
- 重启服务
- 增加资源限制
- 检查是否有死锁或阻塞
- 启用请求超时配置

## 日志分析

### 错误日志关键字

- `INVALID_CERTIFICATE`: 证书验证失败
- `SIGNATURE_VERIFICATION_FAILED`: 签名验证失败
- `SESSION_EXPIRED`: 会话过期
- `REPLAY_ATTACK_DETECTED`: 检测到重放攻击
- `DECRYPTION_FAILED`: 解密失败
- `CA_SERVICE_UNAVAILABLE`: CA 服务不可用

### 日志聚合

```bash
# 统计错误类型
docker-compose logs gateway | grep ERROR | awk '{print $NF}' | sort | uniq -c | sort -rn

# 统计认证失败次数
psql -U gateway_user -d vehicle_iot_gateway -c "
SELECT DATE(timestamp) as date, COUNT(*) as failures
FROM audit_logs
WHERE event_type = 'AUTHENTICATION_FAILURE'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
"
```

## 联系支持

如果以上方法无法解决问题，请联系技术支持团队并提供：
- 错误日志（最近 100 行）
- 系统配置信息
- 复现步骤
- 环境信息（操作系统、Docker 版本等）
