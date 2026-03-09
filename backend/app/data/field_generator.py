# 首尔数据集缺失字段生成器
import numpy as np
from scipy.stats import truncnorm


def generate_fields(customers, distance_matrix, emergency_ratio=None, seed=42,
                     time_matrix=None):
    """
    为首尔数据集客户生成缺失字段（需求量、服务时间、应急等级、时间窗）

    参数:
        customers: 客户列表（含 id, x_coord, y_coord）
        distance_matrix: 距离矩阵（含 depot，索引0为depot）
        emergency_ratio: 应急等级比例 dict，如 {"medical": 10, "fresh": 20, "normal": 70}
        seed: 随机种子，保证可复现
        time_matrix: 时间矩阵（可选，提供时用于生成时间窗，否则用距离矩阵）
    返回:
        修改后的客户列表（原地修改并返回）
    """
    if emergency_ratio is None:
        emergency_ratio = {"medical": 10, "fresh": 20, "normal": 70}

    rng = np.random.RandomState(seed)
    n = len(customers)

    # --- 1. 分配应急等级（按比例随机洗牌）---
    levels = _assign_levels_by_ratio(n, emergency_ratio, rng)

    # --- 2. 生成需求量：截断正态分布 N(50, 20)，范围 [10, 200] ---
    demands = _generate_demands(n, rng)

    # --- 3. 逐客户填充字段 ---
    for i, c in enumerate(customers):
        c["emergency_level"] = levels[i]
        c["emergency_weight"] = _get_weight(levels[i])
        c["demand_weight"] = float(demands[i])
        # 服务时间 = 5 + 0.1 × 需求量（参考 PRD.md 第6.2节）
        c["service_time"] = 5.0 + 0.1 * demands[i]

    # --- 4. 生成时间窗（基于行驶时间反推，优先用 time_matrix）---
    tw_matrix = time_matrix if time_matrix is not None else distance_matrix
    _generate_time_windows(customers, tw_matrix, rng)

    return customers


def _assign_levels_by_ratio(n, ratio, rng):
    """
    按比例分配应急等级并随机洗牌

    参数:
        n: 客户总数
        ratio: 比例 dict，如 {"medical": 10, "fresh": 20, "normal": 70}
        rng: numpy RandomState 实例
    返回:
        list[str]，长度为 n 的应急等级列表
    """
    total = sum(ratio.values())
    medical_n = max(1, round(n * ratio["medical"] / total))
    fresh_n = max(1, round(n * ratio["fresh"] / total))
    normal_n = n - medical_n - fresh_n

    levels = (
        ["medical"] * medical_n
        + ["fresh"] * fresh_n
        + ["normal"] * normal_n
    )
    rng.shuffle(levels)
    return levels


def _get_weight(level):
    """根据应急等级返回权重"""
    weights = {"medical": 2.0, "fresh": 1.5, "normal": 1.0}
    return weights[level]


def _generate_demands(n, rng):
    """
    生成截断正态分布的需求量，范围 [10, 200]，均值50，标准差20

    参数:
        n: 客户数量
        rng: numpy RandomState 实例
    返回:
        numpy 数组，长度为 n
    """
    mu, sigma = 50, 20
    lower, upper = 10, 200
    a = (lower - mu) / sigma
    b = (upper - mu) / sigma
    demands = truncnorm.rvs(a, b, loc=mu, scale=sigma, size=n, random_state=rng)
    return np.round(demands, 1)


# 时间窗宽度范围（参考 PRD.md 第6.2节）
_TW_WIDTH = {
    "medical": (15, 30),
    "fresh": (60, 120),
    "normal": (240, 480),
}


def _generate_time_windows(customers, distance_matrix, rng):
    """
    基于行驶时间反推生成时间窗

    规则（参考 PRD.md 第6.2节）:
        ET_i = t_{0,i} + random(0, 60)
        LT_i = ET_i + W_i
        W_i 按应急等级联动

    参数:
        customers: 客户列表（已含 emergency_level）
        distance_matrix: 距离矩阵，索引0为 depot
        rng: numpy RandomState 实例
    """
    for i, c in enumerate(customers):
        # depot 到客户的最短行驶时间（距离矩阵索引 0 → i+1）
        depot_to_customer = distance_matrix[0][i + 1]

        # ET_i = 行驶时间 + 随机偏移 [0, 60]
        offset = rng.uniform(0, 60)
        et = depot_to_customer + offset

        # 时间窗宽度按应急等级
        level = c["emergency_level"]
        w_min, w_max = _TW_WIDTH[level]
        width = rng.uniform(w_min, w_max)

        c["early_time"] = round(et, 1)
        c["late_time"] = round(et + width, 1)
