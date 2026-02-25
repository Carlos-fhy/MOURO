# 2-opt 局部搜索 —— 路线内节点交换优化


def two_opt_improve(route, distance_matrix, id_to_idx):
    """对单条路线执行 2-opt 优化

    在路线内尝试所有节点对的反转操作，接受能缩短总距离的交换。
    重复直到无法继续改善。

    参数:
        route: 单条路线节点ID列表，如 [0, 3, 7, 12, 0]
        distance_matrix: 距离矩阵
        id_to_idx: 节点ID到矩阵索引的映射
    返回:
        优化后的路线
    """
    if len(route) <= 4:
        # 路线中客户数 ≤ 2，无法做 2-opt
        return route

    improved = True
    best = list(route)

    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                delta = _calc_delta(best, i, j, distance_matrix, id_to_idx)
                if delta < -1e-10:
                    # 反转 i..j 段
                    best[i:j + 1] = best[i:j + 1][::-1]
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


def two_opt_routes(routes, distance_matrix, id_to_idx):
    """对所有路线执行 2-opt 优化

    参数:
        routes: 路线列表
        distance_matrix: 距离矩阵
        id_to_idx: 节点ID到矩阵索引的映射
    返回:
        优化后的路线列表
    """
    return [two_opt_improve(r, distance_matrix, id_to_idx) for r in routes]


def relocate_improve(routes, distance_matrix, id_to_idx, customers_dict, capacity):
    """路线间 relocate 算子 —— 尝试将客户从一条路线迁移到另一条路线的最佳位置

    反复扫描所有路线对，找到能减少总距离的迁移操作并执行，
    直到无法继续改善为止。

    参数:
        routes: 路线列表
        distance_matrix: 距离矩阵
        id_to_idx: 节点ID到矩阵索引映射
        customers_dict: 客户ID到信息的映射
        capacity: 车辆容量
    返回:
        优化后的路线列表
    """
    routes = [list(r) for r in routes]
    improved = True

    while improved:
        improved = False
        best_saving = -1e-10
        best_move = None

        for ri in range(len(routes)):
            if len(routes[ri]) <= 3:
                continue
            for pos_i in range(1, len(routes[ri]) - 1):
                cid = routes[ri][pos_i]
                # 移除 cid 后的距离节省
                saving_remove = _removal_saving(
                    routes[ri], pos_i, distance_matrix, id_to_idx
                )

                for rj in range(len(routes)):
                    if ri == rj:
                        continue
                    # 检查容量约束
                    demand = _get_demand(cid, customers_dict)
                    route_load = sum(
                        _get_demand(routes[rj][k], customers_dict)
                        for k in range(1, len(routes[rj]) - 1)
                    )
                    if route_load + demand > capacity:
                        continue

                    # 找 rj 中最佳插入位置
                    best_insert_cost, best_insert_pos = _best_insertion(
                        routes[rj], cid, distance_matrix, id_to_idx
                    )
                    total_saving = saving_remove - best_insert_cost
                    if total_saving > best_saving:
                        best_saving = total_saving
                        best_move = (ri, pos_i, rj, best_insert_pos)

        if best_move:
            ri, pos_i, rj, insert_pos = best_move
            cid = routes[ri][pos_i]
            routes[ri].pop(pos_i)
            routes[rj].insert(insert_pos, cid)
            improved = True

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


def full_local_search(routes, distance_matrix, id_to_idx, customers_dict, capacity):
    """完整局部搜索：先 2-opt 路线内优化，再 relocate 路线间优化

    参数:
        routes: 路线列表
        distance_matrix: 距离矩阵
        id_to_idx: 节点ID到矩阵索引映射
        customers_dict: 客户ID到信息的映射
        capacity: 车辆容量
    返回:
        优化后的路线列表
    """
    # 第一步：路线内 2-opt
    routes = two_opt_routes(routes, distance_matrix, id_to_idx)
    # 第二步：路线间 relocate
    routes = relocate_improve(routes, distance_matrix, id_to_idx, customers_dict, capacity)
    # 第三步：再做一轮 2-opt（relocate 后路线结构变了）
    routes = two_opt_routes(routes, distance_matrix, id_to_idx)
    return routes
