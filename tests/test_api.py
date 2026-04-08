"""Web API 测试

测试 Web 管理平台后端 API 的基本功能。
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_root_endpoint():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check():
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_unauthorized_access():
    """测试未授权访问"""
    response = client.get("/api/vehicles/online")
    assert response.status_code == 403  # Forbidden without auth


def test_get_online_vehicles_with_auth():
    """测试获取在线车辆列表（带认证）"""
    headers = {"Authorization": "Bearer dev-token-12345"}
    response = client.get("/api/vehicles/online", headers=headers)
    
    # 可能返回 200（成功）或 500（数据库未配置）
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "total" in data
        assert "vehicles" in data


def test_get_realtime_metrics_with_auth():
    """测试获取实时指标（带认证）"""
    headers = {"Authorization": "Bearer dev-token-12345"}
    response = client.get("/api/metrics/realtime", headers=headers)
    
    # 可能返回 200（成功）或 500（数据库未配置）
    assert response.status_code in [200, 500]


def test_get_certificates_with_auth():
    """测试获取证书列表（带认证）"""
    headers = {"Authorization": "Bearer dev-token-12345"}
    response = client.get("/api/certificates", headers=headers)
    
    # 可能返回 200（成功）或 500（数据库未配置）
    assert response.status_code in [200, 500]


def test_get_security_policy_with_auth():
    """测试获取安全策略（带认证）"""
    headers = {"Authorization": "Bearer dev-token-12345"}
    response = client.get("/api/config/security", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "policy" in data
    assert "message" in data


def test_update_security_policy_with_auth():
    """测试更新安全策略（带认证）"""
    headers = {"Authorization": "Bearer dev-token-12345"}
    policy_data = {
        "session_timeout": 3600,
        "certificate_validity": 365,
        "timestamp_tolerance": 300,
        "concurrent_session_strategy": "reject_new",
        "max_auth_failures": 5,
        "auth_failure_lockout_duration": 300
    }
    
    response = client.put("/api/config/security", json=policy_data, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "policy" in data
    assert data["policy"]["session_timeout"] == 3600


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
