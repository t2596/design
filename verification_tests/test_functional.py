"""功能验证测试（8.2）

通过 API 调用验证系统核心功能：
  1. 车辆注册 → 验证证书序列号/有效期
  2. 审计日志查询 → 验证注册事件已记录
  3. 安全配置读取/更新 → 验证持久化
  4. 所有请求使用 Authorization 头
"""

import os
import sys
import time
import uuid
import json
import requests

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_TOKEN", "dev-token-12345")
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


def _assert(cond, msg):
    status = "✓" if cond else "✗"
    print(f"  {status} {msg}")
    if not cond:
        raise AssertionError(msg)


def test_vehicle_register():
    """测试 1：车辆注册并验证返回的证书信息"""
    print("\n[测试1] 车辆注册 + 证书颁发")
    vehicle_id = f"VIN_TEST_{uuid.uuid4().hex[:8]}"

    # 先申请证书
    issue_resp = requests.post(
        f"{GATEWAY_URL}/api/certificates/issue",
        json={
            "vehicle_id": vehicle_id,
            "organization": "Test Org",
            "country": "CN",
            "public_key": "a" * 128,
        },
        headers=HEADERS, timeout=10,
    )
    _assert(issue_resp.status_code == 200, f"证书申请 HTTP 200（实际 {issue_resp.status_code}）")
    cert = issue_resp.json()
    _assert("serial_number" in cert, "返回包含 serial_number")
    _assert("valid_from" in cert and "valid_to" in cert, "返回包含有效期")
    print(f"    serial_number={cert['serial_number'][:16]}...")

    # 车辆注册
    reg_resp = requests.post(
        f"{GATEWAY_URL}/api/auth/register",
        json={
            "vehicle_id": vehicle_id,
            "certificate_serial": cert["serial_number"],
            "public_key": "a" * 128,
        },
        headers=HEADERS, timeout=10,
    )
    _assert(reg_resp.status_code == 200, f"车辆注册 HTTP 200（实际 {reg_resp.status_code}）")
    reg = reg_resp.json()
    _assert("session_id" in reg, "返回 session_id")
    print(f"    session_id={reg['session_id'][:16]}...")

    return vehicle_id


def test_audit_log(vehicle_id):
    """测试 2：审计日志查询 → 注册事件应已记录"""
    print("\n[测试2] 审计日志查询")
    time.sleep(1)  # 等待日志落库
    resp = requests.get(
        f"{GATEWAY_URL}/api/audit/logs",
        params={"vehicle_id": vehicle_id, "page_size": 20},
        headers=HEADERS, timeout=10,
    )
    _assert(resp.status_code == 200, f"审计查询 HTTP 200（实际 {resp.status_code}）")
    data = resp.json()
    logs = data.get("logs") or data.get("items") or []
    _assert(len(logs) > 0, f"车辆 {vehicle_id} 的审计日志非空（{len(logs)} 条）")


def test_security_config():
    """测试 3：安全配置读取/更新/持久化"""
    print("\n[测试3] 安全配置读取与更新")
    r1 = requests.get(f"{GATEWAY_URL}/api/config/security", headers=HEADERS, timeout=10)
    _assert(r1.status_code == 200, f"读取配置 HTTP 200（实际 {r1.status_code}）")
    body = r1.json()
    orig = body.get("policy", body)
    print(f"    原 session_timeout={orig.get('session_timeout')}")

    new_timeout = (orig.get("session_timeout") or 3600) + 60
    payload = {**orig, "session_timeout": new_timeout}
    r2 = requests.put(
        f"{GATEWAY_URL}/api/config/security",
        json=payload,
        headers=HEADERS, timeout=10,
    )
    _assert(r2.status_code == 200, f"更新配置 HTTP 200（实际 {r2.status_code}）")

    r3 = requests.get(f"{GATEWAY_URL}/api/config/security", headers=HEADERS, timeout=10)
    body3 = r3.json()
    cur = body3.get("policy", body3)
    _assert(cur.get("session_timeout") == new_timeout,
            f"配置已持久化（新值={new_timeout}，实际={cur.get('session_timeout')}）")


def test_auth_required():
    """测试 4：Authorization 头访问控制"""
    print("\n[测试4] 无 Token 应被拒绝")
    r = requests.get(f"{GATEWAY_URL}/api/config/security", timeout=10)
    _assert(r.status_code in (401, 403), f"无 Token 返回 401/403（实际 {r.status_code}）")


if __name__ == "__main__":
    print("=" * 60)
    print("  功能验证测试 (8.2)")
    print(f"  Gateway: {GATEWAY_URL}")
    print("=" * 60)
    try:
        vid = test_vehicle_register()
        test_audit_log(vid)
        test_security_config()
        test_auth_required()
        print("\n" + "=" * 60)
        print("  ✓ 所有功能验证测试通过")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ 测试失败：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试异常：{e}")
        sys.exit(2)
