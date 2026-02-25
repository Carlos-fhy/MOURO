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
