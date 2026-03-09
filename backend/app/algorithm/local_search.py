# 2-opt 局部搜索 —— 路线内节点交换优化
import math


def tw_attractiveness(arrival, et, lt, level):
    """计算时间窗吸引力因子，用于 ACO 构造阶段的概率计算

    到达时间在 [ET, LT] 内 → 1.0；偏离越大 → 指数衰减。
    下限 0.1 保留随机探索能力，不会排除任何可行客户。
    medical 客户已通过硬约束过滤，直接返回 1.0。

    参数:
        arrival: 预计到达时间
        et: 最早服务时间
        lt: 最晚服务时间
        level: 应急等级 ('medical'/'fresh'/'normal')
    返回:
        吸引力因子，范围 [0.1, 1.0]
    """
    # medical 已通过硬约束过滤，不需要额外软惩罚
    if level == "medical":
        return 1.0

    # 在时间窗内，吸引力最大
    if et <= arrival <= lt:
        return 1.0

    # 时间窗宽度，用于归一化偏离程度
    window = max(lt - et, 1.0)

    if arrival < et:
        deviation = (et - arrival) / window
    else:
        deviation = (arrival - lt) / window

    # 指数衰减，下限 0.1
    return max(0.1, math.exp(-2.0 * deviation))


def _route_tw_feasible(route, time_matrix, id_to_idx, customers_dict):
    """检查整条路线是否满足时间窗约束（所有等级客户均不迟到）

    参数:
        route: 路线节点ID列表，如 [0, 3, 7, 12, 0]
        time_matrix: 时间矩阵（None 时跳过检查，返回 True）
        id_to_idx: 节点ID到矩阵索引映射
        customers_dict: 客户ID到信息的映射
    返回:
        True 表示可行，False 表示存在迟到
    """
    if time_matrix is None:
        return True
    current_time = 0.0
    for k in range(1, len(route) - 1):
        prev_idx = id_to_idx[route[k - 1]]
        curr_idx = id_to_idx[route[k]]
        travel = time_matrix[prev_idx][curr_idx]
        arrival = current_time + travel

        c_info = customers_dict.get(route[k], {})
        et = c_info.get("early_time", 0)
        lt = c_info.get("late_time", float("inf"))
        st = c_info.get("service_time", 0)
        level = c_info.get("emergency_level", "normal")

        if arrival > lt:
            return False

        if arrival < et and level == "medical":
            current_time = et + st
        else:
            current_time = max(arrival, et) + st if level == "medical" else arrival + st
    return True


def two_opt_improve(route, distance_matrix, id_to_idx, max_passes=100,
                    time_matrix=None, customers_dict=None):
    """对单条路线执行 2-opt 优化

    在路线内尝试所有节点对的反转操作，接受能缩短总距离且不违反时间窗的交换。
    重复直到无法继续改善或达到最大轮次。

    参数:
        route: 单条路线节点ID列表，如 [0, 3, 7, 12, 0]
        distance_matrix: 距离矩阵
        id_to_idx: 节点ID到矩阵索引的映射
        max_passes: 最大迭代轮次（默认100，防止大规模实例卡死）
        time_matrix: 时间矩阵（可选，传入时启用时间窗校验）
        customers_dict: 客户信息字典（可选，配合 time_matrix 使用）
    返回:
        优化后的路线
    """
    if len(route) <= 4:
        return route

    improved = True
    best = list(route)
    passes = 0

    while improved and passes < max_passes:
        improved = False
        passes += 1
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                delta = _calc_delta(best, i, j, distance_matrix, id_to_idx)
                if delta < -1e-10:
                    # 先反转，再校验时间窗
                    candidate = list(best)
                    candidate[i:j + 1] = candidate[i:j + 1][::-1]
                    if _route_tw_feasible(candidate, time_matrix,
                                          id_to_idx, customers_dict):
                        best = candidate
                        improved = True
    return best


def _calc_delta(route, i, j, distance_matrix, id_to_idx):
    """计算 2-opt 交换的距离变化量

    交换前边: (i-1, i) + (j, j+1)
    交换后边: (i-1, j) + (i, j+1)
    delta = 新距离 - 旧距离，负值表示改善
    """
    a = id_to_idx[route[i - 1]]
    b = id_to_idx[route[i]]
    c = id_to_idx[route[j]]
    d = id_to_idx[route[j + 1]]

    old_dist = distance_matrix[a][b] + distance_matrix[c][d]
    new_dist = distance_matrix[a][c] + distance_matrix[b][d]
    return new_dist - old_dist


def two_opt_routes(routes, distance_matrix, id_to_idx,
                   time_matrix=None, customers_dict=None):
    """对所有路线执行 2-opt 优化

    参数:
        routes: 路线列表
        distance_matrix: 距离矩阵
        id_to_idx: 节点ID到矩阵索引的映射
        time_matrix: 时间矩阵（可选，传入时启用时间窗校验）
        customers_dict: 客户信息字典（可选）
    返回:
        优化后的路线列表
    """
    return [two_opt_improve(r, distance_matrix, id_to_idx,
                            time_matrix=time_matrix,
                            customers_dict=customers_dict)
            for r in routes]


def relocate_improve(routes, distance_matrix, id_to_idx, customers_dict, capacity,
                     max_rounds=50, time_matrix=None):
    """路线间 relocate 算子 —— 尝试将客户从一条路线迁移到另一条路线的最佳位置

    采用 first-improvement 策略：找到第一个能改善的迁移就立即执行，
    避免 best-improvement 的全量扫描开销。设有最大轮次上限防止极端情况。
    传入 time_matrix 时，迁移前校验源路线和目标路线的时间窗可行性。

    参数:
        routes: 路线列表
        distance_matrix: 距离矩阵
        id_to_idx: 节点ID到矩阵索引映射
        customers_dict: 客户ID到信息的映射
        capacity: 车辆容量
        max_rounds: 最大迭代轮次（默认50）
        time_matrix: 时间矩阵（可选，传入时启用时间窗校验）
    返回:
        优化后的路线列表
    """
    routes = [list(r) for r in routes]

    # 预计算并缓存每条路线的载重
    loads = [
        sum(_get_demand(r[k], customers_dict) for k in range(1, len(r) - 1))
        for r in routes
    ]

    for _ in range(max_rounds):
        moved = False

        for ri in range(len(routes)):
            if len(routes[ri]) <= 3:
                continue
            for pos_i in range(1, len(routes[ri]) - 1):
                cid = routes[ri][pos_i]
                demand = _get_demand(cid, customers_dict)
                saving_remove = _removal_saving(
                    routes[ri], pos_i, distance_matrix, id_to_idx
                )

                for rj in range(len(routes)):
                    if ri == rj:
                        continue
                    # 用缓存的载重检查容量约束
                    if loads[rj] + demand > capacity:
                        continue

                    best_insert_cost, best_insert_pos = _best_insertion(
                        routes[rj], cid, distance_matrix, id_to_idx
                    )
                    # first-improvement：找到改善立即执行
                    if saving_remove - best_insert_cost > 1e-10:
                        # 模拟迁移，校验时间窗可行性
                        if time_matrix is not None:
                            new_rj = list(routes[rj])
                            new_rj.insert(best_insert_pos, cid)
                            new_ri = list(routes[ri])
                            new_ri.pop(pos_i)
                            if (not _route_tw_feasible(new_rj, time_matrix,
                                                       id_to_idx, customers_dict)
                                or not _route_tw_feasible(new_ri, time_matrix,
                                                          id_to_idx, customers_dict)):
                                continue  # 时间窗不可行，跳过
                        routes[ri].pop(pos_i)
                        routes[rj].insert(best_insert_pos, cid)
                        loads[ri] -= demand
                        loads[rj] += demand
                        moved = True
                        break  # 跳出 rj 循环，重新扫描
                if moved:
                    break  # 跳出 pos_i 循环
            if moved:
                break  # 跳出 ri 循环，开始新一轮

        if not moved:
            break

    # 移除空路线（只剩 depot→depot）
    routes = [r for r in routes if len(r) > 2]
    return routes


def _removal_saving(route, pos, distance_matrix, id_to_idx):
    """计算从路线中移除 pos 位置客户后的距离节省"""
    prev = id_to_idx[route[pos - 1]]
    curr = id_to_idx[route[pos]]
    nxt = id_to_idx[route[pos + 1]]
    old = distance_matrix[prev][curr] + distance_matrix[curr][nxt]
    new = distance_matrix[prev][nxt]
    return old - new


def _best_insertion(route, cid, distance_matrix, id_to_idx):
    """找到将 cid 插入 route 的最佳位置，返回 (插入成本增量, 插入位置)"""
    c_idx = id_to_idx[cid]
    best_cost = float("inf")
    best_pos = 1

    for pos in range(1, len(route)):
        prev = id_to_idx[route[pos - 1]]
        nxt = id_to_idx[route[pos]]
        cost = (distance_matrix[prev][c_idx] + distance_matrix[c_idx][nxt]
                - distance_matrix[prev][nxt])
        if cost < best_cost:
            best_cost = cost
            best_pos = pos

    return best_cost, best_pos


def _get_demand(node_id, customers_dict):
    """获取节点需求量，depot 返回 0"""
    if node_id not in customers_dict:
        return 0
    c = customers_dict[node_id]
    return c.get("demand", c.get("demand_weight", 0))


def repair_late_customers(routes, time_matrix, id_to_idx, customers_dict):
    """通过重新插入修复迟到客户。

    修复对象：
    1. medical 客户：任何迟到都修复（硬时间窗不可行）
    2. fresh 客户：严重迟到（超过 LT 20% 以上）才修复，轻微迟到由惩罚函数处理
    """
    if time_matrix is None or not routes:
        return [list(r) for r in routes]

    routes = [list(r) for r in routes]
    depot_id = routes[0][0]
    late_entries = []

    for ri, route in enumerate(routes):
        current_time = 0.0
        for k in range(1, len(route) - 1):
            prev_idx = id_to_idx[route[k - 1]]
            curr_idx = id_to_idx[route[k]]
            travel = time_matrix[prev_idx][curr_idx]
            arrival = current_time + travel

            cid = route[k]
            c_info = customers_dict.get(cid, {})
            et = c_info.get("early_time", 0)
            lt = c_info.get("late_time", float("inf"))
            st = c_info.get("service_time", 0)
            level = c_info.get("emergency_level", "normal")

            # medical：任何迟到都修复
            if level == "medical" and arrival > lt:
                late_entries.append((ri, k, cid))
            # fresh：超过 LT 20% 的严重迟到才修复
            elif level == "fresh" and lt < float("inf"):
                threshold = lt * 1.2
                if arrival > threshold:
                    late_entries.append((ri, k, cid))

            if arrival < et and level == "medical":
                current_time = et + st
            else:
                current_time = max(arrival, et) + st if level == "medical" else arrival + st

    if not late_entries:
        return routes

    removed = []
    for ri, pos, cid in reversed(late_entries):
        routes[ri].pop(pos)
        removed.append(cid)
    removed.reverse()

    for cid in removed:
        placed = False
        for ri, route in enumerate(routes):
            if len(route) <= 2:
                continue
            for pos in range(1, len(route)):
                if _check_arrival_ok(route, pos, cid, time_matrix, id_to_idx, customers_dict):
                    routes[ri].insert(pos, cid)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            routes.append([depot_id, cid, depot_id])

    routes = [r for r in routes if len(r) > 2]
    return routes


def _check_arrival_ok(route, insert_pos, cid, time_matrix, id_to_idx, customers_dict):
    """检查插入后是否造成 medical 迟到或 fresh 严重迟到。

    保护规则：
    1. medical：到达时间 > LT 即不可行
    2. fresh：到达时间 > LT × 1.2 即不可行（与 repair 阈值一致）
    """
    test_route = list(route)
    test_route.insert(insert_pos, cid)
    current_time = 0.0

    for k in range(1, len(test_route) - 1):
        prev_idx = id_to_idx[test_route[k - 1]]
        curr_idx = id_to_idx[test_route[k]]
        travel = time_matrix[prev_idx][curr_idx]
        arrival = current_time + travel

        node_id = test_route[k]
        c_info = customers_dict.get(node_id, {})
        et = c_info.get("early_time", 0)
        lt = c_info.get("late_time", float("inf"))
        st = c_info.get("service_time", 0)
        level = c_info.get("emergency_level", "normal")

        # medical：任何迟到不可行
        if level == "medical" and arrival > lt:
            return False
        # fresh：严重迟到不可行（与 repair 阈值一致）
        if level == "fresh" and lt < float("inf") and arrival > lt * 1.2:
            return False

        if arrival < et and level == "medical":
            current_time = et + st
        else:
            current_time = max(arrival, et) + st if level == "medical" else arrival + st

    return True


def full_local_search(routes, distance_matrix, id_to_idx, customers_dict, capacity,
                      time_matrix=None):
    """完整局部搜索：先 2-opt 路线内优化，再 relocate 路线间优化

    传入 time_matrix 时，所有算子在接受改动前校验时间窗可行性，
    避免距离优化破坏构造阶段建立的时间可行解。

    参数:
        routes: 路线列表
        distance_matrix: 距离矩阵
        id_to_idx: 节点ID到矩阵索引映射
        customers_dict: 客户ID到信息的映射
        capacity: 车辆容量
        time_matrix: 时间矩阵（可选，传入时启用时间窗校验）
    返回:
        优化后的路线列表
    """
    # 第一步：路线内 2-opt（时间窗感知）
    routes = two_opt_routes(routes, distance_matrix, id_to_idx,
                            time_matrix=time_matrix, customers_dict=customers_dict)
    # 第二步：路线间 relocate（时间窗感知）
    routes = relocate_improve(routes, distance_matrix, id_to_idx,
                              customers_dict, capacity, time_matrix=time_matrix)
    # 第三步：再做一轮 2-opt（relocate 后路线结构变了）
    routes = two_opt_routes(routes, distance_matrix, id_to_idx,
                            time_matrix=time_matrix, customers_dict=customers_dict)
    return routes
