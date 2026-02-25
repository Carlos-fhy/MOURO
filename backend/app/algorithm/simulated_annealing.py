# 模拟退火算法 —— 基于 Metropolis 准则的单解邻域搜索优化
import math
import numpy as np

from app.algorithm.base import BaseAlgorithm, SolutionResult
from app.algorithm.greedy import GreedySolver
from app.algorithm.precheck import precheck_reachability
from app.utils.objective import (
    build_schedule,
    calculate_f1,
    calculate_f2,
    calculate_f3,
    calculate_z,
)


class SimulatedAnnealing(BaseAlgorithm):
    """模拟退火算法

    使用贪心解作为初始解，通过 swap/insert/reverse 三种邻域操作
    在客户排列上搜索，按 Metropolis 准则接受或拒绝新解。

    参数:
        customers: 客户列表
        depot: 配送中心
        distance_matrix: 距离矩阵
        time_matrix: 时间矩阵
        params: 算法参数字典
    """

    def __init__(self, customers, depot, distance_matrix,
                 time_matrix, params):
        """初始化模拟退火算法参数"""
        super().__init__(
            customers, depot, distance_matrix, time_matrix, params
        )
        # 退火参数
        self.initial_temperature = params.get(
            "initial_temperature", 1000
        )
        self.cooling_rate = params.get("cooling_rate", 0.995)
        self.min_temperature = params.get("min_temperature", 1e-3)
        self.seed = params.get("seed", 42)

        # 业务参数
        self.alpha_base = params.get("alpha_base", 1.0)
        self.beta_base = params.get("beta_base", 2.0)
        self.fixed_cost = params.get("fixed_cost", 200)
        self.cost_per_km = params.get("cost_per_km", 5.0)

    def solve(self, callback=None):
        """模拟退火主循环

        参数:
            callback: 每轮迭代回调函数，签名 callback(msg_dict)
        返回:
            SolutionResult 实例
        """
        rng = np.random.RandomState(self.seed)
        depot_id = self.depot["id"]

        # ---- 预检：剔除不可达的硬时间窗客户 ----
        reachable, unreachable = precheck_reachability(
            self.customers, self.depot,
            self.time_matrix, self.id_to_idx
        )
        unreachable_ids = [c["id"] for c in unreachable]
        working = reachable
        working_dict = {c["id"]: c for c in working}

        # ---- 贪心构造初始解 ----
        greedy = GreedySolver(
            working, self.depot,
            self.distance_matrix, self.time_matrix, self.params
        )
        greedy_result = greedy.solve()
        # 从贪心路线中提取客户排列（去掉 depot）
        current_seq = self._routes_to_sequence(
            greedy_result["routes"], depot_id
        )

        # ---- 评估初始解 ----
        current_routes = self._decode(current_seq)
        cur_f1, cur_f2, cur_f3 = self._evaluate(
            current_routes, working_dict
        )

        # 初始化 Min-Max 归一化边界（迭代中动态更新）
        f1_min, f1_max = cur_f1, cur_f1
        f2_min, f2_max = cur_f2, cur_f2
        f3_min, f3_max = cur_f3, cur_f3

        cur_z = 0.0  # 初始 z 在边界相等时为 0
        best_seq = current_seq[:]
        best_routes = current_routes
        best_f1, best_f2, best_f3, best_z = (
            cur_f1, cur_f2, cur_f3, cur_z
        )
        convergence = [(0, round(best_z, 6))]
        no_improve = 0

        # ---- 主循环：每次迭代 = 一次降温步骤 ----
        temperature = self.initial_temperature

        for iteration in range(1, self.max_iterations + 1):
            # 温度过低则提前终止
            if temperature < self.min_temperature:
                break

            # 生成邻域解
            new_seq = self._neighbor(current_seq, rng)
            new_routes = self._decode(new_seq)
            nf1, nf2, nf3 = self._evaluate(
                new_routes, working_dict
            )

            # 动态更新归一化边界
            f1_min = min(f1_min, nf1)
            f1_max = max(f1_max, nf1)
            f2_min = min(f2_min, nf2)
            f2_max = max(f2_max, nf2)
            f3_min = min(f3_min, nf3)
            f3_max = max(f3_max, nf3)

            # 用更新后的边界重新计算 Z 值
            bds = ((f1_min, f1_max), (f2_min, f2_max),
                   (f3_min, f3_max))
            cur_z = calculate_z(
                cur_f1, cur_f2, cur_f3,
                bds[0], bds[1], bds[2], self.lambdas
            )
            new_z = calculate_z(
                nf1, nf2, nf3,
                bds[0], bds[1], bds[2], self.lambdas
            )

            # ---- Metropolis 接受准则 ----
            delta_z = new_z - cur_z
            accept = False
            if delta_z < 0:
                # 新解更优，直接接受
                accept = True
            else:
                # 以概率 exp(-delta_z / T) 接受劣解
                if temperature > 0:
                    prob = math.exp(-delta_z / temperature)
                else:
                    prob = 0.0
                if rng.random() < prob:
                    accept = True

            if accept:
                current_seq = new_seq
                current_routes = new_routes
                cur_f1, cur_f2, cur_f3 = nf1, nf2, nf3
                cur_z = new_z

            # ---- 更新全局最优解 ----
            # 用当前边界重新评估 best 的 Z 值
            best_z = calculate_z(
                best_f1, best_f2, best_f3,
                bds[0], bds[1], bds[2], self.lambdas
            )
            if cur_z < best_z - self.early_stop_threshold:
                best_seq = current_seq[:]
                best_routes = current_routes
                best_f1, best_f2, best_f3 = cur_f1, cur_f2, cur_f3
                best_z = cur_z
                no_improve = 0
            else:
                no_improve += 1

            convergence.append((iteration, round(best_z, 6)))

            # ---- 回调通知 ----
            if callback:
                callback({
                    "type": "iteration",
                    "iteration": iteration,
                    "z": round(best_z, 6),
                    "temperature": round(temperature, 4),
                    "f1": round(best_f1, 2),
                    "f2": round(best_f2, 2),
                    "f3": round(best_f3, 2),
                })

            # ---- 早停判断 ----
            if no_improve >= self.patience:
                break

            # ---- 降温：T = T * cooling_rate ----
            temperature *= self.cooling_rate

        # ---- 构造最终调度明细 ----
        final_schedule = build_schedule(
            best_routes, working_dict,
            self.time_matrix, self.id_to_idx,
            self.alpha_base, self.beta_base
        )
        vehicles_used = sum(
            1 for r in best_routes if len(r) > 2
        )

        return SolutionResult(
            routes=best_routes,
            f1=round(best_f1, 4),
            f2=round(best_f2, 4),
            f3=round(best_f3, 4),
            z=round(best_z, 6),
            vehicles_used=vehicles_used,
            convergence=convergence,
            schedule=final_schedule,
            unreachable=unreachable_ids,
        )

    @staticmethod
    def _routes_to_sequence(routes, depot_id):
        """从路线列表中提取客户ID排列（去掉 depot）

        参数:
            routes: 路线列表，如 [[0,3,7,0], [0,1,5,0]]
            depot_id: 配送中心ID
        返回:
            客户ID排列，如 [3, 7, 1, 5]
        """
        seq = []
        for route in routes:
            for node in route:
                if node != depot_id:
                    seq.append(node)
        return seq

    def _decode(self, sequence):
        """将客户ID排列按容量约束分割为路线列表

        按顺序扫描排列，累加需求量，超过车辆容量时断开新路线。
        每条路线首尾添加 depot。

        参数:
            sequence: 客户ID排列
        返回:
            路线列表，如 [[0,3,7,0], [0,1,5,0]]
        """
        depot_id = self.depot["id"]
        # 构建客户需求量映射
        demand_map = {}
        for c in self.customers:
            cid = c["id"]
            demand_map[cid] = c.get(
                "demand", c.get("demand_weight", 0)
            )

        routes = []
        current_route = [depot_id]
        current_load = 0.0

        for cid in sequence:
            d = demand_map.get(cid, 0)
            if current_load + d > self.vehicle_capacity:
                # 当前路线已满，关闭并开启新路线
                current_route.append(depot_id)
                routes.append(current_route)
                current_route = [depot_id]
                current_load = 0.0
            current_route.append(cid)
            current_load += d

        # 关闭最后一条路线
        if len(current_route) > 1:
            current_route.append(depot_id)
            routes.append(current_route)

        return routes

    @staticmethod
    def _neighbor(sequence, rng):
        """随机选择 swap/insert/reverse 之一生成邻域解

        参数:
            sequence: 当前客户ID排列
            rng: numpy RandomState 实例
        返回:
            新的客户ID排列（不修改原列表）
        """
        n = len(sequence)
        if n < 2:
            return sequence[:]

        new_seq = sequence[:]
        op = rng.randint(0, 3)  # 0=swap, 1=insert, 2=reverse

        if op == 0:
            # swap：交换两个不同位置的客户
            i, j = _pick_two(n, rng)
            new_seq[i], new_seq[j] = new_seq[j], new_seq[i]
        elif op == 1:
            # insert：将位置 i 的客户移动到位置 j
            i, j = _pick_two(n, rng)
            cid = new_seq.pop(i)
            new_seq.insert(j, cid)
        else:
            # reverse：反转 [i, j] 区间的子序列
            i, j = _pick_two(n, rng)
            lo, hi = min(i, j), max(i, j)
            new_seq[lo:hi + 1] = reversed(new_seq[lo:hi + 1])

        return new_seq

    def _evaluate(self, routes, working_dict):
        """计算给定路线的 F1/F2/F3 三个目标值

        参数:
            routes: 路线列表
            working_dict: 客户ID到客户信息的映射
        返回:
            (f1, f2, f3) 元组
        """
        schedule = build_schedule(
            routes, working_dict,
            self.time_matrix, self.id_to_idx,
            self.alpha_base, self.beta_base
        )
        f1 = calculate_f1(
            routes, self.distance_matrix, self.id_to_idx,
            self.fixed_cost, self.cost_per_km
        )
        f2 = calculate_f2(schedule, working_dict)
        f3 = calculate_f3(
            schedule, working_dict,
            self.alpha_base, self.beta_base
        )
        return f1, f2, f3


def _pick_two(n, rng):
    """从 [0, n) 中随机选取两个不同的索引

    参数:
        n: 序列长度
        rng: numpy RandomState 实例
    返回:
        (i, j) 两个不同的索引
    """
    i = rng.randint(0, n)
    j = rng.randint(0, n - 1)
    if j >= i:
        j += 1
    return i, j
