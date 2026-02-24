# 后端结构与数据模型

## 1. 项目结构

```
backend/
├── app/
│   ├── __init__.py              # Flask 应用工厂
│   ├── config.py                # 全局配置与算法默认参数
│   ├── extensions.py            # 数据库连接管理（原生 sqlite3）
│   ├── auth/
│   │   ├── __init__.py
│   │   └── routes.py            # 登录接口
│   ├── data/
│   │   ├── __init__.py
│   │   ├── routes.py            # 数据加载接口
│   │   ├── solomon_parser.py    # Solomon 算例解析器
│   │   ├── seoul_parser.py      # 首尔 ACVRP 数据解析器
│   │   └── field_generator.py   # 缺失字段生成器
│   ├── solve/
│   │   ├── __init__.py
│   │   ├── routes.py            # 求解接口 + SSE 推送
│   │   └── task_manager.py      # 算法任务线程管理
│   ├── compare/
│   │   ├── __init__.py
│   │   └── routes.py            # 算法对比接口
│   ├── algorithm/
│   │   ├── __init__.py
│   │   ├── base.py              # 算法基类（统一接口）
│   │   ├── improved_aco.py      # 改进蚁群算法
│   │   ├── standard_aco.py      # 标准蚁群算法
│   │   ├── genetic.py           # 遗传算法
│   │   ├── simulated_annealing.py  # 模拟退火
│   │   ├── local_search.py      # 2-opt 局部搜索
│   │   ├── greedy.py            # 贪心算法（信息素初始化用）
│   │   └── ortools_solver.py    # OR-Tools 精确求解（锚点校验）
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py          # SQLite ORM 模型
│   └── utils/
│       ├── __init__.py
│       ├── distance.py          # 距离矩阵计算
│       ├── normalize.py         # Min-Max 归一化工具
│       └── objective.py         # 目标函数计算（F1/F2'/F3/Z）
├── data/
│   ├── solomon/                 # Solomon 算例文件（文件名小写，UI 显示大写）
│   │   ├── c101.txt
│   │   ├── c201.txt
│   │   ├── r101.txt
│   │   ├── r201.txt
│   │   ├── rc101.txt
│   │   └── rc201.txt
│   └── seoul/                   # 首尔 ACVRP 数据文件
├── mouro.db                     # SQLite 数据库文件
├── requirements.txt
└── run.py                       # 启动入口
```

## 2. Flask 应用架构

**应用工厂（`app/__init__.py`）：**

```python
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    CORS(app)

    from app.auth.routes import auth_bp
    from app.data.routes import data_bp
    from app.solve.routes import solve_bp
    from app.compare.routes import compare_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(solve_bp, url_prefix='/api/solve')
    app.register_blueprint(compare_bp, url_prefix='/api/compare')

    return app
```

**蓝图划分：**

| 蓝图 | 前缀 | 职责 |
|------|------|------|
| `auth_bp` | `/api/auth` | 登录认证 |
| `data_bp` | `/api/data` | 数据加载与查询 |
| `solve_bp` | `/api/solve` | 求解启动与 SSE 推送 |
| `compare_bp` | `/api/compare` | 多算法对比 |

## 3. API 接口清单

**统一响应格式：** 所有接口返回 `{"success": bool, "data": {...}, "message": "..."}`。下表响应体列仅描述 `data` 字段内容。

### 3.1 认证接口

| 方法 | 路径 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| POST | `/api/auth/login` | `{username, password}` | `{token}` 或 `401` | 登录获取 JWT |

### 3.2 数据接口

| 方法 | 路径 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| GET | `/api/data/solomon/list` | — | `{instances: ["C101", ...]}` | 获取可用 Solomon 算例列表 |
| POST | `/api/data/load` | `{mode, instance, emergency_ratio?}` | `{depot, customers, matrix_summary}` | 加载并解析数据集 |
| GET | `/api/data/customers` | — | `{customers: [...]}` | 获取当前已加载的客户列表 |
| GET | `/api/data/depot` | — | `{depot: {...}}` | 获取配送中心信息 |

### 3.3 求解接口

| 方法 | 路径 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| POST | `/api/solve/start` | `{algorithm, lambdas, Q, params}` | `{task_id}` | 启动算法求解 |
| GET | `/api/solve/stream/<task_id>` | — | SSE 流 | 实时迭代进度推送 |
| GET | `/api/solve/result/<task_id>` | — | `{routes, kpi, convergence, ...}` | 获取求解结果 |

### 3.4 对比接口

| 方法 | 路径 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| POST | `/api/compare/start` | `{algorithms[], lambdas, Q, params, runs?}` | `{task_id}` | 启动多算法对比，runs 默认5次 |
| GET | `/api/compare/stream/<task_id>` | — | SSE 流 | 各算法进度推送 |
| GET | `/api/compare/result/<task_id>` | — | `{results: [...]}` | 获取对比结果 |

## 4. SSE 推送接口设计

**推送数据格式：**

```python
# 迭代进度消息
{
    "type": "progress",
    "iteration": 50,
    "best_z": 0.452,
    "best_f1": 4520.0,
    "best_f2": 312.5,
    "best_f3": 85.0,
    "vehicles_used": 4
}

# 算法完成消息（不含完整结果，前端收到后调用 GET /result/<task_id> 拉取）
{
    "type": "done",
    "task_id": "abc123",
    "total_iterations": 150,
    "early_stopped": true
}

# 错误消息
{
    "type": "error",
    "message": "算法运行异常"
}
```

**Flask SSE 实现模式：**

```python
from flask import Response, stream_with_context, request

@solve_bp.route('/stream/<task_id>')
def stream(task_id):
    # SSE 端点通过 query param 传递 token（EventSource 不支持自定义 Header）
    token = request.args.get('token')
    verify_token(token)  # 校验失败抛 401

    def generate():
        task = task_manager.get(task_id)
        for msg in task.iter_messages():
            yield f"data: {json.dumps(msg)}\n\n"
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream'
    )
```

## 5. 数据模型

### 5.1 SQLite 表结构

**dataset_id 命名规则：** Solomon 模式为 `"solomon_c101"`、`"solomon_r201"` 等（小写）；首尔模式为 `"seoul_<文件名>"` 如 `"seoul_n50"`。加载新数据集时，先删除同 dataset_id 的旧数据再写入。

**节点表 `nodes`：**

```sql
CREATE TABLE nodes (
    id          INTEGER PRIMARY KEY,
    type        TEXT NOT NULL CHECK(type IN ('depot', 'customer')),
    x_coord     REAL NOT NULL,
    y_coord     REAL NOT NULL,
    dataset_id  TEXT NOT NULL
);
```

**客户需求表 `customers`：**

```sql
CREATE TABLE customers (
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
```

**求解结果表 `solutions`：**

```sql
CREATE TABLE solutions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL UNIQUE,
    dataset_id      TEXT NOT NULL,
    algorithm       TEXT NOT NULL,
    lambdas         TEXT NOT NULL,       -- JSON: [0.33, 0.33, 0.34]
    vehicle_capacity REAL NOT NULL,
    total_cost      REAL,
    weighted_time   REAL,
    penalty_cost    REAL,
    z_value         REAL,
    vehicles_used   INTEGER,
    iterations      INTEGER,
    early_stopped   INTEGER DEFAULT 0,
    routes_json     TEXT,                -- JSON: 完整路线数据
    convergence_json TEXT,               -- JSON: 收敛曲线数据
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 6. 算法模块结构

### 6.1 算法基类

```python
class BaseAlgorithm:
    """所有算法的统一接口"""

    def __init__(self, customers, depot, distance_matrix, time_matrix, params):
        """
        distance_matrix: 距离矩阵（用于 F1 成本计算）
        time_matrix: 行驶时间矩阵（用于 F2' 和时间窗判断）
        Solomon 模式下 time_matrix = distance_matrix（速度=1）
        首尔模式下两者独立（非对称路网时间矩阵）
        """

    def solve(self, callback=None):
        """
        执行求解。
        callback: 每轮迭代回调函数，用于 SSE 推送
        返回: SolutionResult
        """
        raise NotImplementedError

class SolutionResult:
    routes: list          # [[0, 3, 7, 12, 0], [0, 1, 5, 0], ...]
    f1: float             # 总成本
    f2: float             # 加权时间
    f3: float             # 惩罚成本
    z: float              # 综合目标值
    vehicles_used: int
    convergence: list     # [(iteration, z_value), ...]
    schedule: list        # 调度明细，每个元素结构如下：
    # {
    #     "vehicle_id": int,       # 车辆编号（从1开始）
    #     "customer_id": int,      # 客户节点编号
    #     "arrival_time": float,   # 到达时刻
    #     "departure_time": float, # 离开时刻（arrival + wait + service）
    #     "demand": float,         # 卸货重量
    #     "penalty": float,        # 该客户的时间窗惩罚值
    #     "status": str            # "on_time" | "early" | "late"
    # }
```

### 6.2 类继承关系

```
BaseAlgorithm
├── ImprovedACO          # 改进蚁群（双信息素+双启发式+精英+2opt）
├── StandardACO          # 标准蚁群（单信息素+单启发式）
├── GeneticAlgorithm     # 遗传算法
└── SimulatedAnnealing   # 模拟退火

辅助类：
├── Ant                  # 蚂蚁类（构建单条解）
├── LocalSearch          # 2-opt 局部搜索
├── GreedySolver         # 贪心求解（信息素初始化）
└── ORToolsSolver        # 精确求解（锚点校验）
```

## 7. 数据处理流水线

```
Solomon 模式：
  读取 .txt 文件
  → 解析 Node 0 为 Depot（提取 T_max）
  → 解析 Node 1~N 为 Customer
  → 计算欧氏距离矩阵（对称）
  → 按时间窗宽度百分位映射应急等级
  → 写入 SQLite

首尔仿真模式：
  读取 ACVRP 数据文件
  → 解析坐标与非对称距离/时间矩阵
  → 按用户设定比例随机分配应急等级
  → 生成需求量（截断正态 N(50,20)）
  → 生成服务时间（5 + 0.1 × q_i）
  → 基于最短行驶时间反推时间窗
  → 写入 SQLite
```

## 8. 认证方案

```python
# config.py
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "mouro2026"
JWT_SECRET = "mouro-secret-key"
JWT_EXPIRATION = 86400  # 24小时
```

- 登录接口校验用户名密码，匹配则签发 JWT Token
- 其他接口通过装饰器 `@token_required` 校验 Authorization Header

## 9. 配置管理（`config.py`）

```python
class Config:
    # --- Flask ---
    SECRET_KEY = "mouro-secret-key"
    DATABASE_PATH = "mouro.db"          # 原生 sqlite3，不使用 SQLAlchemy

    # --- 认证 ---
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "mouro2026"
    JWT_EXPIRATION = 86400

    # --- 算法默认参数 ---
    DEFAULT_ACO_PARAMS = {
        "ant_count": None,       # None 表示与客户数相同
        "max_iterations": 200,
        "patience": 50,
        "early_stop_threshold": 1e-6,
        "alpha": 1.0,            # 成本信息素重要度
        "beta": 2.0,             # 成本启发式重要度
        "gamma": 1.0,            # 时间信息素重要度
        "delta": 2.0,            # 时间启发式重要度
        "rho_cost": 0.1,         # 成本信息素挥发系数
        "rho_time": 0.1,         # 时间信息素挥发系数
    }

    DEFAULT_GA_PARAMS = {
        "population_size": 100,      # 种群大小
        "max_iterations": 200,
        "patience": 50,
        "early_stop_threshold": 1e-6,
        "crossover_rate": 0.8,       # 交叉概率
        "mutation_rate": 0.1,        # 变异概率
    }

    DEFAULT_SA_PARAMS = {
        "initial_temperature": 1000, # 初始温度
        "cooling_rate": 0.995,       # 降温系数
        "min_temperature": 1e-3,     # 终止温度
        "max_iterations": 200,
        "patience": 50,
        "early_stop_threshold": 1e-6,
    }

    # --- 业务默认参数 ---
    DEFAULT_VEHICLE_CAPACITY = 1000  # kg
    DEFAULT_LAMBDAS = [0.33, 0.33, 0.34]
    ALPHA_BASE = 1.0                 # 基础早到惩罚系数
    BETA_BASE = 2.0                  # 基础迟到惩罚系数
    VEHICLE_FIXED_COST = 200         # 单车固定成本
    COST_PER_KM = 5.0                # 单位距离成本

    # --- 应急等级 ---
    EMERGENCY_WEIGHTS = {
        "medical": 2.0,
        "fresh": 1.5,
        "normal": 1.0,
    }
    DEFAULT_EMERGENCY_RATIO = {
        "medical": 10,
        "fresh": 20,
        "normal": 70,
    }
```
