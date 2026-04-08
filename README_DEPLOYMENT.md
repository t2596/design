# 部署指南总览

## 🎯 快速导航

根据你的需求选择合适的指南：

### 📦 镜像构建
- **快速构建**: 运行 `bash quick-build.sh`
- **完整构建**: 运行 `bash build-and-push.sh -r username -v v1.0 -p`
- **详细说明**: 查看 `BUILD_AND_PUSH_IMAGE.md`

### 🚀 Kubernetes部署
- **全新部署**: 运行 `cd deployment/kubernetes && bash deploy-all.sh`
- **更新部署**: 查看 `COMPLETE_DEPLOYMENT_GUIDE.md`
- **一键部署**: 查看 `K8S_ONE_CLICK_DEPLOY_README.md`

### 🔧 问题修复
- **问题2（审计日志）**: 查看 `AUDIT_LOG_FIX_README.md`
- **问题3（安全配置）**: 查看 `SECURITY_CONFIG_FIX_README.md`
- **问题汇总**: 查看 `PROBLEMS_2_AND_3_FIXED.md`

## ⚡ 最快部署方式

### 方式1：本地测试（单节点）

```bash
# 1. 快速构建镜像
bash quick-build.sh

# 2. 部署到K8s
cd deployment/kubernetes
bash deploy-all.sh

# 3. 验证
kubectl get pods -n vehicle-iot-gateway
```

### 方式2：生产部署（推荐）

```bash
# 1. 构建并推送镜像
bash build-and-push.sh -r your-username -v v1.0 -p

# 2. 更新K8s配置
# 编辑 deployment/kubernetes/gateway-deployment.yaml
# 将 image 改为: your-username/vehicle-iot-gateway:v1.0

# 3. 部署
cd deployment/kubernetes
bash deploy-all.sh

# 4. 验证
bash ../test_audit_logs_api.sh
bash ../test_security_config_api.sh
```

## 📋 部署前检查清单

### 代码修改
- [ ] 问题2修复已应用（审计日志）
- [ ] 问题3修复已应用（安全配置）
- [ ] 数据库初始化脚本已更新

### 环境准备
- [ ] Docker已安装并运行
- [ ] Kubernetes集群可访问
- [ ] kubectl已配置
- [ ] 镜像仓库已登录（如需推送）

### 配置文件
- [ ] `deployment/kubernetes/gateway-deployment.yaml` 镜像地址已更新
- [ ] `deployment/kubernetes/secrets.yaml` 密码已配置
- [ ] `deployment/kubernetes/configmap.yaml` 配置已检查

## 🔍 验证部署

### 快速验证

```bash
# 检查Pod状态
kubectl get pods -n vehicle-iot-gateway

# 检查数据库表
kubectl exec -it deployment/postgres -n vehicle-iot-gateway -- \
  psql -U postgres -d vehicle_iot_gateway -c "\dt"

# 测试API
curl http://8.147.67.31:32620/health
```

### 完整验证

```bash
# 生成测试数据
python3 generate_audit_test_data.py

# 测试审计日志
bash test_audit_logs_api.sh

# 测试安全配置
bash test_security_config_api.sh
```

## 📚 文档索引

### 核心文档
| 文档 | 说明 | 适用场景 |
|-----|------|---------|
| `BUILD_AND_PUSH_IMAGE.md` | 镜像构建详解 | 需要构建镜像 |
| `COMPLETE_DEPLOYMENT_GUIDE.md` | 完整部署流程 | 首次部署或完整了解 |
| `K8S_ONE_CLICK_DEPLOY_README.md` | 一键部署指南 | 快速部署 |

### 问题修复文档
| 文档 | 说明 |
|-----|------|
| `AUDIT_LOG_FIX_README.md` | 问题2快速指南 |
| `SECURITY_CONFIG_FIX_README.md` | 问题3快速指南 |
| `PROBLEMS_2_AND_3_FIXED.md` | 问题汇总 |
| `docs/AUDIT_LOG_FIX.md` | 问题2详细说明 |
| `docs/SECURITY_CONFIG_FIX.md` | 问题3详细说明 |

### 技术文档
| 文档 | 说明 |
|-----|------|
| `docs/K8S_DATABASE_INIT.md` | 数据库初始化详解 |
| `DEPLOYMENT_WITH_FIXES.md` | 包含修复的部署指南 |

## 🛠️ 常用脚本

### 构建脚本
- `quick-build.sh` - 快速构建（本地测试）
- `build-and-push.sh` - 完整构建和推送

### 测试脚本
- `generate_audit_test_data.py` - 生成审计日志测试数据
- `test_audit_logs_api.sh` - 测试审计日志API
- `test_security_config_api.sh` - 测试安全配置API
- `test_auth_failure_lockout.py` - 测试认证失败锁定

### 部署脚本
- `deployment/kubernetes/deploy-all.sh` - 一键部署
- `deployment/kubernetes/cleanup.sh` - 清理环境
- `apply_security_policy_migration.sh` - 应用数据库迁移

## 🎯 典型场景

### 场景1：开发环境快速测试

```bash
# 1. 快速构建
bash quick-build.sh

# 2. 部署
cd deployment/kubernetes && bash deploy-all.sh

# 3. 测试
python3 ../generate_audit_test_data.py
```

### 场景2：生产环境首次部署

```bash
# 1. 构建并推送镜像
bash build-and-push.sh -r your-registry/your-namespace -v v1.0 -p

# 2. 更新配置
# 编辑 deployment/kubernetes/gateway-deployment.yaml

# 3. 部署
cd deployment/kubernetes && bash deploy-all.sh

# 4. 验证
bash ../test_audit_logs_api.sh
bash ../test_security_config_api.sh
```

### 场景3：更新已有环境

```bash
# 1. 应用数据库迁移
bash apply_security_policy_migration.sh

# 2. 构建新镜像
bash build-and-push.sh -r your-registry -v v1.1 -p

# 3. 更新部署
kubectl apply -f deployment/kubernetes/gateway-deployment.yaml

# 4. 验证
kubectl rollout status deployment/gateway -n vehicle-iot-gateway
```

## ❓ 常见问题

### Q1: 如何选择镜像仓库？
- **Docker Hub**: 适合公开项目和测试
- **阿里云**: 适合国内项目，速度快
- **Harbor**: 适合企业私有部署

### Q2: 是否需要手动执行数据库迁移？
- **全新部署**: 不需要，自动创建所有表
- **更新部署**: 需要，运行 `bash apply_security_policy_migration.sh`

### Q3: 如何验证修复是否生效？
```bash
# 验证问题2
bash test_audit_logs_api.sh

# 验证问题3
bash test_security_config_api.sh
```

### Q4: 部署失败如何排查？
```bash
# 查看Pod状态
kubectl get pods -n vehicle-iot-gateway

# 查看Pod日志
kubectl logs -f deployment/gateway -n vehicle-iot-gateway

# 查看事件
kubectl get events -n vehicle-iot-gateway
```

## 🎉 总结

### 最简部署流程

```bash
# 1. 构建镜像
bash quick-build.sh

# 2. 部署
cd deployment/kubernetes && bash deploy-all.sh

# 3. 验证
kubectl get pods -n vehicle-iot-gateway
```

### 完整部署流程

```bash
# 1. 构建并推送
bash build-and-push.sh -r username -v v1.0 -p

# 2. 更新配置
# 编辑 deployment/kubernetes/gateway-deployment.yaml

# 3. 部署
cd deployment/kubernetes && bash deploy-all.sh

# 4. 验证
bash ../test_audit_logs_api.sh
bash ../test_security_config_api.sh
```

---

**提示**: 选择适合你的部署方式，所有脚本都经过测试，可以直接使用！

**支持**: 如有问题，请查看对应的详细文档或检查日志。
