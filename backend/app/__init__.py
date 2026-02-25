# Flask 应用工厂
import json

import numpy as np
from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS


class NumpyJSONProvider(DefaultJSONProvider):
    """扩展默认 JSON 序列化，支持 numpy 标量和数组"""

    @staticmethod
    def default(o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return DefaultJSONProvider.default(o)


def create_app(config_class=None):
    """
    创建并配置 Flask 应用实例

    参数:
        config_class: 配置类，默认使用 Config
    返回:
        Flask 应用实例
    """
    app = Flask(__name__)
    app.json_provider_class = NumpyJSONProvider
    app.json = NumpyJSONProvider(app)

    if config_class is None:
        app.config.from_object("app.config.Config")
    else:
        app.config.from_object(config_class)

    CORS(app)

    # 注册蓝图
    from app.auth.routes import auth_bp
    from app.data.routes import data_bp
    from app.solve.routes import solve_bp
    from app.compare.routes import compare_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(data_bp, url_prefix="/api/data")
    app.register_blueprint(solve_bp, url_prefix="/api/solve")
    app.register_blueprint(compare_bp, url_prefix="/api/compare")

    # 初始化数据库
    from app.extensions import init_db
    init_db(app)

    return app
