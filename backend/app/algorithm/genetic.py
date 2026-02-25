# 遗传算法 —— 排列编码+顺序交叉+轮盘赌选择，用于多目标城市配送路径优化
import numpy as np
from app.algorithm.base import BaseAlgorithm, SolutionResult
from app.algorithm.greedy import GreedySolver
from app.algorithm.precheck import precheck_reachability
from app.utils.objective import (
    build_schedule, calculate_f1, calculate_f2, calculate_f3, calculate_z
)


class GeneticAlgorithm(BaseAlgorithm):
    """遗传算法求解器

    染色体编码：客户ID的排列序列，解码时按容量约束分割为多条路线。
    选择：轮盘赌；交叉：顺序交叉OX；变异：随机交换两个位置。

    参数:
        customers: 客户列表
        depot: 配送中心
        distance_matrix: 距离矩阵
        time_matrix: 时间矩阵
        params: 算法参数字典
    """

    def __init__(self, customers, depot, distance_matrix, time_matrix, params):
        super().__init__(customers, depot, distance_matrix, time_matrix, params)

        # 遗传算法专用参数
        self.population_size = params.get("population_size", 100)
        self.crossover_rate = params.get("crossover_rate", 0.8)
        self.mutation_rate = params.get("mutation_rate", 0.1)
        self.seed = self._default_seed

        # 业务参数
        self.alpha_base = params.get("alpha_base", 1.0)
        self.beta_base = params.get("beta_base", 2.0)
        self.fixed_cost = params.get("fixed_cost", 200)
        self.cost_per_km = params.get("cost_per_km", 5.0)

        # 客户字典（ID → 客户信息）
        self.customers_dict = {c["id"]: c for c in self.customers}

    def solve(self, callback=None):
        """执行遗传算法求解

        参数:
            callback: 每轮迭代回调函数，签名 callback(msg_dict)，用于 SSE 推送
        返回:
            SolutionResult 实例
        """
        rng = np.random.default_rng(self.seed)

        # ---- 1. 预检：剔除不可达的硬时间窗客户 ----
        reachable, unreachable = precheck_reachability(
            self.customers, self.depot, self.time_matrix, self.id_to_idx
        )
        unreachable_ids = [c["id"] for c in unreachable]

        working_customers = reachable
        working_dict = {c["id"]: c for c in working_customers}
        working_ids = [c["id"] for c in working_customers]

        # ---- 2. 初始种群：一个贪心解 + 其余随机排列 ----
        population = self._init_population(working_customers, working_ids, rng)

        # ---- 3. 迭代状态变量 ----
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
        depot_id = self.depot["id"]

        # ---- 4. 主迭代循环 ----
        for iteration in range(self.max_iterations):
            # 评估当前种群适应度
            fitnesses, pop_data = self._evaluate_population(
                population, depot_id, working_dict
            )

            # 动态更新 Min-Max 归一化边界
            for d in pop_data:
                f1_min, f1_max = min(f1_min, d["f1"]), max(f1_max, d["f1"])
                f2_min, f2_max = min(f2_min, d["f2"]), max(f2_max, d["f2"])
                f3_min, f3_max = min(f3_min, d["f3"]), max(f3_max, d["f3"])

            # 计算每个个体的 Z 值，找本代最优
            z_values = []
            for d in pop_data:
                z = calculate_z(
                    d["f1"], d["f2"], d["f3"],
                    (f1_min, f1_max), (f2_min, f2_max), (f3_min, f3_max),
                    self.lambdas
                )
                z_values.append(z)

            # 本代最优个体
            iter_best_idx = int(np.argmin(z_values))
            iter_best_z = z_values[iter_best_idx]
            iter_data = pop_data[iter_best_idx]

            # 更新全局最优
            if iter_best_z < best_z - self.early_stop_threshold:
                best_z = iter_best_z
                best_routes = iter_data["routes"]
                best_f1 = iter_data["f1"]
                best_f2 = iter_data["f2"]
                best_f3 = iter_data["f3"]
                no_improve_count = 0
            else:
                no_improve_count += 1

            convergence.append((iteration + 1, round(best_z, 6)))

            # SSE 回调
            if callback:
                vehicles_used = (
                    sum(1 for r in best_routes if len(r) > 2)
                    if best_routes else 0
                )
                callback({
                    "type": "progress",
                    "iteration": iteration + 1,
                    "best_z": round(best_z, 6),
                    "best_f1": round(best_f1, 2),
                    "best_f2": round(best_f2, 2),
                    "best_f3": round(best_f3, 2),
                    "vehicles_used": vehicles_used,
                })

            # 早停检查
            if no_improve_count >= self.patience:
                break

            # ---- 5. 遗传操作：精英保留 + 选择交叉变异 ----
            # 适应度取倒数（Z 越小越好 → fitness 越大越好）
            fit_for_select = []
            for zv in z_values:
                fit_for_select.append(1.0 / (zv + 1e-10))

            new_population = []
            # 精英保留：将当前最优个体直接复制到下一代
            new_population.append(list(population[iter_best_idx]))

            # 填充剩余种群
            while len(new_population) < self.population_size:
                # 轮盘赌选择两个父代
                p1 = self._roulette_select(population, fit_for_select, rng)
                p2 = self._roulette_select(population, fit_for_select, rng)

                # 顺序交叉 OX
                if rng.random() < self.crossover_rate:
                    c1, c2 = self._ox_crossover(p1, p2, rng)
                else:
                    c1, c2 = list(p1), list(p2)

                # 随机交换变异
                c1 = self._mutate(c1, rng)
                c2 = self._mutate(c2, rng)

                new_population.append(c1)
                if len(new_population) < self.population_size:
                    new_population.append(c2)

            population = new_population

        # ---- 6. 构建最终结果 ----
        if best_routes is None:
            # 若迭代未产生有效解，使用贪心解兜底
            greedy = GreedySolver(
                working_customers, self.depot,
                self.distance_matrix, self.time_matrix, self.params
            )
            greedy_result = greedy.solve()
            best_routes = greedy_result["routes"]

        final_schedule = build_schedule(
            best_routes, working_dict, self.time_matrix,
            self.id_to_idx, self.alpha_base, self.beta_base
        )
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

    # ------------------------------------------------------------------
    #  私有辅助方法
    # ------------------------------------------------------------------

    def _init_population(self, working_customers, working_ids, rng):
        """初始化种群：一个贪心解 + 其余随机排列

        参数:
            working_customers: 可达客户列表
            working_ids: 可达客户ID列表
            rng: numpy 随机数生成器
        返回:
            population: 染色体列表，每条染色体为客户ID排列
        """
        population = []

        # 第一个个体：贪心解转换为排列编码
        greedy = GreedySolver(
            working_customers, self.depot,
            self.distance_matrix, self.time_matrix, self.params
        )
        greedy_result = greedy.solve()
        greedy_chrom = self._routes_to_chromosome(greedy_result["routes"])
        population.append(greedy_chrom)

        # 其余个体：随机打乱客户ID顺序
        for _ in range(self.population_size - 1):
            chrom = list(working_ids)
            rng.shuffle(chrom)
            population.append(chrom)

        return population

    def _routes_to_chromosome(self, routes):
        """将路线列表转换为染色体（客户ID排列）

        参数:
            routes: 路线列表，如 [[0,3,7,0], [0,1,5,0]]
        返回:
            chromosome: 客户ID排列，如 [3,7,1,5]
        """
        depot_id = self.depot["id"]
        chrom = []
        for route in routes:
            for node in route:
                if node != depot_id:
                    chrom.append(node)
        return chrom

    def _evaluate_population(self, population, depot_id, working_dict):
        """评估整个种群的适应度

        参数:
            population: 染色体列表
            depot_id: 配送中心ID
            working_dict: 可达客户字典
        返回:
            (fitnesses, pop_data): 适应度列表和每个个体的详细数据
        """
        fitnesses = []
        pop_data = []

        for chrom in population:
            routes = self._decode(chrom, depot_id)
            data = self._evaluate_routes(routes, working_dict)
            fitnesses.append(data["f1"])
            pop_data.append(data)

        return fitnesses, pop_data

    def _evaluate_routes(self, routes, working_dict):
        """评估一组路线的三个目标值

        参数:
            routes: 路线列表
            working_dict: 可达客户字典
        返回:
            dict: {routes, f1, f2, f3}
        """
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
        return {"routes": routes, "f1": f1, "f2": f2, "f3": f3}

    def _decode(self, chromosome, depot_id):
        """将染色体（客户ID排列）按容量约束分割为路线列表

        参数:
            chromosome: 客户ID排列，如 [3,7,1,5]
            depot_id: 配送中心ID
        返回:
            routes: 路线列表，如 [[0,3,7,0], [0,1,5,0]]
        """
        routes = []
        route = [depot_id]
        load = 0.0

        for cid in chromosome:
            demand = self.customers_dict.get(cid, {}).get(
                "demand", self.customers_dict.get(cid, {}).get(
                    "demand_weight", 0
                )
            )
            # 若加入当前客户会超载，则关闭当前路线，开启新路线
            if load + demand > self.vehicle_capacity:
                route.append(depot_id)
                routes.append(route)
                route = [depot_id]
                load = 0.0

            route.append(cid)
            load += demand

        # 关闭最后一条路线
        route.append(depot_id)
        routes.append(route)

        return routes

    def _ox_crossover(self, p1, p2, rng):
        """顺序交叉 OX（Order Crossover）

        步骤：
        1. 随机选取两个切割点 [start, end)
        2. 子代1中间段复制自父代1，其余位置按父代2顺序填充
        3. 子代2对称操作

        参数:
            p1: 父代1染色体
            p2: 父代2染色体
            rng: numpy 随机数生成器
        返回:
            (child1, child2): 两个子代染色体
        """
        size = len(p1)
        if size < 2:
            return list(p1), list(p2)

        # 随机选取两个不同的切割点
        start, end = sorted(rng.choice(size, size=2, replace=False))

        child1 = self._ox_one_child(p1, p2, start, end)
        child2 = self._ox_one_child(p2, p1, start, end)
        return child1, child2

    def _ox_one_child(self, donor, filler, start, end):
        """OX 交叉生成单个子代

        参数:
            donor: 提供中间段的父代
            filler: 提供剩余基因顺序的父代
            start: 切割起点（含）
            end: 切割终点（不含）
        返回:
            child: 子代染色体
        """
        size = len(donor)
        child = [None] * size

        # 复制 donor 的 [start, end) 段
        segment = set(donor[start:end])
        child[start:end] = donor[start:end]

        # 从 filler 中按顺序取出不在 segment 中的基因
        filler_genes = [g for g in filler if g not in segment]

        # 从 end 位置开始循环填充
        idx = 0
        for pos in range(size):
            actual = (end + pos) % size
            if child[actual] is None:
                child[actual] = filler_genes[idx]
                idx += 1

        return child

    def _mutate(self, chrom, rng):
        """随机交换变异：以 mutation_rate 概率交换两个随机位置

        参数:
            chrom: 染色体（客户ID排列）
            rng: numpy 随机数生成器
        返回:
            变异后的染色体
        """
        if rng.random() < self.mutation_rate and len(chrom) >= 2:
            i, j = rng.choice(len(chrom), size=2, replace=False)
            chrom[i], chrom[j] = chrom[j], chrom[i]
        return chrom

    def _roulette_select(self, population, fitnesses, rng):
        """轮盘赌选择：按适应度比例选择一个个体

        参数:
            population: 当前种群（染色体列表）
            fitnesses: 适应度列表（值越大越好）
            rng: numpy 随机数生成器
        返回:
            选中个体的染色体副本
        """
        fit_arr = np.array(fitnesses, dtype=float)
        total = fit_arr.sum()

        # 防止全零情况：均匀选择
        if total <= 0:
            idx = rng.integers(len(population))
            return list(population[idx])

        probs = fit_arr / total
        idx = rng.choice(len(population), p=probs)
        return list(population[idx])
