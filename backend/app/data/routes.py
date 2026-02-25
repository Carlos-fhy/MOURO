# 数据管理蓝图 —— 数据集列表、加载、查询接口
import os
import traceback

import numpy as np
from flask import Blueprint, request, jsonify

from app.auth.routes import token_required
from app.data.solomon_parser import get_solomon_instances
from app.data.seoul_parser import get_seoul_instances
from app.data.loader import load_solomon_to_db, load_seoul_to_db

data_bp = Blueprint("data", __name__)

# 模块级缓存：最近一次加载的数据（供求解接口直接使用，避免重复解析）
_current_dataset = None


def get_current_dataset():
    """供其他模块获取当前已加载的数据集"""
    return _current_dataset


def _get_data_dir():
    """获取 backend/data 目录的绝对路径"""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data"
    )


def _serialize_node(node):
    """将节点 dict 序列化为 JSON 安全格式（去除 numpy 类型）"""
    return {k: (float(v) if isinstance(v, (np.floating, np.integer)) else v)
            for k, v in node.items()}


@data_bp.route("/solomon/list", methods=["GET"])
@token_required
def solomon_list():
    """获取可用的 Solomon 算例列表"""
    try:
        instances = get_solomon_instances(
            os.path.join(_get_data_dir(), "solomon"))
        return jsonify({"success": True,
                        "data": {"instances": instances},
                        "message": ""})
    except Exception as e:
        return jsonify({"success": False,
                        "data": None, "message": str(e)}), 500


@data_bp.route("/seoul/list", methods=["GET"])
@token_required
def seoul_list():
    """获取可用的首尔 ACVRP 实例列表"""
    try:
        instances = get_seoul_instances(
            os.path.join(_get_data_dir(), "seoul"))
        return jsonify({"success": True,
                        "data": {"instances": instances},
                        "message": ""})
    except Exception as e:
        return jsonify({"success": False,
                        "data": None,
                        "message": str(e)}), 500


def _find_seoul_instance_dir(instance_name):
    """在首尔数据目录中查找匹配的实例目录路径"""
    seoul_dir = os.path.join(_get_data_dir(), "seoul")
    benchmark_dir = os.path.join(seoul_dir, "ACVRP Benchmark Instances")
    if not os.path.isdir(benchmark_dir):
        raise FileNotFoundError("首尔数据目录不存在")
    for d in os.listdir(benchmark_dir):
        full = os.path.join(benchmark_dir, d)
        if instance_name.lower() in d.lower() and os.path.isdir(full):
            return full
    raise FileNotFoundError(f"首尔实例不存在: {instance_name}")


@data_bp.route("/load", methods=["POST"])
@token_required
def load_dataset():
    """加载并解析数据集，写入数据库并缓存到内存

    请求体: {"mode": "solomon"|"seoul", "instance": "c101", "emergency_ratio": {...}}
    """
    global _current_dataset

    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "").lower()
    instance = body.get("instance", "")
    emergency_ratio = body.get("emergency_ratio")

    if not mode or not instance:
        return jsonify({"success": False, "data": None,
                        "message": "缺少 mode 或 instance 参数"}), 400

    try:
        if mode == "solomon":
            filepath = os.path.join(
                _get_data_dir(), "solomon", f"{instance.lower()}.txt")
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Solomon 算例不存在: {instance}")
            result = load_solomon_to_db(filepath)

        elif mode == "seoul":
            instance_dir = _find_seoul_instance_dir(instance)
            result = load_seoul_to_db(
                instance_dir, emergency_ratio=emergency_ratio)
        else:
            return jsonify({"success": False, "data": None,
                            "message": f"不支持的模式: {mode}"}), 400

    except FileNotFoundError as e:
        return jsonify({"success": False, "data": None,
                        "message": str(e)}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "data": None,
                        "message": f"加载失败: {e}"}), 500

    _current_dataset = result
    dist = result["distance_matrix"]

    return jsonify({
        "success": True,
        "data": {
            "dataset_id": result["dataset_id"],
            "depot": _serialize_node(result["depot"]),
            "customer_count": len(result["customers"]),
            "matrix_summary": {
                "shape": list(dist.shape),
                "min": round(float(np.min(dist[dist > 0])), 2)
                       if np.any(dist > 0) else 0,
                "max": round(float(np.max(dist)), 2),
                "mean": round(float(np.mean(dist)), 2),
            },
        },
        "message": "数据加载成功",
    })


@data_bp.route("/customers", methods=["GET"])
@token_required
def get_customers():
    """获取当前已加载数据集的客户列表"""
    if _current_dataset is None:
        return jsonify({"success": False, "data": None,
                        "message": "尚未加载数据集"}), 400

    customers = _current_dataset["customers"]
    serialized = [_serialize_node(c) for c in customers]
    return jsonify({"success": True,
                    "data": {"customers": serialized},
                    "message": ""})


@data_bp.route("/depot", methods=["GET"])
@token_required
def get_depot():
    """获取当前已加载数据集的配送中心信息"""
    if _current_dataset is None:
        return jsonify({"success": False, "data": None,
                        "message": "尚未加载数据集"}), 400

    depot = _current_dataset["depot"]
    return jsonify({"success": True,
                    "data": {"depot": _serialize_node(depot)},
                    "message": ""})
