# Solomon 解析器单元测试
import os
import sys
import pytest

# 将 backend 目录加入 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data.solomon_parser import (
    parse_solomon_file,
    assign_emergency_levels,
    get_solomon_instances,
)

# Solomon 数据目录
SOLOMON_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "solomon")


def _get_c101_path():
    """获取 C101 文件路径，不存在则跳过测试"""
    path = os.path.join(SOLOMON_DIR, "c101.txt")
    if not os.path.exists(path):
        pytest.skip("c101.txt 未下载，请先运行 download_solomon.py")
    return path


class TestParseSolomonFile:
    """测试 Solomon 文件解析"""

    def test_c101_node_count(self):
        """验证 C101 解析后客户数为 100（加 depot 共 101 个节点）"""
        path = _get_c101_path()
        result = parse_solomon_file(path)
        assert len(result["customers"]) == 100

    def test_c101_depot_coords(self):
        """验证 C101 depot 坐标为 (40, 50)"""
        path = _get_c101_path()
        result = parse_solomon_file(path)
        depot = result["depot"]
        assert depot["x_coord"] == 40
        assert depot["y_coord"] == 50

    def test_c101_t_max(self):
        """验证 C101 的 T_max = depot 的 late_time = 1236"""
        path = _get_c101_path()
        result = parse_solomon_file(path)
        assert result["t_max"] == 1236

    def test_c101_vehicle_capacity(self):
        """验证 C101 车辆容量为 200"""
        path = _get_c101_path()
        result = parse_solomon_file(path)
        assert result["vehicle_capacity"] == 200

    def test_customer_fields_complete(self):
        """验证每个客户节点包含所有必要字段"""
        path = _get_c101_path()
        result = parse_solomon_file(path)
        required_fields = [
            "id", "x_coord", "y_coord", "demand",
            "early_time", "late_time", "service_time", "type",
        ]
        for c in result["customers"]:
            for field in required_fields:
                assert field in c, f"客户缺少字段: {field}"


class TestAssignEmergencyLevels:
    """测试应急等级分配"""

    def test_all_customers_assigned(self):
        """验证所有客户都被分配了应急等级"""
        path = _get_c101_path()
        result = parse_solomon_file(path)
        customers = assign_emergency_levels(result["customers"])
        for c in customers:
            assert "emergency_level" in c
            assert "emergency_weight" in c

    def test_level_distribution(self):
        """验证应急等级分布比例大致正确（10% medical, 20% fresh, 70% normal）"""
        path = _get_c101_path()
        result = parse_solomon_file(path)
        customers = assign_emergency_levels(result["customers"])
        n = len(customers)

        counts = {"medical": 0, "fresh": 0, "normal": 0}
        for c in customers:
            counts[c["emergency_level"]] += 1

        # 允许 ±2 的误差
        assert abs(counts["medical"] - round(n * 0.10)) <= 2
        assert abs(counts["fresh"] - round(n * 0.20)) <= 2

    def test_weight_values(self):
        """验证应急权重值正确"""
        path = _get_c101_path()
        result = parse_solomon_file(path)
        customers = assign_emergency_levels(result["customers"])
        weight_map = {"medical": 2.0, "fresh": 1.5, "normal": 1.0}
        for c in customers:
            assert c["emergency_weight"] == weight_map[c["emergency_level"]]

    def test_medical_has_narrowest_windows(self):
        """验证 medical 等级的客户拥有最窄的时间窗"""
        path = _get_c101_path()
        result = parse_solomon_file(path)
        customers = assign_emergency_levels(result["customers"])

        medical_widths = [
            c["late_time"] - c["early_time"]
            for c in customers if c["emergency_level"] == "medical"
        ]
        normal_widths = [
            c["late_time"] - c["early_time"]
            for c in customers if c["emergency_level"] == "normal"
        ]
        # medical 的平均时间窗宽度应小于 normal
        assert sum(medical_widths) / len(medical_widths) < sum(normal_widths) / len(normal_widths)


class TestGetSolomonInstances:
    """测试算例列表扫描"""

    def test_returns_list(self):
        """验证返回列表类型"""
        result = get_solomon_instances(SOLOMON_DIR)
        assert isinstance(result, list)

    def test_instance_format(self):
        """验证每个实例包含 name 和 filename 字段"""
        result = get_solomon_instances(SOLOMON_DIR)
        for inst in result:
            assert "name" in inst
            assert "filename" in inst

    def test_nonexistent_dir(self):
        """验证不存在的目录返回空列表"""
        result = get_solomon_instances("/nonexistent/path")
        assert result == []
