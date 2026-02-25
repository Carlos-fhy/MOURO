# 认证蓝图 —— JWT 登录 + token_required 装饰器
import datetime
import functools

import jwt
from flask import Blueprint, request, jsonify, current_app

auth_bp = Blueprint("auth", __name__)


def token_required(f):
    """JWT 认证装饰器，校验 Authorization 头或 query param 中的 token"""

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 优先从 Header 获取
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # SSE 场景：从 query param 获取
        if not token:
            token = request.args.get("token")

        if not token:
            return jsonify({"success": False, "data": None,
                            "message": "缺少认证令牌"}), 401

        try:
            jwt.decode(token, current_app.config["SECRET_KEY"],
                       algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "data": None,
                            "message": "令牌已过期"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "data": None,
                            "message": "无效令牌"}), 401

        return f(*args, **kwargs)

    return decorated


@auth_bp.route("/login", methods=["POST"])
def login():
    """登录接口：验证用户名密码，返回 JWT

    请求体: {"username": "admin", "password": "..."}
    成功: {"success": true, "data": {"token": "..."}, "message": "登录成功"}
    失败: 401
    """
    body = request.get_json(silent=True) or {}
    username = body.get("username", "")
    password = body.get("password", "")

    if (username != current_app.config["ADMIN_USERNAME"] or
            password != current_app.config["ADMIN_PASSWORD"]):
        return jsonify({"success": False, "data": None,
                        "message": "用户名或密码错误"}), 401

    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(
            seconds=current_app.config["JWT_EXPIRATION"]
        ),
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"],
                       algorithm="HS256")

    return jsonify({"success": True,
                    "data": {"token": token},
                    "message": "登录成功"})
