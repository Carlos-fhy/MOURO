# SQLite 建表 DDL 与 CRUD 操作
from app.extensions import get_db


# --- 建表 SQL ---
NODES_DDL = """
CREATE TABLE IF NOT EXISTS nodes (
    id          INTEGER PRIMARY KEY,
    type        TEXT NOT NULL CHECK(type IN ('depot', 'customer')),
    x_coord     REAL NOT NULL,
    y_coord     REAL NOT NULL,
    dataset_id  TEXT NOT NULL
);
"""

CUSTOMERS_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    id              INTEGER PRIMARY KEY,
    node_id         INTEGER NOT NULL REFERENCES nodes(id),
    demand_weight   REAL NOT NULL,
    service_time    REAL NOT NULL,
    early_time      REAL NOT NULL,
    late_time       REAL NOT NULL,
    emergency_level TEXT NOT NULL CHECK(emergency_level IN ('medical', 'fresh', 'normal')),
    emergency_weight REAL NOT NULL,
    dataset_id      TEXT NOT NULL
);
"""

SOLUTIONS_DDL = """
CREATE TABLE IF NOT EXISTS solutions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL UNIQUE,
    dataset_id      TEXT NOT NULL,
    algorithm       TEXT NOT NULL,
    lambdas         TEXT NOT NULL,
    vehicle_capacity REAL NOT NULL,
    total_cost      REAL,
    weighted_time   REAL,
    penalty_cost    REAL,
    z_value         REAL,
    vehicles_used   INTEGER,
    iterations      INTEGER,
    early_stopped   INTEGER DEFAULT 0,
    routes_json     TEXT,
    convergence_json TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def create_tables():
    """创建所有数据表"""
    db = get_db()
    db.execute(NODES_DDL)
    db.execute(CUSTOMERS_DDL)
    db.execute(SOLUTIONS_DDL)
    db.commit()


def delete_dataset(dataset_id):
    """删除所有节点和客户数据（单用户系统，每次只保留一个活跃数据集）"""
    db = get_db()
    db.execute("DELETE FROM customers")
    db.execute("DELETE FROM nodes")
    db.commit()


def insert_nodes(nodes, dataset_id):
    """
    批量插入节点数据

    参数:
        nodes: 节点列表，每个元素为 dict，包含 id, type, x_coord, y_coord
        dataset_id: 数据集标识
    """
    db = get_db()
    db.executemany(
        "INSERT INTO nodes (id, type, x_coord, y_coord, dataset_id) VALUES (?, ?, ?, ?, ?)",
        [(n["id"], n["type"], n["x_coord"], n["y_coord"], dataset_id) for n in nodes],
    )
    db.commit()


def insert_customers(customers, dataset_id):
    """
    批量插入客户数据

    参数:
        customers: 客户列表，每个元素为 dict，包含完整客户字段
        dataset_id: 数据集标识
    """
    db = get_db()
    db.executemany(
        """INSERT INTO customers
           (node_id, demand_weight, service_time, early_time, late_time,
            emergency_level, emergency_weight, dataset_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                c["node_id"], c["demand_weight"], c["service_time"],
                c["early_time"], c["late_time"],
                c["emergency_level"], c["emergency_weight"], dataset_id,
            )
            for c in customers
        ],
    )
    db.commit()
