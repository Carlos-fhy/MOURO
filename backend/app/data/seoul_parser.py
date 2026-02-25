# 首尔 ACVRP 数据集解析器（CSV 格式）
import os
import csv
import numpy as np


def parse_seoul_file(instance_dir):
    """
    解析首尔 ACVRP 数据实例目录

    参数:
        instance_dir: 实例目录路径（如 .../01. SLAS100/）
    返回:
        dict，包含以下字段:
        - name: 实例名称
        - dimension: 节点数（含 depot）
        - depot: dict，配送中心节点信息
        - customers: list[dict]，客户节点列表（仅含坐标）
        - distance_matrix: 非对称距离矩阵（numpy 数组）
        - time_matrix: 非对称时间矩阵（numpy 数组）
        - capacity: 车辆容量（若有）
    """
    if not os.path.isdir(instance_dir):
        raise FileNotFoundError(
            f"首尔数据目录不存在: {instance_dir}\n"
            "请从 Mendeley 下载 ACVRP 数据集: "
            "https://data.mendeley.com/datasets/5db8mtw4wg/1\n"
            "将文件放入 backend/data/seoul/ 目录"
        )

    # 从目录名提取实例名称
    dir_name = os.path.basename(instance_dir)
    name = dir_name.split(". ")[-1] if ". " in dir_name else dir_name

    # 查找坐标文件
    coord_file = _find_file(instance_dir, "Coordinates.csv")
    if coord_file is None:
        raise FileNotFoundError(f"未找到坐标文件: {instance_dir}/*Coordinates.csv")

    # 解析坐标
    nodes = _parse_coordinates(coord_file)
    dimension = len(nodes)

    # 解析距离矩阵
    dist_file = _find_file(instance_dir, "Cost_Distance.csv")
    distance_matrix = _parse_matrix(dist_file, dimension) if dist_file else None

    # 解析时间矩阵
    time_file = _find_file(instance_dir, "Cost_Time.csv")
    time_matrix = _parse_matrix(time_file, dimension) if time_file else None

    # 解析车辆容量（取 V1 型车辆）
    capacity = _parse_capacity(instance_dir)

    # 分离 depot（索引0）和客户
    depot = nodes[0]
    depot["type"] = "depot"
    customers = nodes[1:]
    for c in customers:
        c["type"] = "customer"

    return {
        "name": name,
        "dimension": dimension,
        "depot": depot,
        "customers": customers,
        "distance_matrix": distance_matrix,
        "time_matrix": time_matrix,
        "capacity": capacity,
    }


def _find_file(directory, suffix):
    """在目录中查找以指定后缀结尾的文件"""
    for f in os.listdir(directory):
        if f.endswith(suffix):
            return os.path.join(directory, f)
    return None


def _parse_coordinates(filepath):
    """
    解析坐标 CSV 文件

    格式: node_id,longitude,latitude（无表头）
    返回: 节点列表 [{"id": int, "x_coord": float, "y_coord": float}, ...]
    """
    nodes = []
    with open(filepath, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            nodes.append({
                "id": int(row[0]),
                "x_coord": float(row[1]),  # 经度
                "y_coord": float(row[2]),  # 纬度
            })
    return nodes


def _parse_matrix(filepath, dimension):
    """
    解析成本矩阵 CSV 文件（距离或时间）

    格式: 每行为从节点 i 到所有节点的成本值，逗号分隔，无表头
    返回: numpy 二维数组 shape=(dimension, dimension)
    """
    matrix = []
    with open(filepath, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            matrix.append([float(v) for v in row])
    return np.array(matrix)


def _parse_capacity(instance_dir):
    """
    解析车辆容量文件（优先取 V1 型车辆）

    返回: 容量值（float），未找到文件时返回默认值 1000
    """
    v1_file = _find_file(instance_dir, "Vehicle_V1.csv")
    if v1_file is None:
        return 1000.0

    with open(v1_file, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                return float(row[1])
            elif row:
                return float(row[0])
    return 1000.0


def get_seoul_instances(data_dir):
    """
    扫描目录返回可用的首尔 ACVRP 数据实例列表

    参数:
        data_dir: 首尔数据根目录（含 "ACVRP Benchmark Instances" 子目录）
    返回:
        list[dict]，每个元素包含 name（显示名）和 path（实例目录路径）
    """
    instances = []
    if not os.path.isdir(data_dir):
        return instances

    # 查找 ACVRP Benchmark Instances 子目录
    benchmark_dir = os.path.join(data_dir, "ACVRP Benchmark Instances")
    if not os.path.isdir(benchmark_dir):
        benchmark_dir = data_dir

    for dirname in sorted(os.listdir(benchmark_dir)):
        full_path = os.path.join(benchmark_dir, dirname)
        if not os.path.isdir(full_path):
            continue
        # 跳过 _Solutions 等非实例目录
        coord_file = _find_file(full_path, "Coordinates.csv")
        if coord_file is None:
            continue

        display_name = dirname.split(". ")[-1] if ". " in dirname else dirname
        instances.append({
            "name": display_name,
            "path": full_path,
        })

    return instances
