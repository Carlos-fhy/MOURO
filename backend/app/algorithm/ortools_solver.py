# OR-Tools 精确求解器 —— 用于锚点校验的基准解
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from app.algorithm.base import SolutionResult
from app.algorithm.greedy import GreedySolver
from app.utils.objective import (
    build_schedule, calculate_f1, calculate_f2, calculate_f3,
    calculate_reference_z,
)


class ORToolsSolver:
    """OR-Tools CVRPTW 精确求解器

    使用 Google OR-Tools 的 Routing Library 求解小规模 VRPTW 实例，
    作为锚点校验的基准解。

    参数:
        customers: 客户列表
        depot: 配送中心
        distance_matrix: 距离矩阵
        time_matrix: 时间矩阵
        params: 参数字典
    """

    def __init__(self, customers, depot, distance_matrix, time_matrix, params):
        self.customers = customers
        self.depot = depot
        self.distance_matrix = distance_matrix
        self.time_matrix = time_matrix if time_matrix is not None else distance_matrix
        self.params = params
        self.vehicle_capacity = params.get("vehicle_capacity", 1000)
        self.lambdas = params.get("lambdas", [0.33, 0.33, 0.34])
        self.alpha_base = params.get("alpha_base", 1.0)
        self.beta_base = params.get("beta_base", 2.0)
        self.fixed_cost = params.get("fixed_cost", 200)
        self.cost_per_km = params.get("cost_per_km", 5.0)

        # 节点映射
        self.all_nodes = [depot] + customers
        self.n = len(self.all_nodes)
        self.id_to_idx = {depot["id"]: 0}
        for i, c in enumerate(customers):
            self.id_to_idx[c["id"]] = i + 1
        self.customers_dict = {c["id"]: c for c in customers}

    def solve(self, callback=None, time_limit_sec=30):
        """使用 OR-Tools Routing Library 求解 CVRPTW

        参数:
            callback: 未使用（保持接口一致）
            time_limit_sec: 求解时间上限（秒）
        返回:
            SolutionResult
        """
        manager = pywrapcp.RoutingIndexManager(
            self.n, self.n, 0  # 节点数, 最大车辆数, depot索引
        )
        routing = pywrapcp.RoutingModel(manager)

        # 距离回调（整数化，OR-Tools 要求整数）
        dist_int = (self.distance_matrix * 100).astype(int)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(dist_int[from_node][to_node])

        transit_cb_idx = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_cb_idx)

        # 容量约束
        def demand_callback(from_index):
            node = manager.IndexToNode(from_index)
            if node == 0:
                return 0
            c = self.all_nodes[node]
            return int(c.get("demand", c.get("demand_weight", 0)))

        demand_cb_idx = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_cb_idx, 0,
            [int(self.vehicle_capacity)] * self.n,
            True, "Capacity"
        )

        # 时间窗约束
        time_int = (self.time_matrix * 100).astype(int)

        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(time_int[from_node][to_node])

        time_cb_idx = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_cb_idx,
            int(1e7),  # 允许等待时间上限
            int(1e7),  # 车辆最大行驶时间
            False, "Time"
        )
        time_dim = routing.GetDimensionOrDie("Time")

        # 为每个节点设置时间窗范围
        for node_idx in range(self.n):
            index = manager.NodeToIndex(node_idx)
            if node_idx == 0:
                # depot：时间窗 [0, 大值]
                time_dim.CumulVar(index).SetRange(0, int(1e7))
            else:
                c = self.all_nodes[node_idx]
                et = int(c.get("early_time", 0) * 100)
                lt = int(c.get("late_time", 1e5) * 100)
                level = c.get("emergency_level", "normal")
                if level == "medical":
                    # 硬时间窗：必须在 [ET, LT] 内到达
                    time_dim.CumulVar(index).SetRange(et, lt)
                else:
                    # 软时间窗：不强制，设宽松范围
                    time_dim.CumulVar(index).SetRange(0, int(1e7))

        # 允许丢弃非必要节点（避免无解）
        for node_idx in range(1, self.n):
            c = self.all_nodes[node_idx]
            level = c.get("emergency_level", "normal")
            if level != "medical":
                routing.AddDisjunction(
                    [manager.NodeToIndex(node_idx)], int(1e6)
                )

        # 搜索参数
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_params.time_limit.seconds = time_limit_sec

        # 求解
        solution = routing.SolveWithParameters(search_params)

        if not solution:
            # 无解时返回空结果
            return SolutionResult(
                routes=[], f1=0, f2=0, f3=0, z=0,
                vehicles_used=0, convergence=[], schedule=[],
                unreachable=[c["id"] for c in self.customers],
            )

        # 提取路线
        routes = self._extract_routes(manager, routing, solution)

        # 计算目标函数
        schedule = build_schedule(
            routes, self.customers_dict, self.time_matrix,
            self.id_to_idx, self.alpha_base, self.beta_base
        )
        f1 = calculate_f1(
            routes, self.distance_matrix, self.id_to_idx,
            self.fixed_cost, self.cost_per_km
        )
        f2 = calculate_f2(schedule, self.customers_dict)
        f3 = calculate_f3(schedule, self.customers_dict)
        greedy = GreedySolver(
            self.customers, self.depot,
            self.distance_matrix, self.time_matrix, self.params
        )
        greedy_result = greedy.solve()
        z = calculate_reference_z(f1, f2, f3, greedy_result, self.lambdas)
        vehicles_used = sum(1 for r in routes if len(r) > 2)

        return SolutionResult(
            routes=routes, f1=round(f1, 2), f2=round(f2, 2),
            f3=round(f3, 2), z=round(z, 6), vehicles_used=vehicles_used,
            convergence=[], schedule=schedule, unreachable=[],
        )

    def _extract_routes(self, manager, routing, solution):
        """从 OR-Tools solution 中提取路线列表

        返回:
            routes: [[depot_id, c1, c2, ..., depot_id], ...]
        """
        depot_id = self.depot["id"]
        routes = []

        for vehicle_id in range(self.n):
            index = routing.Start(vehicle_id)
            route = [depot_id]

            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != 0:
                    route.append(self.all_nodes[node]["id"])
                index = solution.Value(routing.NextVar(index))

            route.append(depot_id)
            # 只保留有客户的路线
            if len(route) > 2:
                routes.append(route)

        return routes
