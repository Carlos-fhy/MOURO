# 改进蚁群算法 —— 双信息素+双启发式+精英更新+2-opt局部搜索
import numpy as np
from app.algorithm.base import BaseAlgorithm, SolutionResult
from app.algorithm.greedy import GreedySolver
from app.algorithm.precheck import precheck_reachability
from app.algorithm.local_search import full_local_search, repair_late_customers, tw_attractiveness
from app.utils.objective import (
    build_schedule, calculate_f1, calculate_f2, calculate_f3, calculate_z
)


class Ant:
    """单只蚂蚁 —— 构建一条完整的 VRPTW 解

    使用双信息素（τ_cost, τ_time）和双启发式（η_cost, η_time）
    进行状态转移概率计算。

    参数:
        customers: 客户列表
        depot_id: 配送中心节点ID
        distance_matrix: 距离矩阵
        time_matrix: 时间矩阵
        tau_cost: 成本信息素矩阵
        tau_time: 时间信息素矩阵
        eta_cost: 成本启发式矩阵 (1/d_ij)
        eta_time: 时间启发式矩阵 (1/t_ij)
        id_to_idx: 节点ID到矩阵索引映射
        params: 算法参数
        customers_dict: 客户ID到信息的映射
        rng: numpy 随机数生成器
    """

    def __init__(self, customers, depot_id, distance_matrix, time_matrix,
                 tau_cost, tau_time, eta_cost, eta_time,
                 id_to_idx, params, customers_dict, rng):
        self.customers = customers
        self.depot_id = depot_id
        self.distance_matrix = distance_matrix
        self.time_matrix = time_matrix
        self.tau_cost = tau_cost
        self.tau_time = tau_time
        self.eta_cost = eta_cost
        self.eta_time = eta_time
        self.id_to_idx = id_to_idx
        self.params = params
        self.customers_dict = customers_dict
        self.rng = rng

        # 算法超参数
        self.alpha = params.get("alpha", 1.0)    # 成本信息素重要度
        self.beta = params.get("beta", 2.0)      # 成本启发式重要度
        self.gamma = params.get("gamma", 1.0)    # 时间信息素重要度
        self.delta = params.get("delta", 2.0)    # 时间启发式重要度
        self.capacity = params.get("vehicle_capacity", 1000)

    def construct_solution(self):
        """构建一条完整的 VRPTW 解

        返回:
            routes: 路线列表，如 [[0,3,7,0], [0,1,5,0]]
        """
        unvisited = set(c["id"] for c in self.customers)
        routes = []

        while unvisited:
            route = [self.depot_id]
            load = 0.0
            current_time = 0.0
            current_id = self.depot_id

            while unvisited:
                # 计算所有可行候选客户的转移概率
                candidates, probs = self._calc_probabilities(
                    current_id, current_time, load, unvisited
                )
                if not candidates:
                    break

                # 轮盘赌选择下一个客户
                chosen = self.rng.choice(candidates, p=probs)
                c_info = self.customers_dict[chosen]

                # 更新时间和载重
                curr_idx = self.id_to_idx[current_id]
                next_idx = self.id_to_idx[chosen]
                travel = self.time_matrix[curr_idx][next_idx]
                arrival = current_time + travel

                et = c_info.get("early_time", 0)
                lt = c_info.get("late_time", float("inf"))
                st = c_info.get("service_time", 0)
                level = c_info.get("emergency_level", "normal")

                # 硬时间窗早到等待
                if arrival < et and level == "medical":
                    current_time = et + st
                else:
                    current_time = max(arrival, et) + st if level == "medical" else arrival + st

                demand = c_info.get("demand", c_info.get("demand_weight", 0))
                load += demand
                route.append(chosen)
                current_id = chosen
                unvisited.remove(chosen)

            route.append(self.depot_id)
            routes.append(route)

        return routes

    def _calc_probabilities(self, current_id, current_time, load, unvisited):
        """计算从当前节点到所有可行候选客户的转移概率

        状态转移公式: P_ij ∝ τ_cost^α × η_cost^β × τ_time^γ × η_time^δ

        可行性检查:
        1. 容量约束: load + demand_j ≤ Q
        2. 硬时间窗: 若 medical 客户且到达时间 > LT_j，则不可行 (P=0)

        返回:
            (candidates, probs): 候选客户ID列表和对应概率数组
        """
        curr_idx = self.id_to_idx[current_id]
        candidates = []
        scores = []

        for cid in unvisited:
            c_info = self.customers_dict[cid]
            c_idx = self.id_to_idx[cid]

            # 容量检查
            demand = c_info.get("demand", c_info.get("demand_weight", 0))
            if load + demand > self.capacity:
                continue

            # 时间可行性检查
            travel = self.time_matrix[curr_idx][c_idx]
            arrival = current_time + travel
            level = c_info.get("emergency_level", "normal")
            lt = c_info.get("late_time", float("inf"))

            # 迟到不可行：所有等级的客户到达超过 LT 均跳过，
            # 迫使蚂蚁关闭当前路线、开新车从 t=0 出发准时送达
            if arrival > lt:
                continue

            # 计算转移概率分子
            tc = self.tau_cost[curr_idx][c_idx] ** self.alpha
            ec = self.eta_cost[curr_idx][c_idx] ** self.beta
            tt = self.tau_time[curr_idx][c_idx] ** self.gamma
            et = self.eta_time[curr_idx][c_idx] ** self.delta

            score = tc * ec * tt * et
            # 时间窗吸引力因子：偏离时间窗越远，score 越低
            et_val = c_info.get("early_time", 0)
            score *= tw_attractiveness(arrival, et_val, lt, level)
            if score > 0:
                candidates.append(cid)
                scores.append(score)

        if not candidates:
            return [], []

        # 归一化为概率
        total = sum(scores)
        probs = np.array(scores) / total
        return candidates, probs


class ImprovedACO(BaseAlgorithm):
    """改进蚁群算法

    核心改进点：
    1. 双信息素矩阵（τ_cost, τ_time）独立挥发
    2. 双启发式（η_cost=1/d_ij, η_time=1/t_ij）
    3. 精英蚂蚁全局信息素更新
    4. 每轮最优解执行 2-opt 局部搜索
    5. 早停机制（patience + threshold）
    """

    def __init__(self, customers, depot, distance_matrix, time_matrix, params):
        super().__init__(customers, depot, distance_matrix, time_matrix, params)

        # ACO 专用参数
        self.ant_count = params.get("ant_count") or self.n_customers
        self.rho_cost = params.get("rho_cost", 0.1)
        self.rho_time = params.get("rho_time", 0.1)
        self.alpha_base = params.get("alpha_base", 1.0)
        self.beta_base = params.get("beta_base", 2.0)
        self.fixed_cost = params.get("fixed_cost", 200)
        self.cost_per_km = params.get("cost_per_km", 5.0)
        self.seed = self._default_seed
        self.status_interval = max(1, int(params.get("status_interval", 10)))

        self.n = self.n_customers + 1  # 矩阵维度（depot + customers）
        self.customers_dict = {c["id"]: c for c in self.customers}

    def solve(self, callback=None):
        """执行改进蚁群算法求解

        参数:
            callback: 每轮迭代回调，签名 callback(msg_dict)
        返回:
            SolutionResult
        """
        rng = np.random.default_rng(self.seed)
        self._start_timer()
        timed_out = False

        # 1. 预检：剔除不可达的硬时间窗客户
        reachable, unreachable = precheck_reachability(
            self.customers, self.depot, self.time_matrix, self.id_to_idx
        )
        unreachable_ids = [c["id"] for c in unreachable]

        # 若有客户被剔除，重建映射
        working_customers = reachable
        working_dict = {c["id"]: c for c in working_customers}

        # 2. 贪心解 → 信息素初始值 τ₀
        greedy = GreedySolver(
            working_customers, self.depot,
            self.distance_matrix, self.time_matrix, self.params
        )
        greedy_result = greedy.solve()
        f1_nn = max(greedy_result["f1_nn"], 1e-10)
        f2_nn = max(greedy_result["f2_nn"], 1e-10)
        tau0_cost = 1.0 / f1_nn
        tau0_time = 1.0 / f2_nn

        # 3. 初始化信息素矩阵和启发式矩阵
        tau_cost = np.full((self.n, self.n), tau0_cost)
        tau_time = np.full((self.n, self.n), tau0_time)

        # η_cost = 1/d_ij（纯距离启发式）
        with np.errstate(divide="ignore", invalid="ignore"):
            eta_cost = np.where(self.distance_matrix > 0,
                                1.0 / self.distance_matrix, 1e-10)

        # η_time = ω_j / t_ij（融入应急权重的时间启发式）
        # 当 dist==time（Solomon 数据）时，ω_j 使 η_time 与 η_cost 产生差异
        # 医疗急件 ω=2.0 吸引力更强，引导蚂蚁优先服务高紧迫度客户
        weight_vec = np.ones(self.n)
        for c in working_customers:
            idx = self.id_to_idx[c["id"]]
            weight_vec[idx] = c.get("emergency_weight", 1.0)

        with np.errstate(divide="ignore", invalid="ignore"):
            raw_eta_time = np.where(self.time_matrix > 0,
                                    1.0 / self.time_matrix, 1e-10)
        # 按列乘以目标客户的应急权重
        eta_time = raw_eta_time * weight_vec[np.newaxis, :]

        # 4. 迭代状态变量
        best_routes = None
        best_z = float("inf")
        best_f1 = best_f2 = best_f3 = 0.0
        convergence = []

        # Min-Max 归一化边界（动态更新）
        f1_min, f1_max = float("inf"), float("-inf")
        f2_min, f2_max = float("inf"), float("-inf")
        f3_min, f3_max = float("inf"), float("-inf")

        # 早停计数器
        no_improve_count = 0

        # 5. 主迭代循环
        for iteration in range(self.max_iterations):
            if self._time_exceeded():
                timed_out = True
                break
            iter_best_routes = None
            iter_best_z = float("inf")
            iter_best_f1 = iter_best_f2 = iter_best_f3 = 0.0

            # 所有蚂蚁构建解
            for ant_idx in range(self.ant_count):
                if self._time_exceeded():
                    timed_out = True
                    break
                ant = Ant(
                    working_customers, self.depot["id"],
                    self.distance_matrix, self.time_matrix,
                    tau_cost, tau_time, eta_cost, eta_time,
                    self.id_to_idx, self.params, working_dict, rng
                )
                routes = ant.construct_solution()

                # 评估该蚂蚁的解
                schedule = build_schedule(
                    routes, working_dict, self.time_matrix,
                    self.id_to_idx, self.alpha_base, self.beta_base
                )
                f1 = calculate_f1(
                    routes, self.distance_matrix, self.id_to_idx,
                    self.fixed_cost, self.cost_per_km
                )
                f2 = calculate_f2(schedule, working_dict)
                f3 = calculate_f3(schedule, working_dict)

                # 更新归一化边界
                f1_min, f1_max = min(f1_min, f1), max(f1_max, f1)
                f2_min, f2_max = min(f2_min, f2), max(f2_max, f2)
                f3_min, f3_max = min(f3_min, f3), max(f3_max, f3)

                z = calculate_z(
                    f1, f2, f3,
                    (f1_min, f1_max), (f2_min, f2_max), (f3_min, f3_max),
                    self.lambdas
                )

                if z < iter_best_z:
                    iter_best_z = z
                    iter_best_routes = routes
                    iter_best_f1, iter_best_f2, iter_best_f3 = f1, f2, f3


            if timed_out:
                break

            # 本轮最优解执行完整局部搜索（2-opt + relocate）
            if iter_best_routes:
                if callback:
                    callback({
                        "type": "status",
                        "iteration": iteration + 1,
                        "phase": "local_search",
                        "done": 0,
                        "total": 1,
                    })
                iter_best_routes = full_local_search(
                    iter_best_routes, self.distance_matrix, self.id_to_idx,
                    working_dict, self.vehicle_capacity,
                    time_matrix=self.time_matrix
                )
                if callback:
                    callback({
                        "type": "status",
                        "iteration": iteration + 1,
                        "phase": "local_search",
                        "done": 1,
                        "total": 1,
                    })
                # 重新评估 2-opt 后的解
                schedule = build_schedule(
                    iter_best_routes, working_dict, self.time_matrix,
                    self.id_to_idx, self.alpha_base, self.beta_base
                )
                iter_best_f1 = calculate_f1(
                    iter_best_routes, self.distance_matrix, self.id_to_idx,
                    self.fixed_cost, self.cost_per_km
                )
                iter_best_f2 = calculate_f2(schedule, working_dict)
                iter_best_f3 = calculate_f3(schedule, working_dict)
                iter_best_z = calculate_z(
                    iter_best_f1, iter_best_f2, iter_best_f3,
                    (f1_min, f1_max), (f2_min, f2_max), (f3_min, f3_max),
                    self.lambdas
                )

            # 更新全局最优
            if iter_best_z < best_z - self.early_stop_threshold:
                best_z = iter_best_z
                best_routes = iter_best_routes
                best_f1 = iter_best_f1
                best_f2 = iter_best_f2
                best_f3 = iter_best_f3
                no_improve_count = 0
            else:
                no_improve_count += 1

            convergence.append((iteration + 1, round(best_z, 6)))

            # 6. 精英蚂蚁信息素更新（仅用全局最优解更新）
            if best_routes:
                self._update_pheromone(
                    tau_cost, tau_time, best_routes,
                    best_f1, best_f2
                )

            # 7. SSE 回调
            if callback:
                vehicles_used = sum(1 for r in best_routes if len(r) > 2) if best_routes else 0
                callback({
                    "type": "progress",
                    "iteration": iteration + 1,
                    "best_z": round(best_z, 6),
                    "best_f1": round(best_f1, 2),
                    "best_f2": round(best_f2, 2),
                    "best_f3": round(best_f3, 2),
                    "vehicles_used": vehicles_used,
                })

            # 8. 早停检查
            if no_improve_count >= self.patience:
                break

        if timed_out and callback:
            callback({
                "type": "timeout",
                "message": f"达到总时限 {self.max_runtime_sec:.0f}s，返回当前最优解",
                "elapsed_sec": round(self._elapsed_sec(), 2),
            })

        # 9. 构建最终结果
        if best_routes is None:
            best_routes = greedy_result["routes"]

        # 后处理：修复迟到客户（与 GA/SA 统一口径）
        best_routes = repair_late_customers(
            best_routes, self.time_matrix, self.id_to_idx, working_dict
        )

        final_schedule = build_schedule(
            best_routes, working_dict, self.time_matrix,
            self.id_to_idx, self.alpha_base, self.beta_base
        )
        best_f1 = calculate_f1(
            best_routes, self.distance_matrix, self.id_to_idx,
            self.fixed_cost, self.cost_per_km
        )
        best_f2 = calculate_f2(final_schedule, working_dict)
        best_f3 = calculate_f3(final_schedule, working_dict)
        if all(np.isfinite(v) for v in (f1_min, f1_max, f2_min, f2_max, f3_min, f3_max)):
            best_z = calculate_z(
                best_f1, best_f2, best_f3,
                (f1_min, f1_max), (f2_min, f2_max), (f3_min, f3_max),
                self.lambdas
            )
        elif not np.isfinite(best_z):
            best_z = 0.0
        vehicles_used = sum(1 for r in best_routes if len(r) > 2)

        return SolutionResult(
            routes=best_routes,
            f1=round(best_f1, 2),
            f2=round(best_f2, 2),
            f3=round(best_f3, 2),
            z=round(best_z, 6),
            vehicles_used=vehicles_used,
            convergence=convergence,
            schedule=final_schedule,
            unreachable=unreachable_ids,
        )

    def _update_pheromone(self, tau_cost, tau_time, routes, f1, f2):
        """精英蚂蚁信息素更新

        1. 全局挥发：τ = (1-ρ) × τ
        2. 精英沉积：仅全局最优解的边获得信息素增量
           Δτ_cost = w_cost/F1, Δτ_time = w_time/F2'
           其中 w_cost = λ₁, w_time = λ₂+λ₃（惩罚与时效相关）
           λ 权重越大，对应信息素沉积越强，引导搜索偏向该目标
        """
        # 挥发
        tau_cost *= (1 - self.rho_cost)
        tau_time *= (1 - self.rho_time)

        # λ 加权信息素沉积
        w_cost = max(self.lambdas[0], 0.05)
        w_time = max(self.lambdas[1] + self.lambdas[2], 0.05)
        delta_cost = w_cost / max(f1, 1e-10)
        delta_time = w_time / max(f2, 1e-10)

        for route in routes:
            if len(route) <= 2:
                continue
            for k in range(len(route) - 1):
                i = self.id_to_idx[route[k]]
                j = self.id_to_idx[route[k + 1]]
                tau_cost[i][j] += delta_cost
                tau_time[i][j] += delta_time
