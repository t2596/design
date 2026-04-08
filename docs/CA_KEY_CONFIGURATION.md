# CA 密钥配置指南

本文档说明如何为车联网安全通信网关配置 CA 密钥，以启用证书颁发功能。

## 问题描述

当车辆客户端尝试申请证书时，如果网关返回以下错误：

```
证书申请失败: 500 - {"detail":"证书颁发失败: 500: CA 密钥未配置"}
```

这说明网关缺少 CA 密钥配置。

## 解决方案

### 步骤 1: 生成 CA 密钥对

运行以下脚本生成新的 SM2 CA 密钥对：

```bash
python scripts/generate_ca_keys.py
```

脚本会输出：
- CA 私钥（十六进制格式）
- CA 公钥（十六进制格式）
- Kubernetes 配置示例

**示例输出：**

```
CA 私钥（CA_PRIVATE_KEY）:
34ed6a521b4888dfa8e1e466840102c70d034e30b27373581432c86aaa8e6330

CA 公钥（CA_PUBLIC_KEY）:
b0668ec547a5232f2eaa6a47dd3dc97e2d268914adb11520b6a9d43cfce0a39c49c9ed136523b2f16db8379f67856ed89edcf6cf1497e055f72386c84ea039dc
```

### 步骤 2: 更新 Kubernetes Secrets

编辑 `deployment/kubernetes/secrets.yaml`，添加 CA 密钥：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gateway-secrets
  namespace: vehicle-iot-gateway
type: Opaque
stringData:
  POSTGRES_USER: "gateway_user"
  POSTGRES_PASSWORD: "change_me_in_production"
  REDIS_PASSWORD: "change_me_in_production"
  # CA 密钥（十六进制格式）- 用于证书颁发
  CA_PRIVATE_KEY: "你的CA私钥十六进制"
  CA_PUBLIC_KEY: "你的CA公钥十六进制"
```

### 步骤 3: 更新 Gateway Deployment

编辑 `deployment/kubernetes/gateway-deployment.yaml`，添加环境变量引用：

```yaml
        env:
        # ... 其他环境变量 ...
        - name: CA_PRIVATE_KEY
          valueFrom:
            secretKeyRef:
              name: gateway-secrets
              key: CA_PRIVATE_KEY
        - name: CA_PUBLIC_KEY
          valueFrom:
            secretKeyRef:
              name: gateway-secrets
              key: CA_PUBLIC_KEY
        - name: API_TOKEN
          value: "dev-token-12345"
```

### 步骤 4: 应用配置

```bash
# 1. 应用 secrets 配置
kubectl apply -f deployment/kubernetes/secrets.yaml

# 2. 应用 deployment 配置
kubectl apply -f deployment/kubernetes/gateway-deployment.yaml

# 3. 重启网关 Pod（如果需要）
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 4. 验证部署
kubectl get pods -n vehicle-iot-gateway
kubectl logs -n vehicle-iot-gateway deployment/gateway
```

### 步骤 5: 验证配置

使用车辆客户端测试证书申请：

```bash
python client/vehicle_client.py \
  --gateway-host <你的网关IP> \
  --gateway-port <你的网关端口> \
  --mode once \
  --vehicle-id TEST_CERT_001 \
  --api-token dev-token-12345
```

如果配置正确，应该看到：

```
✓ 证书申请成功
  - 序列号: CERT-xxxxx
  - 有效期: 2026-03-26 至 2027-03-26
```

## 安全注意事项

### 生产环境建议

1. **密钥安全**：
   - 不要将 CA 私钥提交到版本控制系统
   - 使用 Kubernetes Secrets 加密存储
   - 定期轮换 CA 密钥

2. **API Token**：
   - 修改默认的 `dev-token-12345` 为强密码
   - 使用环境变量或 Secrets 管理
   - 实施 API 速率限制

3. **证书管理**：
   - 设置合理的证书有效期
   - 实施证书撤销机制（CRL）
   - 定期审计证书颁发记录

### 密钥备份

备份 CA 密钥到安全位置：

```bash
# 导出 secrets
kubectl get secret gateway-secrets -n vehicle-iot-gateway -o yaml > ca-keys-backup.yaml

# 加密备份文件
gpg -c ca-keys-backup.yaml

# 删除明文备份
rm ca-keys-backup.yaml
```

## 故障排查

### 问题 1: 证书申请返回 403 错误

**错误信息：**
```
证书申请失败: 403 - {"detail":"Not authenticated"}
```

**解决方案：**
- 检查 API Token 是否正确
- 确认请求头包含 `Authorization: Bearer <token>`

### 问题 2: 证书申请返回 500 错误（CA 密钥未配置）

**错误信息：**
```
证书申请失败: 500 - {"detail":"证书颁发失败: 500: CA 密钥未配置"}
```

**解决方案：**
- 检查 secrets.yaml 是否包含 CA_PRIVATE_KEY 和 CA_PUBLIC_KEY
- 检查 gateway-deployment.yaml 是否引用了这些环境变量
- 重启网关 Pod 使配置生效

### 问题 3: 密钥格式错误

**错误信息：**
```
ValueError: CA 私钥长度必须为 32 字节
```

**解决方案：**
- 确保使用 `scripts/generate_ca_keys.py` 生成的十六进制格式密钥
- 私钥应该是 64 个十六进制字符（32 字节）
- 公钥应该是 128 个十六进制字符（64 字节）

## 相关文档

- [API 文档](API.md) - API 接口说明
- [部署指南](DEPLOYMENT.md) - Kubernetes 部署说明
- [运维手册](OPERATIONS.md) - 日常运维操作

## 脚本工具

- `scripts/generate_ca_keys.py` - 生成 CA 密钥对
- `scripts/convert_ca_keys.py` - 转换 PEM 格式密钥（实验性）

## 示例配置

完整的配置示例已经包含在以下文件中：
- `deployment/kubernetes/secrets.yaml` - 包含示例 CA 密钥
- `deployment/kubernetes/gateway-deployment.yaml` - 包含环境变量引用

**注意：** 示例密钥仅用于开发测试，生产环境请生成新的密钥！
