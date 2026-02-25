# 距离矩阵计算单元测试
import os
import sys
import math
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.distance import euclidean_distance_matrix


class TestEuclideanDistanceMatrix:
    """测试欧氏距离矩阵计算"""

    def test_three_nodes(self):
        """用3节点小算例验证距离矩阵数值正确"""
        nodes = [
            {"x_coord": 0, "y_coord": 0},
            {"x_coord": 3, "y_coord": 4},
            {"x_coord": 6, "y_coord": 0},
        ]
        matrix = euclidean_distance_matrix(nodes)

        # d(0,1) = sqrt(9+16) = 5.0
        assert abs(matrix[0][1] - 5.0) < 1e-10
        # d(0,2) = 6.0
        assert abs(matrix[0][2] - 6.0) < 1e-10
        # d(1,2) = sqrt(9+16) = 5.0
        assert abs(matrix[1][2] - 5.0) < 1e-10

    def test_symmetry(self):
        """验证距离矩阵对称性: d(i,j) == d(j,i)"""
        nodes = [
            {"x_coord": 0, "y_coord": 0},
            {"x_coord": 3, "y_coord": 4},
            {"x_coord": 6, "y_coord": 0},
        ]
        matrix = euclidean_distance_matrix(nodes)
        n = len(nodes)
        for i in range(n):
            for j in range(n):
                assert abs(matrix[i][j] - matrix[j][i]) < 1e-10

    def test_diagonal_zero(self):
        """验证对角线元素为0"""
        nodes = [
            {"x_coord": 1, "y_coord": 2},
            {"x_coord": 3, "y_coord": 4},
        ]
        matrix = euclidean_distance_matrix(nodes)
        for i in range(len(nodes)):
            assert matrix[i][i] == 0.0

    def test_shape(self):
        """验证矩阵形状正确"""
        nodes = [
            {"x_coord": i, "y_coord": i}
            for i in range(5)
        ]
        matrix = euclidean_distance_matrix(nodes)
        assert matrix.shape == (5, 5)

    def test_single_node(self):
        """验证单节点情况"""
        nodes = [{"x_coord": 10, "y_coord": 20}]
        matrix = euclidean_distance_matrix(nodes)
        assert matrix.shape == (1, 1)
        assert matrix[0][0] == 0.0
