import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.data.solomon_parser import parse_solomon_file, assign_emergency_levels
from app.utils.distance import euclidean_distance_matrix
from app.algorithm.improved_aco import ImprovedACO
from app.algorithm.standard_aco import StandardACO
from app.algorithm.genetic import GeneticAlgorithm
from app.algorithm.simulated_annealing import SimulatedAnnealing
from app.algorithm.alns import ALNSAlgorithm
from app.algorithm.ortools_solver import ORToolsSolver


ALGORITHMS = {
    "改进ACO": ImprovedACO,
    "标准ACO": StandardACO,
    "遗传算法": GeneticAlgorithm,
    "模拟退火": SimulatedAnnealing,
    "ALNS": ALNSAlgorithm,
}

DEFAULT_DATASETS = ["c101.txt", "c201.txt", "r101.txt", "r201.txt", "rc101.txt", "rc201.txt"]
DEFAULT_LAMBDAS = [0.33, 0.33, 0.34]
ANCHORS = [
    {"name": "纯成本", "lambdas": [1, 0, 0], "key": "f1"},
    {"name": "纯时效", "lambdas": [0, 1, 0], "key": "f2"},
    {"name": "纯服务", "lambdas": [0, 0, 1], "key": "f3"},
]


def _dataset_path(filename):
    base_dir = os.path.join(os.path.dirname(__file__), "data", "solomon")
    direct = os.path.join(base_dir, filename)
    nested = os.path.join(base_dir, "In", filename)
    if os.path.exists(direct):
        return direct
    return nested


def _base_params(capacity, iterations, patience, lambdas, seed):
    return {
        "lambdas": lambdas,
        "vehicle_capacity": capacity,
        "max_iterations": iterations,
        "patience": patience,
        "seed": seed,
        "alpha_base": 1.0,
        "beta_base": 2.0,
        "fixed_cost": 200,
        "cost_per_km": 5.0,
    }


def _load_solomon_file(filepath):
    parsed = parse_solomon_file(filepath)
    customers = assign_emergency_levels(parsed["customers"])
    depot = parsed["depot"]
    all_nodes = [depot] + customers
    dist_matrix = euclidean_distance_matrix(all_nodes)
    return {
        "depot": depot,
        "customers": customers,
        "distance_matrix": dist_matrix,
        "time_matrix": dist_matrix,
        "vehicle_capacity": parsed["vehicle_capacity"],
    }


def _run_algorithm_job(job):
    dataset_name, filepath, algo_name, run_idx, seed, iterations, patience, lambdas = job
    dataset = _load_solomon_file(filepath)
    customers = dataset["customers"]
    depot = dataset["depot"]
    dist_matrix = dataset["distance_matrix"]
    time_matrix = dataset.get("time_matrix", dist_matrix)
    capacity = dataset["vehicle_capacity"]
    params = _base_params(capacity, iterations, patience, lambdas, seed)

    solver = ALGORITHMS[algo_name](customers, depot, dist_matrix, time_matrix, params)
    started = time.time()
    result = solver.solve()
    elapsed = time.time() - started

    return {
        "dataset": dataset_name,
        "algorithm": algo_name,
        "run_idx": run_idx,
        "seed": seed,
        "f1": result.f1,
        "f2": result.f2,
        "f3": result.f3,
        "z": result.z,
        "vehicles_used": result.vehicles_used,
        "time": round(elapsed, 2),
        "convergence": result.convergence,
        "unreachable": result.unreachable,
    }


def _run_ortools_job(job):
    dataset_name, filepath, time_limit, lambdas = job
    dataset = _load_solomon_file(filepath)
    customers = dataset["customers"]
    depot = dataset["depot"]
    dist_matrix = dataset["distance_matrix"]
    time_matrix = dataset.get("time_matrix", dist_matrix)
    capacity = dataset["vehicle_capacity"]
    params = _base_params(capacity, 1, 1, lambdas, 42)

    solver = ORToolsSolver(customers, depot, dist_matrix, time_matrix, params)
    started = time.time()
    result = solver.solve(time_limit_sec=time_limit)
    elapsed = time.time() - started

    return {
        "dataset": dataset_name,
        "algorithm": "OR-Tools",
        "run_idx": 0,
        "seed": None,
        "f1": result.f1,
        "f2": result.f2,
        "f3": result.f3,
        "z": result.z,
        "vehicles_used": result.vehicles_used,
        "time": round(elapsed, 2),
        "convergence": result.convergence,
        "unreachable": result.unreachable,
    }


def _run_anchor_job(job):
    dataset_name, filepath, anchor_key, anchor_name, lambdas, run_idx, seed, iterations, patience = job
    dataset = _load_solomon_file(filepath)
    customers = dataset["customers"]
    depot = dataset["depot"]
    dist_matrix = dataset["distance_matrix"]
    time_matrix = dataset.get("time_matrix", dist_matrix)
    capacity = dataset["vehicle_capacity"]
    params = _base_params(capacity, iterations, patience, lambdas, seed)

    solver = ImprovedACO(customers, depot, dist_matrix, time_matrix, params)
    started = time.time()
    result = solver.solve()
    elapsed = time.time() - started

    return {
        "dataset": dataset_name,
        "algorithm": "改进ACO",
        "job_type": "anchor",
        "anchor_key": anchor_key,
        "anchor_name": anchor_name,
        "anchor_lambdas": lambdas,
        "run_idx": run_idx,
        "seed": seed,
        "f1": result.f1,
        "f2": result.f2,
        "f3": result.f3,
        "z": result.z,
        "vehicles_used": result.vehicles_used,
        "time": round(elapsed, 2),
    }


def _anchor_accuracy(aco_value, ortools_value):
    if ortools_value <= 0:
        return 0.0, 0.0
    if aco_value > ortools_value:
        gap = (aco_value - ortools_value) / ortools_value
        accuracy = max(1 - gap, 0) * 100
    else:
        gap = 0.0
        accuracy = 100.0
    return gap, accuracy


def _summarize_dataset(dataset_name, runs, anchor_runs=None):
    by_algo = {}
    for item in runs:
        by_algo.setdefault(item["algorithm"], []).append(item)

    algorithms = {}
    for algo_name, algo_runs in by_algo.items():
        if algo_name == "OR-Tools":
            item = algo_runs[0]
            algorithms[algo_name] = {
                "best_z": item["z"],
                "avg_z": None,
                "std_z": None,
                "best_f1": item["f1"],
                "best_f2": item["f2"],
                "best_f3": item["f3"],
                "vehicles_used": item["vehicles_used"],
                "avg_time": item["time"],
                "accuracy_vs_ortools": None,
                "convergence": item["convergence"],
                "runs": algo_runs,
            }
            continue

        z_values = np.array([r["z"] for r in algo_runs], dtype=float)
        best_idx = int(np.argmin(z_values))
        best = algo_runs[best_idx]
        algorithms[algo_name] = {
            "best_z": round(float(np.min(z_values)), 6),
            "avg_z": round(float(np.mean(z_values)), 6),
            "std_z": round(float(np.std(z_values)), 6),
            "best_f1": best["f1"],
            "best_f2": best["f2"],
            "best_f3": best["f3"],
            "vehicles_used": best["vehicles_used"],
            "avg_time": round(float(np.mean([r["time"] for r in algo_runs])), 2),
            "convergence": best["convergence"],
            "runs": algo_runs,
        }

    ortools = algorithms.get("OR-Tools")
    if ortools and ortools["best_f1"]:
        ortools_f1 = ortools["best_f1"]
        for algo_name, summary in algorithms.items():
            if algo_name == "OR-Tools":
                continue
            algo_f1 = summary["best_f1"]
            accuracy = min(ortools_f1 / algo_f1, algo_f1 / ortools_f1) * 100
            summary["accuracy_vs_ortools"] = round(
                min(accuracy, 100.0), 1
            )

    if ortools and anchor_runs and "改进ACO" in algorithms:
        anchor_details = {}
        anchor_accuracies = []
        for anchor in ANCHORS:
            key = anchor["key"]
            candidates = [r for r in anchor_runs if r.get("anchor_key") == key]
            if not candidates:
                continue
            best_anchor = min(candidates, key=lambda r: r[key])
            aco_value = best_anchor[key]
            ortools_value = ortools[f"best_{key}"]
            gap, accuracy = _anchor_accuracy(aco_value, ortools_value)
            anchor_details[key] = {
                "name": anchor["name"],
                "lambdas": anchor["lambdas"],
                "aco": round(aco_value, 2),
                "ortools": round(ortools_value, 2),
                "gap": round(gap * 100, 2),
                "accuracy": round(accuracy, 1),
                "runs": candidates,
            }
            anchor_accuracies.append(accuracy)
        if anchor_accuracies:
            algorithms["改进ACO"]["accuracy_vs_ortools"] = round(
                float(np.mean(anchor_accuracies)), 1
            )
            algorithms["改进ACO"]["anchor_accuracy"] = anchor_details

    return {
        "dataset": f"Solomon {dataset_name}",
        "lambdas": DEFAULT_LAMBDAS,
        "algorithms": algorithms,
    }


def main():
    parser = argparse.ArgumentParser(description="Parallel benchmark for MOURO algorithms")
    parser.add_argument("--datasets", default=",".join(DEFAULT_DATASETS),
                        help="Comma-separated dataset filenames, e.g. c101.txt,r101.txt")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--patience", type=int, default=80)
    parser.add_argument("--workers", type=int, default=min(32, os.cpu_count() or 1))
    parser.add_argument("--ortools-time", type=int, default=60)
    parser.add_argument("--no-ortools", action="store_true")
    parser.add_argument("--anchor-runs", type=int, default=3)
    parser.add_argument("--anchor-iterations", type=int, default=500)
    parser.add_argument("--anchor-patience", type=int, default=150)
    parser.add_argument("--no-anchors", action="store_true")
    parser.add_argument("--output", default=os.path.join(os.path.dirname(__file__), "benchmark_parallel.json"))
    args = parser.parse_args()

    dataset_files = [x.strip() for x in args.datasets.split(",") if x.strip()]
    jobs = []
    ortools_jobs = []
    anchor_jobs = []
    for filename in dataset_files:
        filepath = _dataset_path(filename)
        if not os.path.exists(filepath):
            print(f"Skip missing dataset: {filepath}", flush=True)
            continue
        dataset_name = os.path.splitext(os.path.basename(filename))[0].upper()
        for algo_name in ALGORITHMS:
            for run_idx in range(args.runs):
                jobs.append((
                    dataset_name, filepath, algo_name, run_idx + 1,
                    42 + run_idx, args.iterations, args.patience, DEFAULT_LAMBDAS,
                ))
        if not args.no_ortools:
            ortools_jobs.append((dataset_name, filepath, args.ortools_time, DEFAULT_LAMBDAS))
        if not args.no_anchors:
            for anchor in ANCHORS:
                for run_idx in range(args.anchor_runs):
                    anchor_jobs.append((
                        dataset_name, filepath,
                        anchor["key"], anchor["name"], anchor["lambdas"],
                        run_idx + 1, 42 + run_idx,
                        args.anchor_iterations, args.anchor_patience,
                    ))

    all_jobs = (
        [("algo", job) for job in jobs] +
        [("ortools", job) for job in ortools_jobs] +
        [("anchor", job) for job in anchor_jobs]
    )
    print(f"Jobs: {len(all_jobs)}  Workers: {args.workers}", flush=True)

    raw_results = []
    started = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        future_map = {}
        for kind, job in all_jobs:
            if kind == "algo":
                fn = _run_algorithm_job
            elif kind == "ortools":
                fn = _run_ortools_job
            else:
                fn = _run_anchor_job
            future_map[executor.submit(fn, job)] = (kind, job)

        done = 0
        for future in as_completed(future_map):
            done += 1
            kind, job = future_map[future]
            try:
                result = future.result()
            except Exception as exc:
                print(f"[{done}/{len(all_jobs)}] FAILED {kind} {job}: {exc}", flush=True)
                continue
            raw_results.append(result)
            if result.get("job_type") == "anchor":
                print(
                    f"[{done}/{len(all_jobs)}] {result['dataset']} anchor {result['anchor_key']} "
                    f"run={result['run_idx']} value={result[result['anchor_key']]:.2f} "
                    f"time={result['time']:.1f}s",
                    flush=True,
                )
                continue
            print(
                f"[{done}/{len(all_jobs)}] {result['dataset']} {result['algorithm']} "
                f"run={result['run_idx']} Z={result['z']:.6f} "
                f"F1={result['f1']:.2f} F2={result['f2']:.2f} F3={result['f3']:.2f} "
                f"time={result['time']:.1f}s",
                flush=True,
            )

    by_dataset = {}
    anchors_by_dataset = {}
    for item in raw_results:
        if item.get("job_type") == "anchor":
            anchors_by_dataset.setdefault(item["dataset"], []).append(item)
        else:
            by_dataset.setdefault(item["dataset"], []).append(item)

    results = [
        _summarize_dataset(name, runs, anchors_by_dataset.get(name, []))
        for name, runs in sorted(by_dataset.items())
    ]
    payload = {
        "elapsed_sec": round(time.time() - started, 2),
        "workers": args.workers,
        "runs": args.runs,
        "iterations": args.iterations,
        "patience": args.patience,
        "anchor_runs": args.anchor_runs,
        "anchor_iterations": args.anchor_iterations,
        "anchor_patience": args.anchor_patience,
        "results": results,
    }

    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    print(f"Saved: {args.output}", flush=True)
    print(f"Elapsed: {payload['elapsed_sec']}s", flush=True)


if __name__ == "__main__":
    main()
