# 标准蚁群算法 —— 单信息素+单启发式，作为对照组
import numpy as np
from app.algorithm.base import BaseAlgorithm, SolutionResult
from app.algorithm.greedy import GreedySolver
from app.algorithm.precheck import precheck_reachability
from app.utils.objective import (
    build_schedule, calculate_f1, calculate_f2, calculate_f3, calculate_z
)


class StandardACO(BaseAlgorithm):
    """标准蚁群算法（对照组）

    与改进版的区别：
    1. 单信息素矩阵（仅 τ）
    2. 单启发式（仅 η=1/d_ij）
    3. 无 2-opt 局部搜索
    4. 全局最优更新（非精英策略，所有蚂蚁均沉积）
    """

    def __init__(self, customers, depot, distance_matrix, time_matrix, params):
        super().__init__(customers, depot, distance_matrix, time_matrix, params)
        self.ant_count = params.get("ant_count") or self.n_customers
        self.rho = params.get("rho_cost", 0.1)
        self.alpha_param = params.get("alpha", 1.0)
        self.beta_param = params.get("beta", 2.0)
        self.alpha_base = params.get("alpha_base", 1.0)
        self.beta_base = params.get("beta_base", 2.0)
        self.fixed_cost = params.get("fixed_cost", 200)
        self.cost_per_km = params.get("cost_per_km", 5.0)
        self.seed = params.get("seed", 42)
        self.n = self.n_customers + 1

    def solve(self, callback=None):
        """执行标准蚁群算法求解"""
        rng = np.random.default_rng(self.seed)

        # 预检
        reachable, unreachable = precheck_reachability(
            self.customers, self.depot, self.time_matrix, self.id_to_idx
        )
        unreachable_ids = [c["id"] for c in unreachable]
        working = reachable
        working_dict = {c["id"]: c for c in working}

        # 贪心解 → τ₀
        greedy = GreedySolver(working, self.depot,
                              self.distance_matrix, self.time_matrix, self.params)
        greedy_result = greedy.solve()
        tau0 = 1.0 / max(greedy_result["f1_nn"], 1e-10)

        # 初始化单信息素和单启发式
        tau = np.full((self.n, self.n), tau0)
        with np.errstate(divide="ignore", invalid="ignore"):
            eta = np.where(self.distance_matrix > 0,
                           1.0 / self.distance_matrix, 1e-10)

        best_routes = None
        best_z = float("inf")
        best_f1 = best_f2 = best_f3 = 0.0
        convergence = []
        f1_min, f1_max = float("inf"), float("-inf")
        f2_min, f2_max = float("inf"), float("-inf")
        f3_min, f3_max = float("inf"), float("-inf")
        no_improve = 0

        for iteration in range(self.max_iterations):
            all_routes = []
            all_z = []

            for _ in range(self.ant_count):
                routes = self._construct(working, working_dict, tau, eta, rng)

                sched = build_schedule(routes, working_dict, self.time_matrix,
                                       self.id_to_idx, self.alpha_base, self.beta_base)
                f1 = calculate_f1(routes, self.distance_matrix, self.id_to_idx,
                                  self.fixed_cost, self.cost_per_km)
                f2 = calculate_f2(sched, working_dict)
                f3 = calculate_f3(sched, working_dict)

                f1_min, f1_max = min(f1_min, f1), max(f1_max, f1)
                f2_min, f2_max = min(f2_min, f2), max(f2_max, f2)
                f3_min, f3_max = min(f3_min, f3), max(f3_max, f3)

                z = calculate_z(f1, f2, f3,
                                (f1_min, f1_max), (f2_min, f2_max),
                                (f3_min, f3_max), self.lambdas)
                all_routes.append((routes, f1, f2, f3, z))
                all_z.append(z)

            # 本轮最优
            idx_best = int(np.argmin(all_z))
            ib_routes, ib_f1, ib_f2, ib_f3, ib_z = all_routes[idx_best]

            if ib_z < best_z - self.early_stop_threshold:
                best_z, best_routes = ib_z, ib_routes
                best_f1, best_f2, best_f3 = ib_f1, ib_f2, ib_f3
                no_improve = 0
            else:
                no_improve += 1

            convergence.append((iteration + 1, round(best_z, 6)))

            # 信息素更新：全局挥发 + 所有蚂蚁沉积
            tau *= (1 - self.rho)
            for routes_i, f1_i, _, _, _ in all_routes:
                delta = 1.0 / max(f1_i, 1e-10)
                for route in routes_i:
                    for k in range(len(route) - 1):
                        i = self.id_to_idx[route[k]]
                        j = self.id_to_idx[route[k + 1]]
                        tau[i][j] += delta

            if callback:
                vn = sum(1 for r in best_routes if len(r) > 2) if best_routes else 0
                callback({"type": "progress", "iteration": iteration + 1,
                          "best_z": round(best_z, 6), "best_f1": round(best_f1, 2),
                          "best_f2": round(best_f2, 2), "best_f3": round(best_f3, 2),
                          "vehicles_used": vn})

            if no_improve >= self.patience:
                break

        if best_routes is None:
            best_routes = greedy_result["routes"]

        final_sched = build_schedule(best_routes, working_dict, self.time_matrix,
                                     self.id_to_idx, self.alpha_base, self.beta_base)
        vn = sum(1 for r in best_routes if len(r) > 2)

        return SolutionResult(
            routes=best_routes, f1=round(best_f1, 2), f2=round(best_f2, 2),
            f3=round(best_f3, 2), z=round(best_z, 6), vehicles_used=vn,
            convergence=convergence, schedule=final_sched,
            unreachable=unreachable_ids,
        )

    def _construct(self, customers, cust_dict, tau, eta, rng):
        """单只蚂蚁构建解（单信息素版本）"""
        depot_id = self.depot["id"]
        unvisited = set(c["id"] for c in customers)
        routes = []

        while unvisited:
            route = [depot_id]
            load = 0.0
            current_time = 0.0
            current = depot_id

            while unvisited:
                curr_idx = self.id_to_idx[current]
                candidates = []
                scores = []

                for cid in unvisited:
                    c = cust_dict[cid]
                    c_idx = self.id_to_idx[cid]
                    demand = c.get("demand", c.get("demand_weight", 0))
                    if load + demand > self.vehicle_capacity:
                        continue

                    travel = self.time_matrix[curr_idx][c_idx]
                    arrival = current_time + travel
                    if c.get("emergency_level") == "medical" and arrival > c.get("late_time", float("inf")):
                        continue

                    score = (tau[curr_idx][c_idx] ** self.alpha_param *
                             eta[curr_idx][c_idx] ** self.beta_param)
                    if score > 0:
                        candidates.append(cid)
                        scores.append(score)

                if not candidates:
                    break

                total = sum(scores)
                probs = np.array(scores) / total
                chosen = rng.choice(candidates, p=probs)

                c_info = cust_dict[chosen]
                c_idx = self.id_to_idx[chosen]
                travel = self.time_matrix[curr_idx][c_idx]
                arrival = current_time + travel
                et = c_info.get("early_time", 0)
                st = c_info.get("service_time", 0)
                level = c_info.get("emergency_level", "normal")

                if arrival < et and level == "medical":
                    current_time = et + st
                else:
                    current_time = arrival + st

                load += c_info.get("demand", c_info.get("demand_weight", 0))
                route.append(chosen)
                current = chosen
                unvisited.remove(chosen)

            route.append(depot_id)
            routes.append(route)

        return routes
