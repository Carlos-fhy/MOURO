# 求解蓝图 —— 算法启动、SSE 进度推送、结果查询
import json

from flask import Blueprint, request, jsonify, Response, stream_with_context

from app.auth.routes import token_required
from app.data.routes import get_current_dataset
from app.solve.task_manager import task_manager
from app.config import Config

solve_bp = Blueprint("solve", __name__)

# 算法名称 → 类的映射
ALGORITHM_MAP = {
    "improved_aco": "app.algorithm.improved_aco.ImprovedACO",
    "standard_aco": "app.algorithm.standard_aco.StandardACO",
    "genetic": "app.algorithm.genetic.GeneticAlgorithm",
    "simulated_annealing": "app.algorithm.simulated_annealing.SimulatedAnnealing",
    "ortools": "app.algorithm.ortools_solver.ORToolsSolver",
}


def _import_algorithm(name):
    """根据算法名称动态导入算法类"""
    path = ALGORITHM_MAP.get(name)
    if not path:
        raise ValueError(f"未知算法: {name}")
    module_path, class_name = path.rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def _build_params(body):
    """从请求体构建算法参数字典"""
    lambdas = body.get("lambdas", Config.DEFAULT_LAMBDAS)
    capacity = body.get("Q", Config.DEFAULT_VEHICLE_CAPACITY)
    user_params = body.get("params", {})

    params = {
        "vehicle_capacity": capacity,
        "lambdas": lambdas,
        "lambda1": lambdas[0],
        "lambda2": lambdas[1],
        "lambda3": lambdas[2],
        "max_runtime_sec": Config.DEFAULT_MAX_RUNTIME_SEC,
        "alpha_base": Config.ALPHA_BASE,
        "beta_base": Config.BETA_BASE,
        "fixed_cost": Config.VEHICLE_FIXED_COST,
        "cost_per_km": Config.COST_PER_KM,
    }
    params.update(user_params)
    return params


def _to_python(val):
    """将 numpy 标量转为 Python 原生类型，确保 JSON 可序列化"""
    if hasattr(val, "item"):
        return val.item()
    return val


def _serialize_result(result):
    """将 SolutionResult 序列化为 JSON 安全的 dict"""
    return {
        "routes": result.routes,
        "f1": _to_python(result.f1),
        "f2": _to_python(result.f2),
        "f3": _to_python(result.f3),
        "z": _to_python(result.z),
        "vehicles_used": _to_python(result.vehicles_used),
        "convergence": result.convergence,
        "schedule": result.schedule,
        "unreachable": result.unreachable,
    }


@solve_bp.route("/start", methods=["POST"])
@token_required
def start_solve():
    """启动算法求解任务

    请求体: {"algorithm": "improved_aco", "lambdas": [0.4,0.3,0.3], "Q": 1000, "params": {...}}
    响应: {"success": true, "data": {"task_id": "abc123"}}
    """
    dataset = get_current_dataset()
    if dataset is None:
        return jsonify({"success": False, "data": None,
                        "message": "请先加载数据集"}), 400

    body = request.get_json(silent=True) or {}
    algo_name = body.get("algorithm", "").lower()

    if algo_name not in ALGORITHM_MAP:
        return jsonify({"success": False, "data": None,
                        "message": f"未知算法: {algo_name}，"
                        f"可选: {list(ALGORITHM_MAP.keys())}"}), 400

    params = _build_params(body)

    try:
        AlgoClass = _import_algorithm(algo_name)
    except Exception as e:
        return jsonify({"success": False, "data": None,
                        "message": str(e)}), 500

    # 从缓存中取出数据
    customers = dataset["customers"]
    depot = dataset["depot"]
    dist_matrix = dataset["distance_matrix"]
    time_matrix = dataset.get("time_matrix", dist_matrix)

    def run_algo(callback):
        solver = AlgoClass(customers, depot, dist_matrix,
                           time_matrix, params)
        return solver.solve(callback=callback)

    task_id = task_manager.submit(run_algo)
    return jsonify({"success": True,
                    "data": {"task_id": task_id},
                    "message": "求解任务已启动"})


@solve_bp.route("/stream/<task_id>")
@token_required
def stream(task_id):
    """SSE 端点：实时推送算法迭代进度

    前端通过 EventSource 连接，token 通过 query param 传递
    """
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


@solve_bp.route("/result/<task_id>")
@token_required
def get_result(task_id):
    """获取求解结果

    响应: {"success": true, "data": {"routes": [...], "kpi": {...}, ...}}
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

    return jsonify({
        "success": True,
        "data": _serialize_result(result),
        "message": "",
    })
