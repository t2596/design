# 数据库迁移脚本

## 迁移脚本列表

- `001_initial_schema.sql`: 初始数据库架构（证书、CRL、审计日志表）

## 执行迁移

### 手动执行
```bash
psql -U gateway_user -d vehicle_iot_gateway -f migrations/001_initial_schema.sql
```

### Docker 环境
迁移脚本会在容器启动时自动执行（通过 docker-entrypoint-initdb.d）

### Kubernetes 环境
使用 Job 执行迁移：
```bash
kubectl apply -f migration-job.yaml
```

## 回滚

如需回滚，请手动执行相应的回滚脚本或删除表：
```sql
DROP VIEW IF EXISTS valid_certificates;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS certificate_revocation_list CASCADE;
DROP TABLE IF EXISTS certificates CASCADE;
```
