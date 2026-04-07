# 加密数据传输功能说明

## 功能概述

已启用基于国密算法的端到端加密数据传输：
- **SM4 对称加密**：加密业务数据（128位密钥）
- **SM2 数字签名**：验证数据完整性和来源

## 数据流程

```
客户端                                    网关
  |                                        |
  | 1. 生成 SM2 密钥对                      |
  |    (私钥 32字节, 公钥 64字节)            |
  |                                        |
  | 2. 注册 + 发送公钥                      |
  |-------------------------------------->|
  |                                        | 3. 生成 SM4 会话密钥(16字节)
  |                                        | 4. 生成网关 SM2 密钥对
  |                                        | 5. 保存车辆公钥到 Redis
  |                                        |
  | 6. 接收会话密钥 + 网关公钥               |
  |<--------------------------------------|
  |                                        |
  | 7. 采集车辆数据                         |
  | 8. 使用 SM4 加密数据                    |
  | 9. 使用 SM2 签名                        |
  | 10. 发送加密报文                        |
  |-------------------------------------->|
  |                                        | 11. 使用 SM2 验证签名
  |                                        | 12. 检查 nonce 防重放
  |                                        | 13. 使用 SM4 解密数据
  |                                        | 14. 保存到数据库
  |                                        |
  | 15. 接收确认响应                        |
  |<--------------------------------------|
```

## 安全特性

### 1. 数据加密（SM4）
- 使用 128 位会话密钥
- CBC 模式加密
- 每个会话独立密钥

### 2. 数字签名（SM2）
- 签名内容：消息头 + 加密载荷 + 时间戳 + nonce
- 签名长度：64 字节
- 验证发送方身份和数据完整性

### 3. 防重放攻击
- 每条消息包含 16 字节唯一 nonce
- nonce 在 Redis 中标记已使用（TTL 10分钟）
- 时间戳验证（容差 ±5 分钟）

### 4. 会话管理
- 会话密钥存储在 Redis
- 会话超时：30 分钟
- 自动清理过期会话

## API 端点

### 1. 车辆注册（建立加密会话）

**端点**：`POST /api/auth/register`

**请求**：
```json
{
  "vehicle_id": "VIN1234",
  "certificate_serial": "CERT-001",
  "public_key": "04a1b2c3..." // SM2 公钥 (hex, 128字符)
}
```

**响应**：
```json
{
  "success": true,
  "session_id": "uuid",
  "session_key": "0123456789abcdef...", // SM4 密钥 (hex, 32字符)
  "gateway_public_key": "04d4e5f6...", // 网关公钥 (hex, 128字符)
  "message": "车辆 VIN1234 注册成功，已建立加密会话"
}
```

### 2. 发送加密数据

**端点**：`POST /api/auth/data/secure?vehicle_id=VIN1234&session_id=uuid`

**请求**：
```json
{
  "header": {
    "version": 1,
    "message_type": "DATA_TRANSFER",
    "sender_id": "VIN1234",
    "receiver_id": "gateway",
    "session_id": "uuid"
  },
  "encrypted_payload": "a1b2c3d4...", // SM4 加密后的数据 (hex)
  "signature": "e5f6g7h8...", // SM2 签名 (hex, 128字符)
  "timestamp": "2026-04-01T12:00:00",
  "nonce": "0123456789abcdef..." // 16字节 nonce (hex, 32字符)
}
```

**响应**：
```json
{
  "success": true,
  "message": "加密车辆数据接收成功",
  "vehicle_id": "VIN1234",
  "timestamp": "2026-04-01T12:00:00",
  "encryption": "SM4",
  "signature": "SM2-verified"
}
```

## 部署步骤

### 1. 重新构建镜像

```bash
# 构建 Gateway 镜像
docker build -t vehicle-iot-gateway:latest .

# 构建 Client 镜像
cd client
docker build -t vehicle-iot-client:latest .
```

### 2. 部署到 K8s

```bash
# 删除旧的 Gateway Pods
kubectl delete pods -n vehicle-iot-gateway -l app=gateway

# 等待新 Pods 启动
kubectl wait --for=condition=ready pod -l app=gateway -n vehicle-iot-gateway --timeout=120s
```

### 3. 测试加密传输

```bash
# 运行测试脚本
bash test_encrypted_transmission.sh

# 或手动运行客户端
python client/vehicle_client.py \
  --vehicle-id VIN_TEST_ENCRYPT \
  --gateway-host 8.147.67.31 \
  --gateway-port 32620 \
  --mode once
```

## 验证方法

### 1. 客户端输出验证

正常输出应包含：
```
正在使用 SM4 加密数据...
  - 加密后数据大小: XXX 字节
  - 签名长度: 64 字节
✓ 加密数据发送成功
  - 签名验证: 通过
```

### 2. Gateway 日志验证

```bash
kubectl logs -n vehicle-iot-gateway deployment/gateway --tail=50 | grep -E 'secure|SM4|SM2'
```

应看到：
- 接收到加密数据
- SM2 签名验证通过
- SM4 解密成功

### 3. 数据库验证

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT vehicle_id, timestamp, state FROM vehicle_data ORDER BY timestamp DESC LIMIT 5;"
```

应看到新的数据记录。

## 故障排查

### 问题 1：签名验证失败

**原因**：车辆公钥不匹配或签名算法错误

**解决**：
1. 检查车辆公钥是否正确保存到 Redis
2. 验证签名数据顺序是否一致

### 问题 2：Nonce 已使用

**原因**：重放攻击或客户端重复发送

**解决**：
1. 确保每次发送使用新的 nonce
2. 检查 Redis 中的 nonce 记录

### 问题 3：解密失败

**原因**：会话密钥不匹配或数据损坏

**解决**：
1. 重新注册建立新会话
2. 检查会话密钥是否正确传递

## 性能影响

- **加密开销**：~5-10ms per message
- **签名开销**：~10-15ms per message
- **总延迟增加**：~15-25ms
- **CPU 使用率增加**：~5-10%

## 兼容性

### 保留旧端点

为了向后兼容，保留了未加密的端点：
- `POST /api/auth/data` - 接收明文数据（不推荐）

### 迁移建议

1. 先部署新版本 Gateway
2. 逐步升级客户端
3. 监控两个端点的使用情况
4. 最终废弃明文端点

## 安全建议

1. **生产环境**：
   - 使用真实的 CA 证书
   - 启用 HTTPS/TLS
   - 定期轮换会话密钥
   - 实施严格的访问控制

2. **密钥管理**：
   - 私钥不要存储在代码中
   - 使用硬件安全模块（HSM）
   - 定期备份密钥

3. **监控**：
   - 记录所有加密/解密操作
   - 监控签名验证失败率
   - 告警异常的 nonce 使用

## 相关文件

- `client/vehicle_client.py` - 客户端加密实现
- `src/api/routes/auth.py` - 网关解密实现
- `src/secure_messaging.py` - 加密/解密核心逻辑
- `src/crypto/sm4.py` - SM4 加密算法
- `src/crypto/sm2.py` - SM2 签名算法
