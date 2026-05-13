# 系统验证测试套件

三个独立的端到端测试脚本，对应论文 8.2 / 8.3 / 8.4 章节。

## 运行前准备

```bash
export GATEWAY_URL=http://localhost:8000
export API_TOKEN=dev-token-12345
pip install requests
```

## 脚本说明

| 脚本 | 对应章节 | 用途 |
|------|---------|------|
| `test_functional.py` | 8.2 功能验证 | 注册 / 审计日志 / 安全配置 / 鉴权 |
| `test_performance.py` | 8.3 性能测试 | 多客户端并发压测，输出延迟/吞吐量报告 |
| `test_security.py` | 8.4 安全测试 | 未授权/重放/篡改/撤销/锁定 7 类攻击验证 |

## 运行

```bash
# 功能测试
python verification_tests/test_functional.py

# 性能测试（100 并发，持续 10 分钟）
python verification_tests/test_performance.py --clients 100 --duration 600 --interval 1

# 安全测试
python verification_tests/test_security.py
```
