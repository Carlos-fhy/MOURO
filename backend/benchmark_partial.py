# 部分基准测试 —— 仅重跑三个对照算法，复用已有的改进ACO和OR-Tools结果
import os
import sys
import json
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import functools
print = functools.partial(print, flush=True)

from app import create_app
from app.data.loader import load_solomon_to_db
from app.algorithm.standard_aco import StandardACO
from app.algorithm.genetic import GeneticAlgorithm
from app.algorithm.simulated_annealing import SimulatedAnnealing

SOLOMON_FILES = ["c101.txt", "c201.txt", "r101.txt", "r201.txt", "rc101.txt", "rc201.txt"]

ALGORITHMS = {
    "标准ACO": StandardACO,
    "遗传算法": GeneticAlgorithm,
    "模拟退火": SimulatedAnnealing,
}

RUNS_PER_ALGO = 5


def run_single_dataset(filepath):
    """对单个算例仅运行三个对照算法"""
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
                "time": round(elapsed, 2),
                "convergence": result.convergence,
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
            "avg_time": round(
                float(np.mean([r["time"] for r in algo_results])), 2
            ),
            "convergence": algo_results[best_idx]["convergence"],
        }

    return dataset_name, results


def main():
    app = create_app()
    data_dir = os.path.join(os.path.dirname(__file__), "data", "solomon")

    # 读取已有结果
    json_path = os.path.join(
        os.path.dirname(__file__), "..", "frontend", "public", "benchmark.json"
    )
    with open(json_path, "r", encoding="utf-8") as f:
        all_results = json.load(f)

    # 建立 dataset_name → 索引 的映射
    name_to_idx = {}
    for i, entry in enumerate(all_results):
        name = entry["dataset"].replace("Solomon ", "")
        name_to_idx[name] = i

    with app.app_context():
        for filename in SOLOMON_FILES:
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath):
                print(f"跳过: {filepath}")
                continue

            dataset_name, new_results = run_single_dataset(filepath)

            idx = name_to_idx.get(dataset_name)
            if idx is None:
                print(f"警告: benchmark.json 中未找到 {dataset_name}，跳过")
                continue

            # 用新结果覆盖三个对照算法，保留改进ACO和OR-Tools
            for algo_name, algo_data in new_results.items():
                all_results[idx]["algorithms"][algo_name] = algo_data

            # 重新计算准确率
            ortools_f1 = all_results[idx]["algorithms"]["OR-Tools"]["best_f1"]
            if ortools_f1 > 0:
                for algo_name in new_results:
                    algo_f1 = new_results[algo_name]["best_f1"]
                    accuracy = min(ortools_f1 / algo_f1,
                                   algo_f1 / ortools_f1) * 100
                    all_results[idx]["algorithms"][algo_name][
                        "accuracy_vs_ortools"
                    ] = round(accuracy, 1)
                    print(f"    {algo_name} vs OR-Tools: {accuracy:.1f}%")

    # 保存
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已合并保存到: {json_path}")


if __name__ == "__main__":
    main()
