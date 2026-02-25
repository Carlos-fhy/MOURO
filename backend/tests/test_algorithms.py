# 算法集成测试 —— 5节点小算例验证所有算法输出格式和基本正确性
import numpy as np
import pytest
from app.algorithm.base import SolutionResult


# ── 测试夹具：1 depot + 4 customers ──

@pytest.fixture
def small_instance():
    """构造 5 节点小算例（1 depot + 4 customers）

    布局:
        depot(0,0), c1(10,0), c2(0,10), c3(10,10), c4(5,5)
    应急等级:
        c1=medical, c2=fresh, c3=normal, c4=normal
    """
    depot = {
        "id": 0, "x": 0, "y": 0,
        "early_time": 0, "late_time": 9999, "service_time": 0,
        "demand": 0, "emergency_level": "normal",
    }
    customers = [
        {"id": 1, "x": 10, "y": 0, "demand": 30,
         "early_time": 0, "late_time": 200, "service_time": 10,
         "emergency_level": "medical"},
        {"id": 2, "x": 0, "y": 10, "demand": 20,
         "early_time": 0, "late_time": 9999, "service_time": 10,
         "emergency_level": "fresh"},
        {"id": 3, "x": 10, "y": 10, "demand": 25,
         "early_time": 0, "late_time": 9999, "service_time": 10,
         "emergency_level": "normal"},
        {"id": 4, "x": 5, "y": 5, "demand": 15,
         "early_time": 0, "late_time": 9999, "service_time": 10,
         "emergency_level": "normal"},
    ]

    nodes = [depot] + customers
    n = len(nodes)
    coords = np.array([[nd["x"], nd["y"]] for nd in nodes], dtype=float)
    diff = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))

    params = {
        "vehicle_capacity": 100,
        "max_iterations": 10,
        "ant_count": 5,
        "alpha": 1.0, "beta": 2.0,
        "gamma": 1.0, "delta": 2.0,
        "rho_cost": 0.1, "rho_time": 0.1,
        "alpha_base": 1.0, "beta_base": 2.0,
        "fixed_cost": 200, "cost_per_km": 5.0,
        "lambda1": 0.4, "lambda2": 0.3, "lambda3": 0.3,
        "patience": 5, "early_stop_threshold": 1e-6,
        "seed": 42,
        # GA 参数
        "pop_size": 10, "crossover_rate": 0.8, "mutation_rate": 0.2,
        # SA 参数
        "initial_temp": 100, "cooling_rate": 0.95, "min_temp": 0.1,
    }

    return depot, customers, dist, dist, params


def _validate_result(result, customers):
    """通用校验：验证 SolutionResult 字段完整性和基本正确性"""
    assert isinstance(result, SolutionResult)
    assert result.routes, "路线不能为空"
    assert result.f1 >= 0, "F1（成本）不能为负"
    assert result.f2 >= 0, "F2'（加权完工时间）不能为负"
    assert result.f3 >= 0, "F3（惩罚）不能为负"
    assert result.vehicles_used >= 1, "至少使用 1 辆车"
    assert isinstance(result.schedule, list)
    assert isinstance(result.unreachable, list)

    # 验证所有客户都被访问（排除不可达的）
    visited = set()
    for route in result.routes:
        for nid in route[1:-1]:  # 去掉首尾 depot
            visited.add(nid)
    expected = set(c["id"] for c in customers) - set(result.unreachable)
    assert visited == expected, f"未访问客户: {expected - visited}"


# ── 改进蚁群算法测试 ──

class TestImprovedACO:
    def test_solve_returns_valid_result(self, small_instance):
        """改进ACO：输出格式完整且所有客户被访问"""
        from app.algorithm.improved_aco import ImprovedACO
        depot, customers, dist, time_mat, params = small_instance
        solver = ImprovedACO(customers, depot, dist, time_mat, params)
        result = solver.solve()
        _validate_result(result, customers)

    def test_convergence_recorded(self, small_instance):
        """改进ACO：收敛曲线非空"""
        from app.algorithm.improved_aco import ImprovedACO
        depot, customers, dist, time_mat, params = small_instance
        solver = ImprovedACO(customers, depot, dist, time_mat, params)
        result = solver.solve()
        assert len(result.convergence) > 0, "收敛曲线不能为空"

    def test_callback_invoked(self, small_instance):
        """改进ACO：回调函数被调用"""
        from app.algorithm.improved_aco import ImprovedACO
        depot, customers, dist, time_mat, params = small_instance
        solver = ImprovedACO(customers, depot, dist, time_mat, params)
        msgs = []
        result = solver.solve(callback=lambda m: msgs.append(m))
        assert len(msgs) > 0, "回调应至少被调用一次"
        assert msgs[0]["type"] == "progress"


# ── 标准蚁群算法测试 ──

class TestStandardACO:
    def test_solve_returns_valid_result(self, small_instance):
        """标准ACO：输出格式完整且所有客户被访问"""
        from app.algorithm.standard_aco import StandardACO
        depot, customers, dist, time_mat, params = small_instance
        solver = StandardACO(customers, depot, dist, time_mat, params)
        result = solver.solve()
        _validate_result(result, customers)

    def test_convergence_recorded(self, small_instance):
        """标准ACO：收敛曲线非空"""
        from app.algorithm.standard_aco import StandardACO
        depot, customers, dist, time_mat, params = small_instance
        solver = StandardACO(customers, depot, dist, time_mat, params)
        result = solver.solve()
        assert len(result.convergence) > 0


# ── 遗传算法测试 ──

class TestGeneticAlgorithm:
    def test_solve_returns_valid_result(self, small_instance):
        """GA：输出格式完整且所有客户被访问"""
        from app.algorithm.genetic import GeneticAlgorithm
        depot, customers, dist, time_mat, params = small_instance
        solver = GeneticAlgorithm(customers, depot, dist, time_mat, params)
        result = solver.solve()
        _validate_result(result, customers)

    def test_convergence_recorded(self, small_instance):
        """GA：收敛曲线非空"""
        from app.algorithm.genetic import GeneticAlgorithm
        depot, customers, dist, time_mat, params = small_instance
        solver = GeneticAlgorithm(customers, depot, dist, time_mat, params)
        result = solver.solve()
        assert len(result.convergence) > 0


# ── 模拟退火算法测试 ──

class TestSimulatedAnnealing:
    def test_solve_returns_valid_result(self, small_instance):
        """SA：输出格式完整且所有客户被访问"""
        from app.algorithm.simulated_annealing import SimulatedAnnealing
        depot, customers, dist, time_mat, params = small_instance
        solver = SimulatedAnnealing(customers, depot, dist, time_mat, params)
        result = solver.solve()
        _validate_result(result, customers)

    def test_convergence_recorded(self, small_instance):
        """SA：收敛曲线非空"""
        from app.algorithm.simulated_annealing import SimulatedAnnealing
        depot, customers, dist, time_mat, params = small_instance
        solver = SimulatedAnnealing(customers, depot, dist, time_mat, params)
        result = solver.solve()
        assert len(result.convergence) > 0


# ── OR-Tools 精确求解器测试 ──

class TestORToolsSolver:
    def test_solve_returns_valid_result(self, small_instance):
        """OR-Tools：输出格式完整且所有客户被访问"""
        from app.algorithm.ortools_solver import ORToolsSolver
        depot, customers, dist, time_mat, params = small_instance
        solver = ORToolsSolver(customers, depot, dist, time_mat, params)
        result = solver.solve(time_limit_sec=10)
        _validate_result(result, customers)

    def test_no_convergence(self, small_instance):
        """OR-Tools：精确求解器无收敛曲线"""
        from app.algorithm.ortools_solver import ORToolsSolver
        depot, customers, dist, time_mat, params = small_instance
        solver = ORToolsSolver(customers, depot, dist, time_mat, params)
        result = solver.solve(time_limit_sec=10)
        assert result.convergence == []


# ── 跨算法对比测试 ──

class TestCrossAlgorithm:
    def test_all_algorithms_cover_same_customers(self, small_instance):
        """所有算法应访问相同的客户集合"""
        from app.algorithm.improved_aco import ImprovedACO
        from app.algorithm.standard_aco import StandardACO
        from app.algorithm.genetic import GeneticAlgorithm
        from app.algorithm.simulated_annealing import SimulatedAnnealing

        depot, customers, dist, time_mat, params = small_instance
        cust_ids = set(c["id"] for c in customers)

        results = {}
        for name, cls in [("improved_aco", ImprovedACO),
                          ("standard_aco", StandardACO),
                          ("ga", GeneticAlgorithm),
                          ("sa", SimulatedAnnealing)]:
            solver = cls(customers, depot, dist, time_mat, params)
            results[name] = solver.solve()

        for name, result in results.items():
            visited = set()
            for route in result.routes:
                for nid in route[1:-1]:
                    visited.add(nid)
            covered = visited | set(result.unreachable)
            assert covered == cust_ids, f"{name} 客户覆盖不完整"
