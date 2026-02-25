# Solomon VRPTW 标准算例解析器
import os


def parse_solomon_file(filepath):
    """
    解析 Solomon 格式的 VRPTW 算例文件

    参数:
        filepath: Solomon .txt 文件路径
    返回:
        dict，包含以下字段:
        - name: 算例名称（如 C101）
        - vehicle_capacity: 车辆载重上限
        - depot: dict，配送中心节点信息
        - customers: list[dict]，客户节点列表
        - t_max: 配送中心的最晚时间（即 depot 的 late_time）
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    # 去除空行和首尾空白
    lines = [line.strip() for line in lines if line.strip()]

    # 第1行：算例名称
    name = lines[0]

    # 跳过表头行，找到 VEHICLE 段
    # Solomon 格式: 名称 → 空行 → VEHICLE → NUMBER CAPACITY → 数值行
    #              → 空行 → CUSTOMER → CUST_NO. ... → 数据行
    vehicle_idx = None
    customer_idx = None
    for i, line in enumerate(lines):
        upper = line.upper()
        if upper.startswith("VEHICLE"):
            vehicle_idx = i
        # 只匹配段标题 "CUSTOMER"，不匹配列头 "CUST NO."
        if upper == "CUSTOMER" or upper.startswith("CUSTOMER") and "NO" not in upper:
            customer_idx = i

    # 解析车辆容量：VEHICLE 段后第2行（跳过 NUMBER CAPACITY 表头）
    capacity_line = lines[vehicle_idx + 2]
    parts = capacity_line.split()
    vehicle_capacity = int(parts[1])

    # 解析节点数据：跳过 CUSTOMER 段标题和列头行
    data_start = customer_idx + 2
    nodes = []
    for line in lines[data_start:]:
        parts = line.split()
        if len(parts) < 7:
            continue
        node = {
            "id": int(parts[0]),
            "x_coord": float(parts[1]),
            "y_coord": float(parts[2]),
            "demand": float(parts[3]),
            "early_time": float(parts[4]),
            "late_time": float(parts[5]),
            "service_time": float(parts[6]),
        }
        nodes.append(node)

    # Node 0 为 depot，其余为客户
    depot = nodes[0]
    depot["type"] = "depot"
    t_max = depot["late_time"]

    customers = nodes[1:]
    for c in customers:
        c["type"] = "customer"

    return {
        "name": name,
        "vehicle_capacity": vehicle_capacity,
        "depot": depot,
        "customers": customers,
        "t_max": t_max,
    }


def assign_emergency_levels(customers):
    """
    根据时间窗宽度百分位为 Solomon 客户分配应急等级

    规则（参考 PRD.md 第6.1节）:
        1. 计算每个客户的时间窗宽度 W_i = late_time - early_time
        2. 按 W_i 升序排序
        3. 前 10%（W_i 最小）→ medical（ω=2.0，硬时间窗）
        4. 第 11%~30%        → fresh（ω=1.5，紧软时间窗）
        5. 剩余 70%          → normal（ω=1.0，宽松软时间窗）

    参数:
        customers: 客户列表（会被原地修改，添加 emergency_level 和 emergency_weight 字段）
    返回:
        修改后的客户列表
    """
    # 计算时间窗宽度并排序
    indexed = [(i, c["late_time"] - c["early_time"]) for i, c in enumerate(customers)]
    indexed.sort(key=lambda x: x[1])

    n = len(indexed)
    # 前 10% → medical
    medical_count = max(1, int(n * 0.10))
    # 第 11%~30% → fresh
    fresh_count = max(1, int(n * 0.20))

    for rank, (idx, _) in enumerate(indexed):
        if rank < medical_count:
            customers[idx]["emergency_level"] = "medical"
            customers[idx]["emergency_weight"] = 2.0
        elif rank < medical_count + fresh_count:
            customers[idx]["emergency_level"] = "fresh"
            customers[idx]["emergency_weight"] = 1.5
        else:
            customers[idx]["emergency_level"] = "normal"
            customers[idx]["emergency_weight"] = 1.0

    return customers


def get_solomon_instances(data_dir):
    """
    扫描目录返回可用的 Solomon 算例列表

    参数:
        data_dir: Solomon 数据文件所在目录
    返回:
        list[dict]，每个元素包含 name（大写显示名）和 filename（小写文件名）
    """
    instances = []
    if not os.path.isdir(data_dir):
        return instances

    for filename in sorted(os.listdir(data_dir)):
        if filename.endswith(".txt") and not filename.startswith("download"):
            display_name = filename.replace(".txt", "").upper()
            instances.append({
                "name": display_name,
                "filename": filename,
            })

    return instances
