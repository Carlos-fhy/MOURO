# 距离矩阵计算工具
import numpy as np


def euclidean_distance_matrix(nodes):
    """
    计算节点间的欧氏距离矩阵（对称矩阵）

    参数:
        nodes: 节点列表，每个元素为 dict，包含 x_coord 和 y_coord
    返回:
        numpy 二维数组，shape=(n, n)，其中 n 为节点数
    """
    coords = np.array([[n["x_coord"], n["y_coord"]] for n in nodes])
    # 利用广播计算所有节点对之间的欧氏距离
    # diff[i][j] = coords[i] - coords[j]
    diff = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
    dist_matrix = np.sqrt(np.sum(diff ** 2, axis=2))
    return dist_matrix
