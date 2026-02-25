# 贪心求解器 —— 最近邻构造初始解，用于信息素初始化
import numpy as np
from app.algorithm.base import SolutionResult
from app.utils.objective import evaluate_solution


class GreedySolver:
    """最近邻贪心求解器

    参数:
        customers: 客户列表
        depot: 配送中心
        distance_matrix: 距离矩阵
        time_matrix: 时间矩阵
        params: 参数字典（含 vehicle_capacity 等）
    """

    def __init__(self, customers, depot, distance_matrix, time_matrix, params):
        self.customers = customers
        self.depot = depot
        self.distance_matrix = distance_matrix
        self.time_matrix = time_matrix if time_matrix is not None else distance_matrix
        self.params = params
        self.vehicle_capacity = params.get("vehicle_capacity", 1000)
        # λ 权重影响贪心选择指标
        lambdas = params.get("lambdas", [0.33, 0.33, 0.34])
        self.w_cost = lambdas[0]
        self.w_time = lambdas[1] + lambdas[2]

        # 客户信息映射（用于时间窗紧迫度计算）
        self._cust_dict = {c["id"]: c for c in customers}

        self.customer_ids = [c["id"] for c in customers]
        self.id_to_idx = {depot["id"]: 0}
        for i, c in enumerate(customers):
            self.id_to_idx[c["id"]] = i + 1

        # 客户需求量映射
        self._demand = {}
        for c in customers:
            self._demand[c["id"]] = c.get("demand", c.get("demand_weight", 0))

    def solve(self):
        """最近邻贪心构造解

        返回:
            dict: {routes, f1_nn, f2_nn} 用于信息素初始化
        """
        depot_id = self.depot["id"]
        unvisited = set(self.customer_ids)
        routes = []

        while unvisited:
            route = [depot_id]
            load = 0.0
            current = depot_id

            while unvisited:
                # 按 λ 加权指标选择下一个客户
                # 省钱优先(λ₁大)→ 纯距离最近
                # 抢时间(λ₂+λ₃大)→ 综合考虑距离和截止时间紧迫度
                best_cid = None
                best_score = float("inf")
                curr_idx = self.id_to_idx[current]

                for cid in unvisited:
                    cid_idx = self.id_to_idx[cid]
                    dist = self.distance_matrix[curr_idx][cid_idx]
                    # 时间窗紧迫度：截止时间越近越紧迫，值越小越优先
                    c_info = self._cust_dict[cid]
                    deadline = c_info.get("late_time", 9999)
                    score = self.w_cost * dist + self.w_time * deadline
                    if score < best_score:
                        best_score = score
                        best_cid = cid

                if best_cid is None:
                    break

                # 检查容量约束
                demand = self._demand.get(best_cid, 0)
                if load + demand > self.vehicle_capacity:
                    break

                route.append(best_cid)
                load += demand
                current = best_cid
                unvisited.remove(best_cid)

            route.append(depot_id)
            routes.append(route)

        # 评估解的目标值
        result = evaluate_solution(
            routes, self.customers, self.depot,
            self.distance_matrix, self.time_matrix,
            self.id_to_idx, self.params
        )

        return {
            "routes": routes,
            "f1_nn": result["f1"],
            "f2_nn": result["f2"],
        }
