# 目标函数计算模块 —— F1(经济成本) / F2'(加权完工时间) / F3(时间窗惩罚) / Z(综合目标)
import numpy as np
from app.utils.normalize import min_max_normalize


def calculate_f1(routes, distance_matrix, id_to_idx,
                 fixed_cost=200, cost_per_km=5.0):
    """计算目标1：纯经济成本 F1 = Σ C_fixed + Σ d_ij × C_per_km

    参数:
        routes: 路线列表，如 [[0,3,7,0], [0,1,5,0]]
        distance_matrix: 距离矩阵（numpy 数组）
        id_to_idx: 节点ID到矩阵索引的映射
        fixed_cost: 单车固定成本
        cost_per_km: 单位距离成本
    返回:
        F1 值（float）
    """
    total = 0.0
    for route in routes:
        if len(route) <= 2:
            continue
        total += fixed_cost
        for k in range(len(route) - 1):
            i_idx = id_to_idx[route[k]]
            j_idx = id_to_idx[route[k + 1]]
            total += distance_matrix[i_idx][j_idx] * cost_per_km
    return total


def calculate_f2(schedule, customers_dict):
    """计算目标2：加权完工时间 F2' = Σ(ω_ei × t_arrive_i)

    参数:
        schedule: 调度明细列表（由 build_schedule 生成）
        customers_dict: 客户ID到客户信息的映射 {id: customer_dict}
    返回:
        F2' 值（float）
    """
    total = 0.0
    for entry in schedule:
        cid = entry["customer_id"]
        if cid in customers_dict:
            omega = customers_dict[cid].get("emergency_weight", 1.0)
            total += omega * entry["arrival_time"]
    return total


def calculate_f3(schedule, customers_dict, alpha_base=1.0, beta_base=2.0):
    """计算目标3：时间窗惩罚成本 F3 = Σ P_i(t)

    惩罚公式: P_i(t) = α_i·max(ET_i - t, 0) + β_i·max(t - LT_i, 0)
    其中 α_i = α_base × ω_ei，β_i = β_base × ω_ei

    参数:
        schedule: 调度明细列表
        customers_dict: 客户ID到客户信息的映射
        alpha_base: 基础早到惩罚系数
        beta_base: 基础迟到惩罚系数
    返回:
        F3 值（float）
    """
    total = 0.0
    for entry in schedule:
        total += entry["penalty"]
    return total


def build_schedule(routes, customers_dict, time_matrix, id_to_idx,
                   alpha_base=1.0, beta_base=2.0):
    """根据路线构建调度明细，计算每个客户的到达/离开时刻和惩罚

    参数:
        routes: 路线列表
        customers_dict: 客户ID到客户信息的映射
        time_matrix: 行驶时间矩阵
        id_to_idx: 节点ID到矩阵索引的映射
        alpha_base: 基础早到惩罚系数
        beta_base: 基础迟到惩罚系数
    返回:
        调度明细列表
    """
    schedule = []
    vehicle_id = 0

    for route in routes:
        if len(route) <= 2:
            continue
        vehicle_id += 1
        current_time = 0.0

        for k in range(1, len(route) - 1):
            prev_idx = id_to_idx[route[k - 1]]
            curr_idx = id_to_idx[route[k]]
            cid = route[k]

            travel = time_matrix[prev_idx][curr_idx]
            arrival = current_time + travel

            cust = customers_dict.get(cid, {})
            et = cust.get("early_time", 0)
            lt = cust.get("late_time", float("inf"))
            st = cust.get("service_time", 0)
            omega = cust.get("emergency_weight", 1.0)
            level = cust.get("emergency_level", "normal")
            demand = cust.get("demand", cust.get("demand_weight", 0))

            penalty = 0.0
            if arrival < et:
                if level == "medical":
                    # 硬时间窗：等待至 ET_i，不产生惩罚
                    status = "early"
                    departure = et + st
                else:
                    # 软时间窗：立即服务，产生早到惩罚
                    alpha_i = alpha_base * omega
                    penalty = alpha_i * (et - arrival)
                    status = "early"
                    departure = arrival + st
            elif arrival > lt:
                beta_i = beta_base * omega
                penalty = beta_i * (arrival - lt)
                status = "late"
                departure = arrival + st
            else:
                status = "on_time"
                departure = arrival + st

            schedule.append({
                "vehicle_id": vehicle_id,
                "customer_id": cid,
                "arrival_time": round(arrival, 2),
                "departure_time": round(departure, 2),
                "demand": demand,
                "penalty": round(penalty, 2),
                "status": status,
            })

            current_time = departure

    return schedule


def calculate_z(f1, f2, f3, f1_bounds, f2_bounds, f3_bounds, lambdas):
    """计算综合目标值 Z = λ₁F1* + λ₂F2'* + λ₃F3*

    参数:
        f1, f2, f3: 三个目标的原始值
        f1_bounds: (f1_min, f1_max) 当前已知边界
        f2_bounds: (f2_min, f2_max)
        f3_bounds: (f3_min, f3_max)
        lambdas: [λ₁, λ₂, λ₃] 权重向量，和为1
    返回:
        Z 值（float）
    """
    f1_star = min_max_normalize(f1, f1_bounds[0], f1_bounds[1])
    f2_star = min_max_normalize(f2, f2_bounds[0], f2_bounds[1])
    f3_star = min_max_normalize(f3, f3_bounds[0], f3_bounds[1])
    return lambdas[0] * f1_star + lambdas[1] * f2_star + lambdas[2] * f3_star


def calculate_reference_z(f1, f2, f3, reference, lambdas, eps=1e-10):
    """计算基于固定参考解的综合目标值。

    默认使用贪心解作为 reference，使贪心解的 Z=1。若某算法在某个
    目标上优于贪心，该目标分量会小于 1；劣于贪心则大于 1。
    这种计算方式不依赖搜索过程中的动态 min/max 边界，适合作为
    最终展示和算法对比的稳定 Z 值。
    """
    ref_f1 = max(abs(reference.get("f1", reference.get("f1_nn", 0.0))), eps)
    ref_f2 = max(abs(reference.get("f2", reference.get("f2_nn", 0.0))), eps)
    ref_f3 = max(abs(reference.get("f3", reference.get("f3_nn", 0.0))), eps)

    return (
        lambdas[0] * (f1 / ref_f1) +
        lambdas[1] * (f2 / ref_f2) +
        lambdas[2] * (f3 / ref_f3)
    )


def evaluate_solution(routes, customers, depot, distance_matrix, time_matrix,
                      id_to_idx, params):
    """一站式评估：给定路线，计算全部目标值和调度明细

    参数:
        routes: 路线列表
        customers: 客户列表
        depot: 配送中心
        distance_matrix: 距离矩阵
        time_matrix: 时间矩阵
        id_to_idx: 节点ID到索引映射
        params: 包含 lambdas, alpha_base, beta_base, fixed_cost, cost_per_km
    返回:
        dict: {f1, f2, f3, schedule, vehicles_used}
    """
    alpha_base = params.get("alpha_base", 1.0)
    beta_base = params.get("beta_base", 2.0)
    fixed_cost = params.get("fixed_cost", 200)
    cost_per_km = params.get("cost_per_km", 5.0)

    customers_dict = {c["id"]: c for c in customers}

    schedule = build_schedule(
        routes, customers_dict, time_matrix, id_to_idx,
        alpha_base, beta_base
    )
    f1 = calculate_f1(routes, distance_matrix, id_to_idx, fixed_cost, cost_per_km)
    f2 = calculate_f2(schedule, customers_dict)
    f3 = calculate_f3(schedule, customers_dict, alpha_base, beta_base)
    vehicles_used = sum(1 for r in routes if len(r) > 2)

    return {
        "f1": f1, "f2": f2, "f3": f3,
        "schedule": schedule,
        "vehicles_used": vehicles_used,
    }
