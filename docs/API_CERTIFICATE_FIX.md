# 证书颁发 API 修复

## 问题描述

证书颁发 API (`/api/certificates/issue`) 存在一个 bug：
- API 忽略了客户端提供的 `public_key` 参数
- API 自己生成了新的密钥对
- 导致客户端无法使用自己的私钥

## 错误信息

```
证书申请失败: 500 - {"detail":"证书颁发失败: public_key 长度必须为 64 字节，当前为 32"}
```

## 问题原因

### 之前的代码（错误）

```python
@router.post("/issue")
async def issue_new_certificate(request: IssueCertificateRequest):
    # ❌ 错误：忽略客户端的公钥，自己生成新的
    public_key, private_key = generate_sm2_keypair()
    
    # 使用自己生成的公钥颁发证书
    certificate = issue_certificate(
        subject_info,
        public_key,  # ← 这是 API 自己生成的，不是客户端的
        ca_private_key,
        ca_public_key,
        db_conn
    )
```

### 修复后的代码（正确）

```python
class IssueCertificateRequest(BaseModel):
    vehicle_id: str
    organization: str = "Vehicle Manufacturer"
    country: str = "CN"
    public_key: str  # ✅ 添加：接收客户端的公钥

@router.post("/issue")
async def issue_new_certificate(request: IssueCertificateRequest):
    # ✅ 正确：使用客户端提供的公钥
    public_key = bytes.fromhex(request.public_key)
    
    # 验证公钥长度
    if len(public_key) != 64:
        raise HTTPException(
            status_code=400,
            detail=f"公钥长度必须为 64 字节，当前为 {len(public_key)}"
        )
    
    # 使用客户端的公钥颁发证书
    certificate = issue_certificate(
        subject_info,
        public_key,  # ← 这是客户端提供的公钥
        ca_private_key,
        ca_public_key,
        db_conn
    )
```

## 修复内容

### 1. 更新请求模型

添加 `public_key` 字段到 `IssueCertificateRequest`：

```python
class IssueCertificateRequest(BaseModel):
    vehicle_id: str
    organization: str = "Vehicle Manufacturer"
    country: str = "CN"
    public_key: str  # 十六进制格式的公钥
```

### 2. 使用客户端公钥

```python
# 解析客户端提供的公钥
public_key = bytes.fromhex(request.public_key)

# 验证公钥长度（SM2 公钥应该是 64 字节）
if len(public_key) != 64:
    raise HTTPException(
        status_code=400,
        detail=f"公钥长度必须为 64 字节，当前为 {len(public_key)}"
    )
```

### 3. 移除不需要的代码

删除了自动生成密钥对的代码：

```python
# ❌ 删除这行
# public_key, private_key = generate_sm2_keypair()
```

## 部署修复

### 方法 1: 重新构建镜像（推荐）

```bash
# 1. 重新构建 Docker 镜像
docker build -t vehicle-iot-gateway:latest .

# 2. 推送到镜像仓库（如果使用）
docker push your-registry/vehicle-iot-gateway:latest

# 3. 重启 Kubernetes Deployment
kubectl rollout restart deployment/gateway -n vehicle-iot-gateway

# 4. 验证更新
kubectl rollout status deployment/gateway -n vehicle-iot-gateway
```

### 方法 2: 热更新（临时）

如果只是测试，可以直接修改运行中的容器：

```bash
# 1. 进入容器
kubectl exec -it -n vehicle-iot-gateway deployment/gateway -- /bin/sh

# 2. 编辑文件
vi /app/src/api/routes/certificates.py

# 3. 重启 uvicorn（如果支持热重载）
# 或者删除 Pod 让它重新创建
kubectl delete pod -l app=gateway -n vehicle-iot-gateway
```

## 验证修复

### 1. 测试证书申请

```bash
python client/vehicle_client.py \
  --gateway-host <网关IP> \
  --gateway-port <网关端口> \
  --mode once \
  --vehicle-id TEST_CERT_FIX \
  --api-token dev-token-12345
```

### 2. 预期输出

修复后应该看到：

```
✓ 证书申请成功
  - 序列号: CERT-xxxxx
  - 有效期: 2026-03-26 至 2027-03-26
```

而不是：

```
⚠ 证书申请失败: 证书申请失败: 500 - ...
使用模拟证书继续...
```

### 3. 验证证书

```bash
# 查看颁发的证书
kubectl exec -it -n vehicle-iot-gateway deployment/postgres -- \
  psql -U gateway_user -d vehicle_iot_gateway \
  -c "SELECT serial_number, subject, valid_from, valid_to FROM certificates WHERE subject LIKE '%TEST_CERT_FIX%';"
```

## API 文档更新

### 请求示例

```bash
curl -X POST "http://localhost:8000/api/certificates/issue" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "VIN123456789",
    "organization": "Test Manufacturer",
    "country": "CN",
    "public_key": "b0668ec547a5232f2eaa6a47dd3dc97e2d268914adb11520b6a9d43cfce0a39c49c9ed136523b2f16db8379f67856ed89edcf6cf1497e055f72386c84ea039dc"
  }'
```

### 响应示例

```json
{
  "serial_number": "CERT-20260326-001",
  "message": "证书颁发成功，序列号: CERT-20260326-001"
}
```

## 影响范围

### 受影响的功能

- ✅ 证书颁发 API (`POST /api/certificates/issue`)
- ✅ 车辆客户端证书申请

### 不受影响的功能

- ✅ 证书查询 API
- ✅ 证书撤销 API
- ✅ CRL 查询 API
- ✅ 其他所有 API

## 技术细节

### SM2 公钥格式

- **长度**: 64 字节（128 个十六进制字符）
- **格式**: 未压缩点格式（04 + X坐标 + Y坐标）
- **编码**: 十六进制字符串

### 客户端流程

1. 客户端生成 SM2 密钥对（私钥 32 字节，公钥 64 字节）
2. 客户端将公钥转换为十六进制字符串
3. 客户端发送公钥到 API 申请证书
4. API 使用客户端的公钥颁发证书
5. 客户端使用自己的私钥进行签名和认证

## 相关文档

- [API 文档](API.md) - 完整的 API 接口说明
- [CA 密钥配置](CA_KEY_CONFIGURATION.md) - CA 密钥配置指南
- [客户端文档](../client/README.md) - 车辆客户端使用说明

## 总结

这个修复确保了：
- ✅ API 正确使用客户端提供的公钥
- ✅ 客户端可以使用自己的私钥进行后续操作
- ✅ 证书颁发流程符合 PKI 标准
- ✅ 双向认证可以正常工作
