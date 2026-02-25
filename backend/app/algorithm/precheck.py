# 不可达客户预检模块 —— 算法启动前检测硬时间窗客户可达性


def precheck_reachability(customers, depot, time_matrix, id_to_idx):
    """检测硬时间窗客户的可达性

    对每个 medical 客户检查：从 depot 直达的最短时间是否超过其最晚时间。
    若 t_min_arrive > LT_i，则该客户不可达，应从求解列表中剔除。

    参数:
        customers: 客户列表
        depot: 配送中心
        time_matrix: 时间矩阵
        id_to_idx: 节点ID到矩阵索引的映射
    返回:
        (reachable, unreachable) 两个列表
    """
    depot_idx = id_to_idx[depot["id"]]
    reachable = []
    unreachable = []

    for c in customers:
        if c.get("emergency_level") == "medical":
            c_idx = id_to_idx[c["id"]]
            t_min = time_matrix[depot_idx][c_idx]
            if t_min > c.get("late_time", float("inf")):
                unreachable.append(c)
                continue
        reachable.append(c)

    return reachable, unreachable
