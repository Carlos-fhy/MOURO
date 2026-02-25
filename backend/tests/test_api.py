# API 集成测试 —— 验证认证、数据加载、求解、对比接口的完整流程
import json
import time
import os

import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture
def app():
    """创建测试用 Flask 应用"""
    import app.data.routes as data_mod
    data_mod._current_dataset = None
    test_app = create_app(TestConfig)
    yield test_app
    data_mod._current_dataset = None


@pytest.fixture
def client(app):
    """Flask 测试客户端"""
    return app.test_client()


def _get_token(client):
    """登录获取 JWT token"""
    resp = client.post("/api/auth/login", json={
        "username": "admin", "password": "mouro2026"
    })
    data = resp.get_json()
    return data["data"]["token"]


def _auth_header(token):
    """构建认证请求头"""
    return {"Authorization": f"Bearer {token}"}


# ── 认证接口测试 ──

class TestAuth:
    def test_login_success(self, client):
        """正确用户名密码登录成功"""
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "mouro2026"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "token" in data["data"]

    def test_login_wrong_password(self, client):
        """错误密码返回 401"""
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert resp.status_code == 401

    def test_protected_without_token(self, client):
        """无 token 访问受保护接口返回 401"""
        resp = client.get("/api/data/solomon/list")
        assert resp.status_code == 401


# ── 数据接口测试 ──

class TestDataAPI:
    def test_solomon_list(self, client):
        """获取 Solomon 算例列表"""
        token = _get_token(client)
        resp = client.get("/api/data/solomon/list",
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["data"]["instances"], list)

    def test_load_solomon_c101(self, client):
        """加载 Solomon C101 数据集"""
        token = _get_token(client)
        resp = client.post("/api/data/load",
                           json={"mode": "solomon", "instance": "c101"},
                           headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["customer_count"] == 100

    def test_load_nonexistent(self, client):
        """加载不存在的算例返回 404"""
        token = _get_token(client)
        resp = client.post("/api/data/load",
                           json={"mode": "solomon", "instance": "zzz999"},
                           headers=_auth_header(token))
        assert resp.status_code == 404


# ── 求解接口测试 ──

class TestSolveAPI:
    def _load_data(self, client, token):
        """辅助：先加载 C101 数据"""
        client.post("/api/data/load",
                    json={"mode": "solomon", "instance": "c101"},
                    headers=_auth_header(token))

    def test_start_without_data(self, client):
        """未加载数据时启动求解返回 400"""
        token = _get_token(client)
        resp = client.post("/api/solve/start",
                           json={"algorithm": "improved_aco"},
                           headers=_auth_header(token))
        assert resp.status_code == 400

    def test_start_and_get_result(self, client):
        """启动求解并获取结果（小迭代数快速验证）"""
        token = _get_token(client)
        self._load_data(client, token)

        resp = client.post("/api/solve/start", json={
            "algorithm": "improved_aco",
            "lambdas": [0.4, 0.3, 0.3],
            "Q": 1000,
            "params": {
                "max_iterations": 3,
                "ant_count": 3,
                "patience": 2,
            },
        }, headers=_auth_header(token))

        assert resp.status_code == 200
        task_id = resp.get_json()["data"]["task_id"]
        assert task_id

        # 轮询等待任务完成
        for _ in range(60):
            time.sleep(0.5)
            resp = client.get(
                f"/api/solve/result/{task_id}",
                headers=_auth_header(token))
            if resp.status_code == 200:
                break

        data = resp.get_json()
        assert data["success"] is True
        assert len(data["data"]["routes"]) > 0
        assert data["data"]["f1"] > 0
