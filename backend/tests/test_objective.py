# 目标函数单元测试 —— 用手算小算例验证 F1/F2'/F3/Z
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.objective import (
    calculate_f1, calculate_f2, calculate_f3,
    build_schedule, calculate_z, evaluate_solution,
)
from app.utils.normalize import min_max_normalize


# ---- 测试用小算例：1 depot + 3 customers ----
# 坐标: depot(0,0), C1(3,0), C2(0,4), C3(3,4)
# 距离矩阵 (4x4):
#       D    C1   C2   C3
#  D  [ 0,   3,   4,   5  ]
#  C1 [ 3,   0,   5,   4  ]
#  C2 [ 4,   5,   0,   3  ]
#  C3 [ 5,   4,   3,   0  ]

DIST = np.array([
    [0, 3, 4, 5],
    [3, 0, 5, 4],
    [4, 5, 0, 3],
    [5, 4, 3, 0],
], dtype=float)

ID_TO_IDX = {0: 0, 1: 1, 2: 2, 3: 3}

CUSTOMERS = [
    {"id": 1, "emergency_level": "medical", "emergency_weight": 2.0,
     "early_time": 5, "late_time": 20, "service_time": 10, "demand": 30},
    {"id": 2, "emergency_level": "fresh", "emergency_weight": 1.5,
     "early_time": 2, "late_time": 30, "service_time": 8, "demand": 50},
    {"id": 3, "emergency_level": "normal", "emergency_weight": 1.0,
     "early_time": 0, "late_time": 50, "service_time": 5, "demand": 20},
]

CUSTOMERS_DICT = {c["id"]: c for c in CUSTOMERS}

DEPOT = {"id": 0, "x_coord": 0, "y_coord": 0}


# ---- 归一化测试 ----

def test_normalize_normal():
    """正常归一化"""
    assert min_max_normalize(5, 0, 10) == 0.5

def test_normalize_zero_range():
    """除零保护：max == min 时返回 0"""
    assert min_max_normalize(5, 5, 5) == 0.0

def test_normalize_boundary():
    """边界值"""
    assert min_max_normalize(0, 0, 10) == 0.0
    assert min_max_normalize(10, 0, 10) == 1.0


# ---- F1 测试 ----

def test_f1_single_route():
    """单条路线 F1 = 固定成本 + 距离成本
    路线: 0→1→3→0, 距离 = 3+4+5 = 12, F1 = 200 + 12*5 = 260
    """
    routes = [[0, 1, 3, 0]]
    f1 = calculate_f1(routes, DIST, ID_TO_IDX, fixed_cost=200, cost_per_km=5.0)
    assert f1 == 260.0

def test_f1_two_routes():
    """两条路线 F1 = 2*固定 + 总距离成本
    路线1: 0→1→0, 距离=3+3=6
    路线2: 0→2→3→0, 距离=4+3+5=12
    F1 = 2*200 + (6+12)*5 = 490
    """
    routes = [[0, 1, 0], [0, 2, 3, 0]]
    f1 = calculate_f1(routes, DIST, ID_TO_IDX, fixed_cost=200, cost_per_km=5.0)
    assert f1 == 490.0


# ---- build_schedule 测试 ----

def test_schedule_on_time():
    """准时到达：depot→C3(到达5, ET=0, LT=50) → 无惩罚"""
    routes = [[0, 3, 0]]
    sched = build_schedule(routes, CUSTOMERS_DICT, DIST, ID_TO_IDX)
    assert len(sched) == 1
    assert sched[0]["status"] == "on_time"
    assert sched[0]["penalty"] == 0.0
    assert sched[0]["arrival_time"] == 5.0  # d(0,3)=5

def test_schedule_medical_early_wait():
    """医疗客户早到等待：depot→C1, 到达时间=3, ET=5, 硬时间窗等待"""
    routes = [[0, 1, 0]]
    sched = build_schedule(routes, CUSTOMERS_DICT, DIST, ID_TO_IDX)
    assert sched[0]["status"] == "early"
    assert sched[0]["penalty"] == 0.0  # 硬时间窗等待不惩罚
    assert sched[0]["departure_time"] == 15.0  # ET(5) + service(10)

def test_schedule_soft_early_penalty():
    """生鲜客户早到惩罚：depot→C2, 到达=4, ET=2 → 准时无惩罚
    改用自定义场景：ET=10, 到达=4, 早到惩罚 = α_base*ω*(ET-t) = 1.0*1.5*6 = 9.0
    """
    custom_dict = {2: {"id": 2, "emergency_level": "fresh", "emergency_weight": 1.5,
                       "early_time": 10, "late_time": 30, "service_time": 8, "demand": 50}}
    routes = [[0, 2, 0]]
    sched = build_schedule(routes, custom_dict, DIST, ID_TO_IDX)
    assert sched[0]["status"] == "early"
    assert sched[0]["penalty"] == 9.0


# ---- F2 测试 ----

def test_f2_weighted_time():
    """F2' = Σ(ω_ei × t_arrive_i)
    路线: 0→1→3→0
    C1: 到达=3, 硬时间窗等待到5, ω=2.0 → 2.0*3=6.0
    C3: 到达=15+4=19(departure_C1=15, travel=4), ω=1.0 → 1.0*19=19.0
    F2' = 6.0 + 19.0 = 25.0
    """
    routes = [[0, 1, 3, 0]]
    sched = build_schedule(routes, CUSTOMERS_DICT, DIST, ID_TO_IDX)
    f2 = calculate_f2(sched, CUSTOMERS_DICT)
    assert f2 == 25.0


# ---- F3 测试 ----

def test_f3_no_penalty():
    """全部准时到达，F3=0"""
    routes = [[0, 3, 0]]
    sched = build_schedule(routes, CUSTOMERS_DICT, DIST, ID_TO_IDX)
    f3 = calculate_f3(sched, CUSTOMERS_DICT)
    assert f3 == 0.0


# ---- Z 测试 ----

def test_z_equal_weights():
    """等权重 λ=[1/3,1/3,1/3]，所有目标归一化后取平均"""
    z = calculate_z(
        f1=50, f2=30, f3=10,
        f1_bounds=(0, 100), f2_bounds=(0, 60), f3_bounds=(0, 20),
        lambdas=[1/3, 1/3, 1/3]
    )
    # F1*=0.5, F2*=0.5, F3*=0.5 → Z=0.5
    assert abs(z - 0.5) < 1e-9

def test_z_single_objective():
    """单目标 λ=[1,0,0]，Z = F1*"""
    z = calculate_z(
        f1=75, f2=999, f3=999,
        f1_bounds=(50, 100), f2_bounds=(0, 1000), f3_bounds=(0, 1000),
        lambdas=[1, 0, 0]
    )
    assert abs(z - 0.5) < 1e-9


# ---- evaluate_solution 综合测试 ----

def test_evaluate_solution_complete():
    """验证一站式评估返回所有字段"""
    routes = [[0, 1, 3, 0], [0, 2, 0]]
    params = {
        "lambdas": [0.33, 0.33, 0.34],
        "alpha_base": 1.0, "beta_base": 2.0,
        "fixed_cost": 200, "cost_per_km": 5.0,
    }
    result = evaluate_solution(
        routes, CUSTOMERS, DEPOT, DIST, DIST, ID_TO_IDX, params
    )
    assert "f1" in result
    assert "f2" in result
    assert "f3" in result
    assert "schedule" in result
    assert result["vehicles_used"] == 2
    assert result["f1"] > 0
    assert len(result["schedule"]) == 3  # 3个客户
