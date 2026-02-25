# SQLite 数据库连接管理
import sqlite3

from flask import g, current_app


def get_db():
    """获取当前请求的数据库连接，使用 Row factory 支持字典式访问"""
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        # 共享缓存内存数据库需要 uri=True
        use_uri = db_path.startswith("file:")
        g.db = sqlite3.connect(db_path, uri=use_uri)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    """关闭当前请求的数据库连接"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """初始化数据库：注册关闭钩子，创建表结构"""
    app.teardown_appcontext(close_db)

    # 共享缓存内存数据库需要保持至少一个连接存活，否则数据会丢失
    db_path = app.config["DATABASE_PATH"]
    if db_path.startswith("file:") and "memory" in db_path:
        app._keep_alive_db = sqlite3.connect(db_path, uri=True)

    with app.app_context():
        from app.models.database import create_tables
        create_tables()
