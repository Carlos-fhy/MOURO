# 算法基类与统一数据结构定义
from dataclasses import dataclass, field
import time


@dataclass
class SolutionResult:
    """算法求解结果的统一数据结构

    属性:
        routes: 路线列表，每条路线为节点ID序列，如 [[0,3,7,0], [0,1,5,0]]
        f1: 纯经济成本（固定+距离，含回程）
        f2: 加权完工时间 Σ(ω_ei × t_arrive_i)
        f3: 时间窗惩罚成本 Σ P_i(t)
        z: 综合目标值 Z = λ₁F1* + λ₂F2'* + λ₃F3*
        vehicles_used: 使用车辆数
        convergence: 收敛数据 [(iteration, z_value), ...]
        schedule: 调度明细列表
        unreachable: 预检剔除的不可达客户ID列表
    """
    routes: list = field(default_factory=list)
    f1: float = 0.0
    f2: float = 0.0
    f3: float = 0.0
    z: float = 0.0
    vehicles_used: int = 0
    convergence: list = field(default_factory=list)
    schedule: list = field(default_factory=list)
    unreachable: list = field(default_factory=list)


class BaseAlgorithm:
    """所有算法的统一基类

    参数:
        customers: 客户列表，每个元素为 dict（含 id, x_coord, y_coord, demand/demand_weight,
                   service_time, early_time, late_time, emergency_level, emergency_weight）
        depot: 配送中心 dict（含 id, x_coord, y_coord）
        distance_matrix: 距离矩阵（numpy 二维数组，用于 F1 成本计算）
        time_matrix: 行驶时间矩阵（numpy 二维数组，用于 F2' 和时间窗判断）
                     Solomon 模式下 time_matrix = distance_matrix（速度=1）
                     首尔模式下两者独立（非对称路网时间矩阵）
        params: 算法参数 dict
    """

    def __init__(self, customers, depot, distance_matrix, time_matrix, params):
        self.customers = customers
        self.depot = depot
        self.distance_matrix = distance_matrix
        self.time_matrix = time_matrix if time_matrix is not None else distance_matrix
        self.params = params

        # 提取常用参数
        self.lambdas = params.get("lambdas", [0.33, 0.33, 0.34])
        self.vehicle_capacity = params.get("vehicle_capacity", 1000)
        self.max_iterations = params.get("max_iterations", 200)
        self.patience = params.get("patience", 50)
        self.early_stop_threshold = params.get("early_stop_threshold", 1e-6)
        # 总时限（秒），为 None 表示不限时
        self.max_runtime_sec = params.get("max_runtime_sec")
        if self.max_runtime_sec is not None:
            try:
                self.max_runtime_sec = float(self.max_runtime_sec)
            except (TypeError, ValueError):
                self.max_runtime_sec = None
            if self.max_runtime_sec is not None and self.max_runtime_sec <= 0:
                self.max_runtime_sec = None
        self._start_time = None

        # 动态种子：未指定 seed 时，根据 λ 生成不同种子
        # 同一 λ 配置可复现，不同 λ 产生不同搜索路径
        if "seed" not in params:
            self._default_seed = hash(tuple(
                round(v, 4) for v in self.lambdas
            )) % (2**31)
        else:
            self._default_seed = params["seed"]

        # 构建客户ID到索引的映射（距离矩阵中的行列索引）
        # 约定：索引0 = depot，索引1~N = customers（按列表顺序）
        self.n_customers = len(customers)
        self.customer_ids = [c["id"] for c in customers]
        self.id_to_idx = {self.depot["id"]: 0}
        for i, c in enumerate(customers):
            self.id_to_idx[c["id"]] = i + 1

    def solve(self, callback=None):
        """执行求解

        参数:
            callback: 每轮迭代回调函数，签名 callback(msg_dict)，用于 SSE 推送
        返回:
            SolutionResult 实例
        """
        raise NotImplementedError("子类必须实现 solve 方法")

    def _start_timer(self):
        """开始计时，用于总时限控制。"""
        self._start_time = time.time()

    def _elapsed_sec(self):
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def _time_exceeded(self):
        """是否已超过总时限。"""
        if self.max_runtime_sec is None:
            return False
        return self._elapsed_sec() >= self.max_runtime_sec
