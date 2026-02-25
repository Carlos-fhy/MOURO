# 缺失字段生成器单元测试
import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data.field_generator import generate_fields


def _make_test_customers(n=20):
    """构造测试用客户列表和距离矩阵"""
    customers = [
        {"id": i + 1, "x_coord": float(i * 10), "y_coord": float(i * 5), "type": "customer"}
        for i in range(n)
    ]
    # 构造简单距离矩阵（含 depot，共 n+1 个节点）
    size = n + 1
    dist = np.zeros((size, size))
    for i in range(size):
        for j in range(size):
            dist[i][j] = abs(i - j) * 10.0
    return customers, dist


class TestGenerateFields:
    """测试缺失字段生成"""

    def test_all_fields_present(self):
        """验证生成后每个客户包含所有必要字段"""
        customers, dist = _make_test_customers()
        generate_fields(customers, dist)
        required = [
            "emergency_level", "emergency_weight",
            "demand_weight", "service_time",
            "early_time", "late_time",
        ]
        for c in customers:
            for field in required:
                assert field in c, f"客户 {c['id']} 缺少字段: {field}"

    def test_demand_range(self):
        """验证需求量在 [10, 200] 范围内"""
        customers, dist = _make_test_customers(50)
        generate_fields(customers, dist)
        for c in customers:
            assert 10 <= c["demand_weight"] <= 200, (
                f"客户 {c['id']} 需求量 {c['demand_weight']} 超出范围"
            )

    def test_emergency_ratio(self):
        """验证应急等级比例大致符合设定"""
        customers, dist = _make_test_customers(100)
        ratio = {"medical": 10, "fresh": 20, "normal": 70}
        generate_fields(customers, dist, emergency_ratio=ratio)

        counts = {"medical": 0, "fresh": 0, "normal": 0}
        for c in customers:
            counts[c["emergency_level"]] += 1

        assert counts["medical"] == 10
        assert counts["fresh"] == 20
        assert counts["normal"] == 70

    def test_time_window_valid(self):
        """验证时间窗合理性: early_time < late_time"""
        customers, dist = _make_test_customers()
        generate_fields(customers, dist)
        for c in customers:
            assert c["early_time"] < c["late_time"], (
                f"客户 {c['id']} 时间窗不合理: ET={c['early_time']} >= LT={c['late_time']}"
            )

    def test_service_time_formula(self):
        """验证服务时间公式: s_i = 5 + 0.1 × q_i"""
        customers, dist = _make_test_customers()
        generate_fields(customers, dist)
        for c in customers:
            expected = 5.0 + 0.1 * c["demand_weight"]
            assert abs(c["service_time"] - expected) < 0.01

    def test_reproducibility(self):
        """验证相同种子产生相同结果"""
        c1, d1 = _make_test_customers()
        c2, d2 = _make_test_customers()
        generate_fields(c1, d1, seed=123)
        generate_fields(c2, d2, seed=123)
        for a, b in zip(c1, c2):
            assert a["demand_weight"] == b["demand_weight"]
            assert a["emergency_level"] == b["emergency_level"]
