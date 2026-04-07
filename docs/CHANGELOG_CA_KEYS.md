# CA 密钥配置变更说明

## 变更概述

移除了不再使用的 `CA_PRIVATE_KEY_PATH` 配置，简化了 CA 密钥管理。

## 变更原因

之前的配置中存在两种 CA 密钥配置方式：
1. ❌ `CA_PRIVATE_KEY_PATH` - 指向 PEM 文件路径（未实际使用）
2. ✅ `CA_PRIVATE_KEY` / `CA_PUBLIC_KEY` - 十六进制格式的环境变量（实际使用）

代码实际上只使用了环境变量方式（见 `src/api/routes/certificates.py`），文件路径配置是遗留的冗余配置。

## 变更内容

### 1. 删除的配置

#### `deployment/kubernetes/secrets.yaml`
```yaml
# 删除
CA_PRIVATE_KEY_PATH: "/app/keys/ca_private.pem"
```

#### `deployment/kubernetes/gateway-deployment.yaml`
```yaml
# 删除环境变量
- name: CA_PRIVATE_KEY_PATH
  valueFrom:
    secretKeyRef:
      name: gateway-secrets
      key: CA_PRIVATE_KEY_PATH

# 删除 volume mount
volumeMounts:
- name: ca-keys
  mountPath: /app/keys
  readOnly: true

# 删除 volume
volumes:
- name: ca-keys
  secret:
    secretName: ca-key-secret
```

### 2. 保留的配置

#### `deployment/kubernetes/secrets.yaml`
```yaml
stringData:
  # CA 密钥（十六进制格式）- 用于证书颁发
  CA_PRIVATE_KEY: "34ed6a521b4888dfa8e1e466840102c70d034e30b27373581432c86aaa8e6330"
  CA_PUBLIC_KEY: "b0668ec547a5232f2eaa6a47dd3dc97e2d268914adb11520b6a9d43cfce0a39c49c9ed136523b2f16db8379f67856ed89edcf6cf1497e055f72386c84ea039dc"
```

#### `deployment/kubernetes/gateway-deployment.yaml`
```yaml
env:
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
```

## 优势

1. **简化配置**：只需要配置环境变量，不需要管理文件和 volume
2. **减少依赖**：不需要创建 `ca-key-secret` Secret 和挂载 volume
3. **更清晰**：配置方式统一，避免混淆
4. **更安全**：密钥直接存储在 Kubernetes Secrets 中，不需要额外的文件管理

## 迁移指南

如果你已经部署了旧版本，按以下步骤迁移：

### 步骤 1: 生成 CA 密钥（如果还没有）

```bash
python scripts/generate_ca_keys.py
```

### 步骤 2: 更新 secrets.yaml

删除 `CA_PRIVATE_KEY_PATH`，添加 `CA_PRIVATE_KEY` 和 `CA_PUBLIC_KEY`。

### 步骤 3: 更新 gateway-deployment.yaml

删除 `CA_PRIVATE_KEY_PATH` 环境变量和相关的 volume 配置。

### 步骤 4: 应用配置

```bash
# 应用更新
kubectl apply -f deployment/kubernetes/secrets.yaml
kubectl apply -f deployment/kubernetes/gateway-deployment.yaml

# 重启网关
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway
```

### 步骤 5: 清理（可选）

如果之前创建了 `ca-key-secret`，可以删除：

```bash
kubectl delete secret ca-key-secret -n vehicle-iot-gateway
```

## 验证

部署后，测试证书申请功能：

```bash
python client/vehicle_client.py \
  --gateway-host <网关IP> \
  --gateway-port <网关端口> \
  --mode once \
  --vehicle-id TEST_CERT \
  --api-token dev-token-12345
```

应该看到：
```
✓ 证书申请成功
  - 序列号: CERT-xxxxx
```

## 相关文档

- [CA 密钥配置指南](CA_KEY_CONFIGURATION.md) - 完整的配置说明
- [部署指南](DEPLOYMENT.md) - Kubernetes 部署说明

## 技术细节

### 代码实现

证书颁发 API (`src/api/routes/certificates.py`) 从环境变量读取 CA 密钥：

```python
ca_private_key_hex = os.getenv("CA_PRIVATE_KEY")
ca_public_key_hex = os.getenv("CA_PUBLIC_KEY")

if not ca_private_key_hex or not ca_public_key_hex:
    raise HTTPException(
        status_code=500,
        detail="CA 密钥未配置"
    )

ca_private_key = bytes.fromhex(ca_private_key_hex)
ca_public_key = bytes.fromhex(ca_public_key_hex)
```

### 密钥格式

- **私钥**：32 字节（64 个十六进制字符）
- **公钥**：64 字节（128 个十六进制字符）
- **算法**：SM2（国密椭圆曲线算法）

## 常见问题

### Q: 为什么不使用 PEM 文件？

A: 
1. 环境变量方式更简单，不需要管理文件和 volume
2. Kubernetes Secrets 已经提供了加密存储
3. 代码实现更直接，不需要文件 I/O

### Q: 十六进制格式安全吗？

A: 
- 密钥存储在 Kubernetes Secrets 中，已经加密
- 不会暴露在日志或配置文件中
- 与 PEM 文件相比，安全性相同

### Q: 如何备份密钥？

A: 
```bash
# 导出 secrets
kubectl get secret gateway-secrets -n vehicle-iot-gateway -o yaml > backup.yaml

# 加密备份
gpg -c backup.yaml
```

### Q: 可以使用原来的 PEM 文件吗？

A: 可以，但需要转换：
1. 如果是未加密的 PEM 文件，可以提取原始字节并转换为十六进制
2. 如果是加密的 SM2 密钥，建议使用 `scripts/generate_ca_keys.py` 生成新密钥
3. 标准的 cryptography 库不支持 SM2 算法的 PEM 格式
