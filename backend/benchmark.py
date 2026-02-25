# 基准性能测试脚本 —— 在 Solomon C101 上运行全部算法并生成对比数据
import os
import sys
import json
import time
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.data.loader import load_solomon_to_db
from app.algorithm.improved_aco import ImprovedACO
from app.algorithm.standard_aco import StandardACO
from app.algorithm.genetic import GeneticAlgorithm
from app.algorithm.simulated_annealing import SimulatedAnnealing
from app.algorithm.ortools_solver import ORToolsSolver
from app.utils.objective import calculate_z


def run_benchmark():
    """在 Solomon C101 上运行全部算法，输出对比结果"""
    app = create_app()

    with app.app_context():
        # 1. 加载 C101 数据
        data_dir = os.path.join(os.path.dirname(__file__), "data", "solomon")
        filepath = os.path.join(data_dir, "c101.txt")
        print(f"加载数据: {filepath}")
        dataset = load_solomon_to_db(filepath)

        customers = dataset["customers"]
        depot = dataset["depot"]
        dist_matrix = dataset["distance_matrix"]
        Q = dataset["vehicle_capacity"]
        print(f"客户数: {len(customers)}, 车辆容量: {Q}")

        # 三组 λ 配置
        lambda_configs = {
            "省钱优先": [0.7, 0.15, 0.15],
            "抢时间": [0.15, 0.7, 0.15],
            "均衡": [0.33, 0.33, 0.34],
        }

        # 算法列表
        algorithms = {
            "改进ACO": ImprovedACO,
            "标准ACO": StandardACO,
            "遗传算法": GeneticAlgorithm,
            "模拟退火": SimulatedAnnealing,
        }

        # 使用均衡 λ 做主对比
        lambdas = [0.33, 0.33, 0.34]
        base_params = {
            "lambdas": lambdas,
            "vehicle_capacity": Q,
            "max_iterations": 200,
            "patience": 50,
            "seed": 42,
        }

        results = {}
        runs_per_algo = 5  # 每个算法跑5次取统计量

        # 2. 运行各算法
        for algo_name, AlgoClass in algorithms.items():
            print(f"\n{'='*50}")
            print(f"运行 {algo_name} ({runs_per_algo} 次)...")
            algo_results = []

            for run_idx in range(runs_per_algo):
                params = {**base_params, "seed": 42 + run_idx}
                algo = AlgoClass(customers, depot, dist_matrix, None, params)

                t0 = time.time()
                result = algo.solve()
                elapsed = time.time() - t0

                algo_results.append({
                    "f1": result.f1,
                    "f2": result.f2,
                    "f3": result.f3,
                    "z": result.z,
                    "vehicles_used": result.vehicles_used,
                    "time": round(elapsed, 2),
                    "convergence": result.convergence,
                })
                print(f"  第{run_idx+1}次: Z={result.z:.4f} F1={result.f1:.1f} "
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

        # 3. 运行 OR-Tools 基准解
        print(f"\n{'='*50}")
        print("运行 OR-Tools 精确求解器...")
        ortools_params = {
            "vehicle_capacity": Q,
            "alpha_base": 1.0,
            "beta_base": 2.0,
            "fixed_cost": 200,
            "cost_per_km": 5.0,
        }
        t0 = time.time()
        ortools = ORToolsSolver(customers, depot, dist_matrix, None, ortools_params)
        ortools_result = ortools.solve(time_limit_sec=60)
        elapsed = time.time() - t0

        results["OR-Tools"] = {
            "best_z": 0,  # OR-Tools 不计算归一化Z
            "best_f1": ortools_result.f1,
            "best_f2": ortools_result.f2,
            "best_f3": ortools_result.f3,
            "vehicles_used": ortools_result.vehicles_used,
            "avg_time": round(elapsed, 2),
            "convergence": [],
        }
        print(f"  F1={ortools_result.f1:.1f} F2'={ortools_result.f2:.1f} "
              f"F3={ortools_result.f3:.1f} 车辆={ortools_result.vehicles_used} "
              f"耗时={elapsed:.1f}s")

        # 4. 计算准确率（改进ACO vs OR-Tools，基于F1）
        ortools_f1 = ortools_result.f1
        if ortools_f1 > 0:
            for algo_name in algorithms:
                algo_f1 = results[algo_name]["best_f1"]
                accuracy = min(ortools_f1 / algo_f1, algo_f1 / ortools_f1) * 100
                results[algo_name]["accuracy_vs_ortools"] = round(accuracy, 1)
                print(f"\n{algo_name} vs OR-Tools 准确率: {accuracy:.1f}%")

        # 5. 多 λ 配置对比（仅改进ACO）
        pareto_points = []
        for config_name, lam in lambda_configs.items():
            params = {**base_params, "lambdas": lam, "seed": 42}
            algo = ImprovedACO(customers, depot, dist_matrix, None, params)
            result = algo.solve()
            pareto_points.append({
                "name": config_name,
                "lambdas": lam,
                "f1": result.f1,
                "f2": result.f2,
                "f3": result.f3,
                "z": result.z,
                "vehicles_used": result.vehicles_used,
            })
            print(f"\nλ={lam} ({config_name}): Z={result.z:.4f} "
                  f"F1={result.f1:.1f} F2'={result.f2:.1f} F3={result.f3:.1f}")

        # 6. 保存结果为 JSON
        output = {
            "dataset": "Solomon C101",
            "customer_count": len(customers),
            "vehicle_capacity": Q,
            "lambdas": lambdas,
            "algorithms": results,
            "pareto_points": pareto_points,
        }

        output_path = os.path.join(os.path.dirname(__file__),
                                    "..", "frontend", "public", "benchmark.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {output_path}")

        # 打印汇总表
        print(f"\n{'='*70}")
        print(f"{'算法':<12} {'最优Z':<10} {'平均Z':<10} {'标准差':<10} "
              f"{'F1':<10} {'车辆':<6} {'耗时':<8}")
        print("-" * 70)
        for name, r in results.items():
            print(f"{name:<12} {r.get('best_z','-'):<10} "
                  f"{r.get('avg_z','-'):<10} {r.get('std_z','-'):<10} "
                  f"{r['best_f1']:<10} {r['vehicles_used']:<6} "
                  f"{r['avg_time']:<8}")


if __name__ == "__main__":
    run_benchmark()
