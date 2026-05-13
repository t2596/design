"""安全测试（8.4）

验证系统在异常/攻击场景下的安全防护能力（5 类用例）：
  1. 未授权访问拒绝
  2. 无效 Token 拒绝
  3. 过期时间戳拒绝（防重放）
  4. 重复 Nonce 拒绝（防重放）
  5. 签名篡改拒绝

测试 3/4/5 会先完整注册一个合法车辆，拿到真实 session_id 与 session_key 后
再构造恶意报文，确保请求真的走到签名/时间戳/Nonce 校验分支。
"""

import os
import sys
import time
import uuid
import requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.crypto.sm2 import generate_sm2_keypair, sm2_sign  # noqa: E402
from src.crypto.sm4 import sm4_encrypt  # noqa: E402
from src.models.message import SecureMessage, MessageHeader, MessageType  # noqa: E402

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_TOKEN", "dev-token-12345")
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


def _check(cond, name, detail=""):
    status = "✓" if cond else "✗"
    print(f"  {status} {name}")
    if detail:
        print(f"      └─ {detail}")
    return cond


def _short(text, n=200):
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= n else text[:n] + "..."


def _setup_real_session():
    """注册一辆合法车辆，返回真实的加密上下文。

    返回: dict(vehicle_id, session_id, session_key, vehicle_priv, vehicle_pub, gateway_pub)
    """
    vid = f"SEC_{uuid.uuid4().hex[:8]}"
    priv, pub = generate_sm2_keypair()

    # 证书颁发
    issue = requests.post(
        f"{GATEWAY_URL}/api/certificates/issue",
        json={"vehicle_id": vid, "organization": "SecTest", "country": "CN",
              "public_key": pub.hex()},
        headers=HEADERS, timeout=10,
    )
    if issue.status_code != 200:
        raise RuntimeError(f"证书颁发失败: {issue.status_code} {issue.text}")
    serial = issue.json()["serial_number"]

    # 注册（public_key 必须传真实 pubkey 的 hex，网关会保存到 Redis 用于后续验签）
    reg = requests.post(
        f"{GATEWAY_URL}/api/auth/register",
        json={"vehicle_id": vid, "certificate_serial": serial, "public_key": pub.hex()},
        headers=HEADERS, timeout=10,
    )
    if reg.status_code != 200:
        raise RuntimeError(f"车辆注册失败: {reg.status_code} {reg.text}")
    data = reg.json()
    return {
        "vehicle_id": vid,
        "session_id": data["session_id"],
        "session_key": bytes.fromhex(data["session_key"]),
        "vehicle_priv": priv,
        "vehicle_pub": pub,
        "gateway_pub": bytes.fromhex(data["gateway_public_key"]),
    }


def _build_legal_secure_msg(ctx, plain=b'{"speed":60}', timestamp=None):
    """手工构造合法的 SecureMessage。

    用 datetime.utcnow() 匹配网关 Pod 内的 UTC 时区，避免客户端本地时区（如 CST）
    与 Pod 时区差异导致时间戳超出 ±5 分钟容差。
    """
    header = MessageHeader(
        version=1, message_type=MessageType.DATA_TRANSFER,
        sender_id=ctx["vehicle_id"], receiver_id="gateway",
        session_id=ctx["session_id"],
    )
    nonce = os.urandom(16)
    ts = timestamp or datetime.utcnow()
    encrypted = sm4_encrypt(plain, ctx["session_key"])

    # 与服务端 verify_and_decrypt_message 保持一致的待签名字节序列
    header_bytes = str(header.to_dict()).encode("utf-8")
    ts_bytes = ts.isoformat().encode("utf-8")
    data_to_sign = header_bytes + encrypted + ts_bytes + nonce
    signature = sm2_sign(data_to_sign, ctx["vehicle_priv"])

    return SecureMessage(
        header=header, encrypted_payload=encrypted,
        signature=signature, timestamp=ts, nonce=nonce,
    )


def _msg_to_dict(msg: SecureMessage) -> dict:
    return {
        "header": msg.header.to_dict(),
        "encrypted_payload": msg.encrypted_payload.hex(),
        "signature": msg.signature.hex(),
        "timestamp": msg.timestamp.isoformat(),
        "nonce": msg.nonce.hex(),
    }


def _post_secure(ctx, body):
    return requests.post(
        f"{GATEWAY_URL}/api/auth/data/secure",
        params={"vehicle_id": ctx["vehicle_id"], "session_id": ctx["session_id"]},
        json=body, headers=HEADERS, timeout=10,
    )


# ---------- 测试用例 ----------

def test_no_auth():
    print("\n[测试1] 未授权访问")
    url = f"{GATEWAY_URL}/api/config/security"
    print(f"  → GET {url}  (不携带 Authorization)")
    r = requests.get(url, timeout=5)
    print(f"  ← HTTP {r.status_code}")
    return _check(
        r.status_code in (401, 403),
        f"鉴权中间件拦截无 Token 请求（期望 401/403，实际 {r.status_code}）",
        detail=_short(r.text),
    )


def test_invalid_token():
    print("\n[测试2] 无效 Token")
    url = f"{GATEWAY_URL}/api/config/security"
    print(f"  → GET {url}  Authorization=Bearer FAKE_TOKEN_XXX")
    r = requests.get(url, headers={"Authorization": "Bearer FAKE_TOKEN_XXX"}, timeout=5)
    print(f"  ← HTTP {r.status_code}")
    return _check(
        r.status_code in (401, 403),
        f"伪造 Token 被拒绝（期望 401/403，实际 {r.status_code}）",
        detail=_short(r.text),
    )


def test_expired_timestamp():
    """用合法会话 + 早 10 分钟的时间戳（签名一致），期望 400 时间戳超差"""
    print("\n[测试3] 过期时间戳（防重放）")
    ctx = _setup_real_session()
    print(f"  → 合法 session_id={ctx['session_id'][:8]}...  构造时间戳=UTC当前-10分钟")
    old_ts = datetime.utcnow() - timedelta(minutes=10)
    msg = _build_legal_secure_msg(ctx, timestamp=old_ts)
    r = _post_secure(ctx, _msg_to_dict(msg))
    print(f"  ← HTTP {r.status_code}")
    return _check(
        r.status_code == 400 and "timestamp" in r.text.lower(),
        f"网关拒绝过期报文（期望 400 Invalid timestamp）",
        detail=_short(r.text),
    )


def test_replay_nonce():
    """相同报文连续提交两次，第二次应被 Nonce 重放检测拦住"""
    print("\n[测试4] 重复 Nonce（防重放）")
    ctx = _setup_real_session()
    msg = _build_legal_secure_msg(ctx)
    body = _msg_to_dict(msg)
    print(f"  → 首次提交 nonce={body['nonce'][:16]}...")
    r1 = _post_secure(ctx, body)
    print(f"  ← 首次 HTTP {r1.status_code}  {_short(r1.text, 80)}")
    print(f"  → 使用相同 nonce 重放")
    r2 = _post_secure(ctx, body)
    print(f"  ← 重放 HTTP {r2.status_code}")
    replay_blocked = r2.status_code == 400 and (
        "nonce" in r2.text.lower() or "重放" in r2.text or "已使用" in r2.text
    )
    return _check(
        replay_blocked,
        f"重放报文被 Redis Nonce 唯一性检查拦截（期望 400 Nonce相关错误）",
        detail=_short(r2.text),
    )


def test_tampered_signature():
    """合法会话下，篡改签名应返回 400 签名验证失败"""
    print("\n[测试5] 签名篡改")
    ctx = _setup_real_session()
    msg = _build_legal_secure_msg(ctx)
    body = _msg_to_dict(msg)
    print(f"  → 构造合法报文，将 signature 替换为全 '11'*64")
    body["signature"] = ("11" * 64)
    r = _post_secure(ctx, body)
    print(f"  ← HTTP {r.status_code}")
    fail_reason_ok = "signature" in r.text.lower() or "签名" in r.text
    return _check(
        r.status_code == 400 and fail_reason_ok,
        f"SM2 验签拒绝篡改报文（期望 400 签名验证失败）",
        detail=_short(r.text),
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  安全测试 (8.4)")
    print(f"  Gateway: {GATEWAY_URL}")
    print("=" * 60)

    tests = [
        test_no_auth, test_invalid_token, test_expired_timestamp,
        test_replay_nonce, test_tampered_signature,
    ]
    passed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__} 异常: {e}")

    print("\n" + "=" * 60)
    print(f"  通过 {passed} / {len(tests)} 个安全测试用例")
    print("=" * 60)
    sys.exit(0 if passed == len(tests) else 1)
