# 基准性能测试脚本 —— 在全部 Solomon 算例上运行所有算法并生成对比数据
import os
import sys
import json
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 强制刷新输出（解决后台运行时缓冲问题）
import functools
print = functools.partial(print, flush=True)

from app import create_app
from app.data.loader import load_solomon_to_db
from app.algorithm.improved_aco import ImprovedACO
from app.algorithm.standard_aco import StandardACO
from app.algorithm.genetic import GeneticAlgorithm
from app.algorithm.simulated_annealing import SimulatedAnnealing
from app.algorithm.ortools_solver import ORToolsSolver


# Solomon 算例文件列表
SOLOMON_FILES = ["c101.txt", "c201.txt", "r101.txt", "r201.txt", "rc101.txt", "rc201.txt"]

ALGORITHMS = {
    "改进ACO": ImprovedACO,
    "标准ACO": StandardACO,
    "遗传算法": GeneticAlgorithm,
    "模拟退火": SimulatedAnnealing,
}

LAMBDA_CONFIGS = {
    "省钱优先": [0.7, 0.15, 0.15],
    "抢时间": [0.15, 0.7, 0.15],
    "均衡": [0.33, 0.33, 0.34],
}

RUNS_PER_ALGO = 5


def run_single_dataset(filepath):
    """对单个 Solomon 算例运行全部算法，返回结果字典"""
    dataset = load_solomon_to_db(filepath)
    customers = dataset["customers"]
    depot = dataset["depot"]
    dist_matrix = dataset["distance_matrix"]
    Q = dataset["vehicle_capacity"]

    filename = os.path.basename(filepath)
    dataset_name = filename.replace(".txt", "").upper()
    print(f"\n{'#'*60}")
    print(f"# 数据集: {dataset_name}  客户数: {len(customers)}  容量: {Q}")
    print(f"{'#'*60}")

    lambdas = [0.33, 0.33, 0.34]
    base_params = {
        "lambdas": lambdas,
        "vehicle_capacity": Q,
        "max_iterations": 300,
        "patience": 80,
        "seed": 42,
    }

    results = {}

    # 运行四种元启发式算法
    for algo_name, AlgoClass in ALGORITHMS.items():
        print(f"\n  运行 {algo_name} ({RUNS_PER_ALGO} 次)...")
        algo_results = []

        for run_idx in range(RUNS_PER_ALGO):
            params = {**base_params, "seed": 42 + run_idx}
            algo = AlgoClass(customers, depot, dist_matrix, None, params)
            t0 = time.time()
            result = algo.solve()
            elapsed = time.time() - t0

            algo_results.append({
                "f1": result.f1, "f2": result.f2, "f3": result.f3,
                "z": result.z, "vehicles_used": result.vehicles_used,
                "time": round(elapsed, 2), "convergence": result.convergence,
            })
            print(f"    第{run_idx+1}次: Z={result.z:.4f} F1={result.f1:.1f} "
                  f"F2'={result.f2:.1f} F3={result.f3:.1f} "
                  f"车辆={result.vehicles_used} 耗时={elapsed:.1f}s")

        z_values = [r["z"] for r in algo_results]
        best_idx = int(np.argmin(z_values))

        results[algo_name] = {
            "best_z": round(min(z_values), 4),
            "avg_z": round(float(np.mean(z_values)), 4),
            "std_z": round(float(np.std(z_values)), 4),
            "best_f1": algo_results[best_idx]["f1"],
            "best_f2": algo_results[best_idx]["f2"],
            "best_f3": algo_results[best_idx]["f3"],
            "vehicles_used": algo_results[best_idx]["vehicles_used"],
            "avg_time": round(float(np.mean([r["time"] for r in algo_results])), 2),
            "convergence": algo_results[best_idx]["convergence"],
        }

    # 运行 OR-Tools
    print(f"\n  运行 OR-Tools...")
    ortools_params = {
        "vehicle_capacity": Q,
        "alpha_base": 1.0, "beta_base": 2.0,
        "fixed_cost": 200, "cost_per_km": 5.0,
    }
    t0 = time.time()
    ortools = ORToolsSolver(customers, depot, dist_matrix, None, ortools_params)
    ortools_result = ortools.solve(time_limit_sec=60)
    elapsed = time.time() - t0

    results["OR-Tools"] = {
        "best_z": 0,
        "best_f1": ortools_result.f1,
        "best_f2": ortools_result.f2,
        "best_f3": ortools_result.f3,
        "vehicles_used": ortools_result.vehicles_used,
        "avg_time": round(elapsed, 2),
        "convergence": [],
    }
    print(f"    F1={ortools_result.f1:.1f} F2'={ortools_result.f2:.1f} "
          f"F3={ortools_result.f3:.1f} 车辆={ortools_result.vehicles_used} "
          f"耗时={elapsed:.1f}s")

    # 计算准确率
    ortools_f1 = ortools_result.f1
    if ortools_f1 > 0:
        for algo_name in ALGORITHMS:
            algo_f1 = results[algo_name]["best_f1"]
            accuracy = min(ortools_f1 / algo_f1, algo_f1 / ortools_f1) * 100
            results[algo_name]["accuracy_vs_ortools"] = round(accuracy, 1)
            print(f"    {algo_name} vs OR-Tools: {accuracy:.1f}%")

    # Pareto 近似解（仅改进ACO）
    pareto_points = []
    for config_name, lam in LAMBDA_CONFIGS.items():
        params = {**base_params, "lambdas": lam, "seed": 42}
        algo = ImprovedACO(customers, depot, dist_matrix, None, params)
        result = algo.solve()
        pareto_points.append({
            "name": config_name, "lambdas": lam,
            "f1": result.f1, "f2": result.f2, "f3": result.f3,
            "z": result.z, "vehicles_used": result.vehicles_used,
        })
        print(f"    λ={lam} ({config_name}): Z={result.z:.4f} F1={result.f1:.1f}")

    return {
        "dataset": f"Solomon {dataset_name}",
        "customer_count": len(customers),
        "vehicle_capacity": Q,
        "lambdas": lambdas,
        "algorithms": results,
        "pareto_points": pareto_points,
    }


def run_benchmark():
    """在全部 Solomon 算例上运行基准测试"""
    app = create_app()
    data_dir = os.path.join(os.path.dirname(__file__), "data", "solomon")

    all_results = []

    with app.app_context():
        for filename in SOLOMON_FILES:
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath):
                print(f"跳过不存在的文件: {filepath}")
                continue
            result = run_single_dataset(filepath)
            all_results.append(result)

    # 保存结果
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "frontend", "public", "benchmark.json"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n全部结果已保存到: {output_path}")


if __name__ == "__main__":
    run_benchmark()
