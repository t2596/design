# 客户端IP地址获取修复

## 问题描述

审计日志中的IP地址显示为 `10.244.0.0`，这是Kubernetes Pod网络的内部IP，而不是真实的客户端IP。

## 问题原因

### Kubernetes网络架构

```
真实客户端 (外网IP)
    ↓
LoadBalancer/Ingress (8.160.179.59)
    ↓
Service (ClusterIP)
    ↓
Gateway Pod (10.244.x.x) ← 代码在这里获取IP
```

### 原始代码问题

```python
# 原始代码
client_ip = http_request.client.host if http_request.client else "unknown"
```

这只能获取直接连接的客户端IP，在Kubernetes环境中是：
- Pod IP（如果客户端在集群内）
- Service IP（如果通过Service访问）
- 不是真实的外部客户端IP

## 解决方案

### 1. 使用HTTP头获取真实IP

当请求经过代理、负载均衡器或Ingress时，真实的客户端IP会被保存在HTTP头中：

- `X-Forwarded-For`: 标准的代理头，可能包含多个IP（逗号分隔）
- `X-Real-IP`: Nginx等常用的头

### 2. 代码修复

添加了 `get_client_ip()` 辅助函数：

```python
def get_client_ip(request: Request) -> str:
    """获取客户端真实IP地址
    
    优先级：
    1. X-Forwarded-For 头（代理/负载均衡器设置）
    2. X-Real-IP 头（Nginx等设置）
    3. 直接连接的客户端IP
    """
    # X-Forwarded-For 可能包含多个IP，取第一个（真实客户端IP）
    x_forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    
    # X-Real-IP 通常由Nginx等设置
    x_real_ip = request.headers.get("X-Real-IP", "").strip()
    if x_real_ip:
        return x_real_ip
    
    # 直接连接的客户端IP（可能是Pod IP或Service IP）
    if request.client:
        return request.client.host
    
    return "unknown"
```

### 3. 更新所有使用点

在 `src/api/routes/auth.py` 中的所有地方替换：

```python
# 旧代码
client_ip = http_request.client.host if http_request.client else "unknown"

# 新代码
client_ip = get_client_ip(http_request)
```

## 配置Nginx/Ingress

### 方案1：使用Nginx Ingress

如果使用Nginx Ingress，需要确保配置了 `X-Forwarded-For` 头：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gateway-ingress
  annotations:
    nginx.ingress.kubernetes.io/use-forwarded-headers: "true"
    nginx.ingress.kubernetes.io/compute-full-forwarded-for: "true"
spec:
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: gateway-service
            port:
              number: 8000
```

### 方案2：使用LoadBalancer Service

如果使用LoadBalancer Service，需要配置 `externalTrafficPolicy`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: gateway-service
spec:
  type: LoadBalancer
  externalTrafficPolicy: Local  # 保留源IP
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: gateway
```

### 方案3：更新Web的Nginx配置

如果通过Web的Nginx代理访问Gateway，确保Nginx配置传递了真实IP：

```nginx
location /api/ {
    proxy_pass http://gateway-service:8000;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Host $host;
}
```

这个配置已经在 `web/nginx.conf` 中了，所以通过Web访问应该能获取到真实IP。

## 验证修复

### 1. 重新构建Gateway镜像

```bash
docker build -t your-registry/vehicle-iot-gateway:v1.2 .
docker push your-registry/vehicle-iot-gateway:v1.2
```

### 2. 更新Kubernetes部署

```bash
kubectl set image deployment/gateway \
  gateway=your-registry/vehicle-iot-gateway:v1.2 \
  -n vehicle-iot-gateway

kubectl wait --for=condition=ready pod -l app=gateway \
  -n vehicle-iot-gateway --timeout=120s
```

### 3. 测试IP获取

#### 从外部访问（通过LoadBalancer）

```bash
# 从外部机器访问
curl -X POST "http://8.160.179.59:32677/api/auth/register" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"TEST-IP-001","certificate_serial":"CERT-001"}'

# 查询审计日志
curl -X GET "http://8.160.179.59:32677/api/audit/logs?vehicle_id=TEST-IP-001" \
  -H "Authorization: Bearer dev-token-12345"

# 检查ip_address字段，应该显示你的外网IP
```

#### 从集群内访问（通过Service）

```bash
# 在集群内的Pod中访问
kubectl run test-pod --rm -it --image=curlimages/curl -- sh
curl -X POST "http://gateway-service.vehicle-iot-gateway:8000/api/auth/register" \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":"TEST-IP-002","certificate_serial":"CERT-002"}'

# 这种情况下，IP仍然会是Pod IP（10.244.x.x），因为没有经过代理
```

### 4. 查看审计日志

```bash
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c \
  "SELECT vehicle_id, ip_address, details FROM audit_logs WHERE vehicle_id LIKE 'TEST-IP-%' ORDER BY timestamp DESC;"
```

## IP地址类型说明

### 1. 外网IP（期望的）
- 格式：`8.160.179.59`, `123.45.67.89`
- 来源：真实的客户端公网IP
- 获取方式：通过 `X-Forwarded-For` 或 `X-Real-IP` 头

### 2. Pod IP（当前的）
- 格式：`10.244.x.x`
- 来源：Kubernetes Pod网络
- 获取方式：`request.client.host`

### 3. Service IP
- 格式：`10.96.x.x` 或 `10.244.x.x`
- 来源：Kubernetes Service ClusterIP
- 获取方式：`request.client.host`（通过Service访问时）

### 4. 内网IP
- 格式：`192.168.x.x`, `172.16.x.x`
- 来源：内网客户端
- 获取方式：通过代理头或直接连接

## 常见场景

### 场景1：客户端在集群外（通过LoadBalancer）

```
客户端 (8.160.179.59) 
  → LoadBalancer 
  → Gateway Pod
  
期望IP: 8.160.179.59
实际IP: 8.160.179.59 (修复后)
```

### 场景2：客户端在集群内（Docker容器）

```
客户端 Pod (10.244.1.10) 
  → Service 
  → Gateway Pod
  
期望IP: 10.244.1.10
实际IP: 10.244.1.10
```

### 场景3：通过Web界面访问

```
浏览器 (123.45.67.89) 
  → Web Pod (Nginx) 
  → Gateway Pod
  
期望IP: 123.45.67.89
实际IP: 123.45.67.89 (如果Nginx配置正确)
```

### 场景4：通过Ingress访问

```
客户端 (123.45.67.89) 
  → Ingress Controller 
  → Gateway Service 
  → Gateway Pod
  
期望IP: 123.45.67.89
实际IP: 123.45.67.89 (如果Ingress配置正确)
```

## 安全考虑

### 1. X-Forwarded-For 可以被伪造

如果不信任代理，客户端可以伪造 `X-Forwarded-For` 头。解决方案：

```python
def get_client_ip(request: Request, trust_proxy: bool = True) -> str:
    if not trust_proxy:
        # 不信任代理，只使用直接连接的IP
        return request.client.host if request.client else "unknown"
    
    # 信任代理，使用X-Forwarded-For
    # ...
```

### 2. 只信任特定的代理

```python
TRUSTED_PROXIES = ["10.244.0.0/16", "10.96.0.0/16"]  # Kubernetes网络

def is_trusted_proxy(ip: str) -> bool:
    # 检查IP是否在信任的代理列表中
    # ...
```

### 3. 记录所有IP信息

```python
# 记录完整的IP链
details = f"车辆注册成功，真实IP: {client_ip}, 直接IP: {request.client.host}, X-Forwarded-For: {request.headers.get('X-Forwarded-For', 'N/A')}"
```

## 总结

**问题：** 审计日志中的IP地址是Kubernetes Pod IP（10.244.0.0），而不是真实客户端IP。

**原因：** 代码只获取直接连接的客户端IP，没有从HTTP头中读取真实IP。

**解决方案：**
1. ✅ 添加 `get_client_ip()` 函数，优先从HTTP头获取真实IP
2. ✅ 更新所有使用 `client_ip` 的地方
3. ⚠️ 需要重新构建和部署Gateway镜像
4. ⚠️ 确保Nginx/Ingress配置正确传递IP头

**验证方法：** 从外部访问后，审计日志中的IP应该是外网IP，而不是10.244.x.x。

---

**下一步：** 重新构建Gateway镜像并部署，然后测试IP获取是否正确。
