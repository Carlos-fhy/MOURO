# 数据加载编排模块 —— 串联解析、标注、距离矩阵、入库的完整流水线
import os
import numpy as np

from app.data.solomon_parser import parse_solomon_file, assign_emergency_levels
from app.data.seoul_parser import parse_seoul_file
from app.data.field_generator import generate_fields
from app.utils.distance import euclidean_distance_matrix
from app.models.database import delete_dataset, insert_nodes, insert_customers


def load_solomon_to_db(filepath, dataset_id=None):
    """
    Solomon 数据完整入库流水线：解析 → 应急等级标注 → 距离矩阵 → 写入数据库

    参数:
        filepath: Solomon .txt 文件路径
        dataset_id: 数据集标识，默认根据文件名生成（如 solomon_c101）
    返回:
        dict，包含 depot、customers、distance_matrix、t_max 等信息
    """
    # 1. 解析 Solomon 文件
    parsed = parse_solomon_file(filepath)

    if dataset_id is None:
        # 从文件名生成 dataset_id，如 "solomon_c101"
        basename = os.path.splitext(os.path.basename(filepath))[0].lower()
        dataset_id = f"solomon_{basename}"

    # 2. 分配应急等级（基于时间窗宽度百分位）
    customers = assign_emergency_levels(parsed["customers"])
    depot = parsed["depot"]

    # 3. 计算欧氏距离矩阵（depot + 所有客户）
    all_nodes = [depot] + customers
    dist_matrix = euclidean_distance_matrix(all_nodes)

    # 4. 清除旧数据并写入数据库
    delete_dataset(dataset_id)

    # 插入节点（depot + customers）
    node_records = [
        {"id": n["id"], "type": n["type"], "x_coord": n["x_coord"], "y_coord": n["y_coord"]}
        for n in all_nodes
    ]
    insert_nodes(node_records, dataset_id)

    # 插入客户详情
    customer_records = [
        {
            "node_id": c["id"],
            "demand_weight": c["demand"],
            "service_time": c["service_time"],
            "early_time": c["early_time"],
            "late_time": c["late_time"],
            "emergency_level": c["emergency_level"],
            "emergency_weight": c["emergency_weight"],
        }
        for c in customers
    ]
    insert_customers(customer_records, dataset_id)

    return {
        "dataset_id": dataset_id,
        "depot": depot,
        "customers": customers,
        "distance_matrix": dist_matrix,
        "t_max": parsed["t_max"],
        "vehicle_capacity": parsed["vehicle_capacity"],
        "node_count": len(all_nodes),
    }


def load_seoul_to_db(instance_dir, emergency_ratio=None, seed=42, dataset_id=None):
    """
    首尔数据完整入库流水线：解析 → 生成缺失字段 → 写入数据库

    参数:
        instance_dir: 首尔 ACVRP 实例目录路径
        emergency_ratio: 应急等级比例，如 {"medical": 10, "fresh": 20, "normal": 70}
        seed: 随机种子
        dataset_id: 数据集标识，默认根据目录名生成
    返回:
        dict，包含 depot、customers、distance_matrix 等信息
    """
    # 1. 解析首尔数据目录
    parsed = parse_seoul_file(instance_dir)

    if dataset_id is None:
        dataset_id = f"seoul_{parsed['name'].lower()}"

    depot = parsed["depot"]
    customers = parsed["customers"]

    # 2. 获取距离矩阵
    if parsed["distance_matrix"] is not None:
        dist_matrix = np.array(parsed["distance_matrix"])
    else:
        # 无距离矩阵时用欧氏距离
        all_nodes = [depot] + customers
        dist_matrix = euclidean_distance_matrix(all_nodes)

    # 2.5 获取时间矩阵（首尔数据含独立时间矩阵，与距离矩阵不同）
    if parsed.get("time_matrix") is not None:
        time_matrix = np.array(parsed["time_matrix"])
    else:
        time_matrix = dist_matrix

    # 3. 生成缺失字段（需求量、服务时间、应急等级、时间窗）
    customers = generate_fields(
        customers, dist_matrix,
        emergency_ratio=emergency_ratio, seed=seed,
        time_matrix=time_matrix,
    )

    # 4. 清除旧数据并写入数据库
    delete_dataset(dataset_id)

    all_nodes = [depot] + customers
    node_records = [
        {"id": n["id"], "type": n["type"],
         "x_coord": n["x_coord"], "y_coord": n["y_coord"]}
        for n in all_nodes
    ]
    insert_nodes(node_records, dataset_id)

    customer_records = [
        {
            "node_id": c["id"],
            "demand_weight": c["demand_weight"],
            "service_time": c["service_time"],
            "early_time": c["early_time"],
            "late_time": c["late_time"],
            "emergency_level": c["emergency_level"],
            "emergency_weight": c["emergency_weight"],
        }
        for c in customers
    ]
    insert_customers(customer_records, dataset_id)

    return {
        "dataset_id": dataset_id,
        "depot": depot,
        "customers": customers,
        "distance_matrix": dist_matrix,
        "time_matrix": time_matrix,
        "capacity": parsed["capacity"],
        "node_count": len(all_nodes),
    }
