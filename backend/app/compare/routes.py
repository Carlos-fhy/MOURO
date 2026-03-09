# 算法对比蓝图 —— 多算法并行对比求解
import json

from flask import Blueprint, request, jsonify, Response, stream_with_context

from app.auth.routes import token_required
from app.data.routes import get_current_dataset
from app.solve.task_manager import task_manager
from app.solve.routes import _import_algorithm, _build_params, _serialize_result
from app.config import Config

compare_bp = Blueprint("compare", __name__)


@compare_bp.route("/start", methods=["POST"])
@token_required
def start_compare():
    """启动多算法对比任务

    请求体: {"algorithms": ["improved_aco","standard_aco"],
             "lambdas": [0.4,0.3,0.3], "Q": 1000, "params": {}, "runs": 1}
    """
    dataset = get_current_dataset()
    if dataset is None:
        return jsonify({"success": False, "data": None,
                        "message": "请先加载数据集"}), 400

    body = request.get_json(silent=True) or {}
    algo_names = body.get("algorithms", [])
    runs = body.get("runs", 1)

    if not algo_names or not isinstance(algo_names, list):
        return jsonify({"success": False, "data": None,
                        "message": "缺少 algorithms 参数"}), 400

    params = _build_params(body)
    customers = dataset["customers"]
    depot = dataset["depot"]
    dist_matrix = dataset["distance_matrix"]
    time_matrix = dataset.get("time_matrix", dist_matrix)

    def run_compare(callback):
        results = {}
        for algo_name in algo_names:
            AlgoClass = _import_algorithm(algo_name.lower())
            algo_results = []
            for run_idx in range(runs):
                run_params = dict(params)
                if runs > 1:
                    run_params["seed"] = 42 + run_idx
                solver = AlgoClass(customers, depot,
                                   dist_matrix, time_matrix, run_params)
                result = solver.solve(callback=lambda msg, a=algo_name:
                    callback({**msg, "algorithm": a}))
                algo_results.append(result)
            results[algo_name] = algo_results
        return results

    task_id = task_manager.submit(run_compare)
    return jsonify({"success": True,
                    "data": {"task_id": task_id},
                    "message": "对比任务已启动"})


@compare_bp.route("/stream/<task_id>")
@token_required
def stream(task_id):
    """SSE 端点：推送多算法对比进度"""
    info = task_manager.get(task_id)
    if info is None:
        return jsonify({"success": False, "data": None,
                        "message": "任务不存在"}), 404

    def generate():
        for msg in task_manager.iter_messages(task_id):
            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'task_id': task_id})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache",
                 "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )


@compare_bp.route("/result/<task_id>")
@token_required
def get_result(task_id):
    """获取对比结果

    响应: {"success": true, "data": {"results": {"algo_name": [...]}}}
    """
    result, error = task_manager.get_result(task_id)

    if error == "任务不存在":
        return jsonify({"success": False, "data": None,
                        "message": error}), 404
    if error == "任务尚未完成":
        return jsonify({"success": False, "data": None,
                        "message": error}), 202
    if error:
        return jsonify({"success": False, "data": None,
                        "message": error}), 500

    # result 是 {algo_name: [SolutionResult, ...]} 字典
    serialized = {}
    for algo_name, runs in result.items():
        serialized[algo_name] = [_serialize_result(r) for r in runs]

    return jsonify({
        "success": True,
        "data": {"results": serialized},
        "message": "",
    })
