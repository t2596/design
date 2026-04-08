# PostgreSQL 卡住问题 - 快速修复

## 问题

PostgreSQL Pod 卡在 `ContainerCreating` 状态，无法启动。

## 原因

缺少 `postgres-init-scripts` ConfigMap。

## 快速修复（3 步）

### 1. 创建 ConfigMap

```bash
kubectl apply -f deployment/kubernetes/postgres-init-configmap.yaml
```

### 2. 删除卡住的 Pod

```bash
kubectl delete pod -l app=postgres -n vehicle-iot-gateway
```

### 3. 验证启动成功

```bash
# 查看 Pod 状态（应该显示 Running）
kubectl get pods -n vehicle-iot-gateway -l app=postgres

# 查看日志（应该看到 "ready to accept connections"）
kubectl logs -n vehicle-iot-gateway -l app=postgres --tail=20
```

## 完成！

PostgreSQL 应该已经正常运行了。

## 验证数据库

```bash
# 测试连接
kubectl exec -it -n vehicle-iot-gateway deployment/postgres -- pg_isready -U gateway_user

# 查看表
kubectl exec -it -n vehicle-iot-gateway deployment/postgres -- psql -U gateway_user -d vehicle_iot_gateway -c "\dt"
```

应该看到 3 个表：
- `certificates`
- `certificate_revocation_list`
- `audit_logs`

## 详细说明

查看 [POSTGRES_INIT_FIX.md](POSTGRES_INIT_FIX.md) 了解更多细节。
