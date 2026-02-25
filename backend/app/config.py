# 全局配置与算法默认参数
import os


class Config:
    """应用全局配置类，所有业务参数从此处读取"""

    # --- Flask ---
    SECRET_KEY = "mouro-secret-key"
    DATABASE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mouro.db"
    )

    # --- 认证 ---
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "mouro2026"
    JWT_EXPIRATION = 86400  # 24小时

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
        "population_size": 100,
        "max_iterations": 200,
        "patience": 50,
        "early_stop_threshold": 1e-6,
        "crossover_rate": 0.8,
        "mutation_rate": 0.1,
    }

    DEFAULT_SA_PARAMS = {
        "initial_temperature": 1000,
        "cooling_rate": 0.995,
        "min_temperature": 1e-3,
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


class TestConfig(Config):
    """测试环境配置，使用共享缓存内存数据库"""

    DATABASE_PATH = "file::memory:?cache=shared"
    TESTING = True
