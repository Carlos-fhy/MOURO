# 分步骤实现计划

## Phase 0: 项目初始化

| 步骤 | 任务 | 产出 |
|------|------|------|
| P0-1 | 创建项目根目录结构（backend/、frontend/、docs/） | 目录骨架 |
| P0-2 | 初始化 Python 虚拟环境，安装后端依赖，生成 requirements.txt | 后端环境就绪 |
| P0-3 | 使用 `npm create vue@latest` 初始化 Vue 3 项目，安装前端依赖 | 前端环境就绪 |
| P0-4 | 配置 Vite 开发代理（proxy `/api` → `localhost:5000`） | 前后端联调基础 |
| P0-5 | 创建 Flask 应用工厂 `app/__init__.py`，注册空蓝图，配置 CORS | Flask 可启动 |
| P0-6 | 创建 `config.py`，写入所有默认参数 | 全局配置就绪 |
| P0-7 | 初始化 SQLite 数据库，执行建表 SQL | 数据库就绪 |
| P0-8 | 下载 Solomon 算例文件（C101/C201/R101/R201/RC101/RC201）放入 `backend/data/solomon/` | 测试数据就绪 |
| P0-9 | 下载首尔 ACVRP 数据集放入 `backend/data/seoul/` | 仿真数据就绪 |

**依赖关系：** P0-1 → P0-2 ~ P0-9 可并行

## Phase 1: 数据层

| 步骤 | 任务 | 产出 |
|------|------|------|
| P1-1 | 编写 Solomon 解析器 `solomon_parser.py`：读取 .txt 文件，解析 depot（Node 0，提取 T_max）和 customer 节点 | Solomon 数据可读取 |
| P1-2 | 编写欧氏距离矩阵计算函数 `distance.py`：输入节点坐标列表，输出对称距离矩阵（numpy 二维数组） | 距离矩阵可生成 |
| P1-3 | 编写应急等级映射逻辑（Solomon 模式）：按时间窗宽度百分位分配 medical/fresh/normal | 应急等级自动标注 |
| P1-4 | 编写首尔数据解析器 `seoul_parser.py`：读取 ACVRP 数据文件，解析坐标与非对称距离/时间矩阵 | 首尔数据可读取 |
| P1-5 | 编写缺失字段生成器 `field_generator.py`：需求量（截断正态）、服务时间（线性）、应急等级（按比例随机）、时间窗（基于路网反推） | 仿真数据完整 |
| P1-6 | 编写数据入库逻辑：将解析后的数据写入 SQLite 的 nodes 和 customers 表 | 数据持久化 |
| P1-7 | 编写单元测试：验证 Solomon C101 解析结果（节点数=101，depot 坐标正确，T_max 正确） | 数据层质量保证 |

**依赖关系：** P1-1 → P1-2 → P1-3 → P1-6 → P1-7；P1-4 → P1-5 → P1-6

## Phase 2: 算法核心

| 步骤 | 任务 | 产出 |
|------|------|------|
| P2-1 | 实现算法基类 `base.py`：定义 `BaseAlgorithm` 接口（`__init__`、`solve`）和 `SolutionResult` 数据类 | 统一算法接口 |
| P2-2 | 实现目标函数计算模块：F1（固定成本+距离成本）、F2'（加权完成时间）、F3（时间窗惩罚），Min-Max 归一化，Z = λ₁F1* + λ₂F2'* + λ₃F3* | 目标函数可计算 |
| P2-3 | 实现贪心求解器 `greedy.py`：最近邻构造初始解，计算 F1_nn 和 F2'_nn 用于信息素初始化 | 信息素初始值就绪 |
| P2-4 | 实现不可达客户预检模块：算法启动前检测硬时间窗客户可达性（t_min_arrive > LT_i 则剔除），返回 unreachable 列表 | 预检功能可用 |
| P2-5 | 实现 `Ant` 类：单只蚂蚁构建完整解（双信息素+双启发式状态转移概率、容量约束、时间窗可行性检查、硬时间窗等待逻辑） | 蚂蚁可构建路线 |
| P2-6 | 实现改进蚁群算法 `improved_aco.py`：蚂蚁群迭代、精英蚂蚁全局信息素更新（独立 ρ_cost/ρ_time 挥发）、早停机制（patience + threshold） | 改进 ACO 可运行 |
| P2-7 | 实现 2-opt 局部搜索 `local_search.py`：路线内节点交换优化 | 解质量提升 |
| P2-8 | 将 2-opt 集成到改进 ACO 的每轮迭代最优解中 | ACO + 2-opt 完整 |
| P2-9 | 实现标准蚁群算法 `standard_aco.py`：单信息素 + 单启发式，作为对照组 | 对照算法 1 |
| P2-10 | 实现遗传算法 `genetic.py`：染色体编码（客户排列）、顺序交叉、变异、轮盘赌选择 | 对照算法 2 |
| P2-11 | 实现模拟退火 `simulated_annealing.py`：初始解（贪心）、邻域操作（swap/insert/reverse）、降温策略 | 对照算法 3 |
| P2-12 | 实现 OR-Tools 精确求解器 `ortools_solver.py`：调用 CP-SAT 或 Routing 求解小规模实例 | 锚点校验基准 |
| P2-13 | 编写算法单元测试：用 5 节点小算例验证各算法输出格式正确、Z 值合理 | 算法层质量保证 |

**依赖关系：** P2-1 → P2-2 → P2-3 → P2-4 → P2-5 → P2-6 → P2-7 → P2-8；P2-9/P2-10/P2-11 依赖 P2-1 和 P2-2 可并行；P2-12 独立；P2-13 在所有算法完成后

## Phase 3: 后端 API

| 步骤 | 任务 | 产出 |
|------|------|------|
| P3-1 | 实现认证蓝图 `auth/routes.py`：POST `/api/auth/login` 校验固定账号密码，签发 JWT Token；编写 `@token_required` 装饰器 | 登录接口可用 |
| P3-2 | 实现数据蓝图 `data/routes.py`：GET `/api/data/solomon/list` 返回可用算例列表；POST `/api/data/load` 调用解析器加载数据 | 数据接口可用 |
| P3-3 | 实现 GET `/api/data/customers` 和 GET `/api/data/depot` 接口：返回当前已加载的客户列表和配送中心信息 | 数据查询接口可用 |
| P3-4 | 实现任务管理器 `solve/task_manager.py`：线程池管理算法任务，消息队列（`queue.Queue`）缓存迭代消息 | 异步任务基础设施 |
| P3-5 | 实现求解蓝图 `solve/routes.py`：POST `/api/solve/start` 启动算法线程，返回 task_id | 求解启动接口可用 |
| P3-6 | 实现 SSE 推送 GET `/api/solve/stream/<task_id>`：Flask `stream_with_context` + `Response(mimetype='text/event-stream')` | 实时进度推送可用 |
| P3-7 | 实现 GET `/api/solve/result/<task_id>`：返回完整求解结果（路线、KPI、收敛数据） | 结果查询接口可用 |
| P3-8 | 实现对比蓝图 `compare/routes.py`：POST `/api/compare/start` 依次运行多算法；GET `/api/compare/stream/<task_id>` 推送各算法进度 | 对比接口可用 |
| P3-9 | 编写 API 集成测试：用 Flask test client 测试登录→加载数据→启动求解完整流程 | API 层质量保证 |

**依赖关系：** P3-1 → P3-2 → P3-3；P3-4 → P3-5 → P3-6 → P3-7；P3-8 依赖 P3-4~P3-7；P3-9 在所有接口完成后

## Phase 4: 前端骨架

| 步骤 | 任务 | 产出 |
|------|------|------|
| P4-1 | 配置 Vue Router：定义路由表（/login、/dashboard、/data、/solve、/result、/compare），添加导航守卫（未登录重定向 /login） | 路由可用 |
| P4-2 | 实现 `AppLayout.vue`：`el-container` + `el-aside` + `el-main` 布局，登录页独立布局 | 整体布局就绪 |
| P4-3 | 实现 `AppSidebar.vue`：`el-menu` router 模式，菜单项对应各页面路由 | 侧边栏导航可用 |
| P4-4 | 实现 `AppHeader.vue`：系统名称、当前用户、退出按钮 | 顶栏可用 |
| P4-5 | 实现 `LoginView.vue`：居中卡片表单，调用登录接口，成功后存 token 跳转 /dashboard | 登录页可用 |
| P4-6 | 编写 `api/request.js`：axios 实例，请求拦截器附加 JWT，响应拦截器处理 401 | HTTP 请求基础设施 |
| P4-7 | 编写 `stores/auth.js`：Pinia store 管理 token 和登录状态，localStorage 持久化 | 认证状态管理就绪 |
| P4-8 | 实现 `DashboardView.vue`：项目简介卡片 + 三个快速入口按钮 | 首页可用 |

**依赖关系：** P4-1 → P4-2 → P4-3 + P4-4 可并行；P4-6 → P4-7 → P4-5；P4-8 独立

## Phase 5: 前端业务页面

| 步骤 | 任务 | 产出 |
|------|------|------|
| P5-1 | 编写 `stores/data.js`：管理当前数据集模式、节点列表、客户列表、距离矩阵元信息 | 数据状态管理就绪 |
| P5-2 | 实现 `DataManageView.vue`：数据源 Radio 切换（Solomon/首尔）、Solomon 下拉框、应急等级比例输入（仿真模式）、加载按钮 | 数据管理页可用 |
| P5-3 | 实现 `RouteMap.vue`（数据预览模式）：Leaflet 地图渲染客户点分布，depot 特殊图标，按应急等级着色 | 地图预览可用 |
| P5-4 | 在 DataManageView 中集成数据预览表格（`el-table`）和 RouteMap 地图 | 数据管理页完整 |
| P5-5 | 编写 `stores/solve.js`：管理算法选择、λ 配置、Q 值、ACO 参数、task_id、求解状态 | 求解状态管理就绪 |
| P5-6 | 实现 `LambdaSlider.vue`：三个联动滑块（λ₁+λ₂+λ₃=1），三个预设按钮（省钱/抢时间/均衡） | λ 配置组件可用 |
| P5-7 | 实现 `SolveView.vue`：算法 Radio 选择、LambdaSlider、车辆载重输入、高级参数折叠面板、启动按钮 | 求解配置页可用 |
| P5-8 | 编写 `utils/sse.js`：EventSource 封装（onMessage/onDone/onError 回调） | SSE 客户端就绪 |
| P5-9 | 实现 `SseLogBox.vue`：黑底绿字终端风格日志框，自动滚动，接收 SSE 迭代消息 | 日志组件可用 |
| P5-10 | 在 SolveView 中集成 SSE 日志框，求解完成后自动跳转 /result | 求解页完整 |

**依赖关系：** P5-1 → P5-2 → P5-3 → P5-4；P5-5 → P5-6 → P5-7；P5-8 → P5-9 → P5-10

## Phase 6: 决策看板与算法对比

| 步骤 | 任务 | 产出 |
|------|------|------|
| P6-1 | 编写 `stores/result.js`：管理求解结果（路线、KPI、收敛数据、Pareto 数据、调度明细） | 结果状态管理就绪 |
| P6-2 | 实现 `KpiCard.vue`：单个 KPI 数据卡片（图标 + 数值 + 标签），支持 props 传入 | KPI 卡片组件可用 |
| P6-3 | 实现 `ConvergenceChart.vue`：ECharts 折线图，X 轴=迭代次数，Y 轴=Z 值，smooth 平滑 | 收敛曲线组件可用 |
| P6-4 | 实现 `RouteMap.vue`（路线展示模式）：在地图上按车辆编号分色绘制路线，悬浮弹出客户详情 popup | 路线地图可用 |
| P6-5 | 实现 `ParetoChart.vue`：ECharts 散点图，X 轴=F1，Y 轴=F2'，当前方案红点高亮 | Pareto 图可用 |
| P6-6 | 实现 `ScheduleTable.vue`：`el-table` 按车辆分组展示调度明细（车辆号/客户顺序/到达时刻/卸货重量/惩罚） | 调度表可用 |
| P6-7 | 实现 `ResultView.vue`：组装 KPI 卡片×4 + RouteMap + ConvergenceChart + ParetoChart + ScheduleTable | 决策看板页完整 |
| P6-8 | 实现 `CompareView.vue`：算法多选 Checkbox、统一 λ 配置、运行按钮、SSE 日志 | 对比页基础可用 |
| P6-9 | 在 CompareView 中实现对比柱状图（ECharts 分组柱状图：F1/F2'/F3/Z）和收敛对比图（多折线叠加） | 对比图表可用 |
| P6-10 | 在 CompareView 中实现性能指标表（最优 Z/平均 Z/标准差/运行时间/车辆数） | 对比页完整 |

**依赖关系：** P6-1 → P6-2~P6-6 可并行 → P6-7；P6-8 → P6-9 → P6-10

## Phase 7: 集成联调与验证

| 步骤 | 任务 | 产出 |
|------|------|------|
| P7-1 | 前后端联调：登录流程（前端表单 → JWT → localStorage → 路由守卫） | 登录流程跑通 |
| P7-2 | 前后端联调：数据加载流程（选择算例 → POST /api/data/load → 地图+表格渲染） | 数据流程跑通 |
| P7-3 | 前后端联调：求解流程（配置参数 → POST /api/solve/start → SSE 日志滚动 → 跳转看板） | 求解流程跑通 |
| P7-4 | 前后端联调：对比流程（多选算法 → POST /api/compare/start → SSE → 对比图表渲染） | 对比流程跑通 |
| P7-5 | 用 OR-Tools 对 Solomon C101 小规模子集（20 节点）求精确解，记录 F1/F2'/F3 基准值 | 精确解基准就绪 |
| P7-6 | 锚点校验：分别以 λ=[1,0,0]、[0,1,0]、[0,0,1] 运行改进 ACO，与 OR-Tools 结果对比，验证准确率 >80% | 锚点校验通过 |
| P7-7 | 跑通 6 个 Solomon 算例（C101/C201/R101/R201/RC101/RC201），记录各算法 KPI | Solomon 实验数据就绪 |
| P7-8 | 跑通首尔仿真数据集，验证非对称距离矩阵和生成字段的正确性 | 首尔实验数据就绪 |
| P7-9 | 多组 λ 实验：运行 21 组均匀采样 λ 组合（步长 0.2），收集 Pareto 近似前沿数据 | Pareto 实验数据就绪 |

**依赖关系：** P7-1 → P7-2 → P7-3 → P7-4（串行联调）；P7-5 → P7-6；P7-7/P7-8/P7-9 在联调完成后可并行

## Phase 8: 收尾与打磨

| 步骤 | 任务 | 产出 |
|------|------|------|
| P8-1 | 实现 Excel 导出功能（Nice-to-have）：后端 openpyxl 生成调度明细表，前端下载按钮 | 导出功能可用 |
| P8-2 | 实现历史记录页 `HistoryView.vue`（Nice-to-have）：从 solutions 表读取历史方案列表，支持查看详情和删除 | 历史记录页可用 |
| P8-3 | UI 打磨：统一间距与字号、Loading 状态完善、空状态提示、响应式适配 | 界面体验提升 |
| P8-4 | 异常处理完善：后端接口统一错误响应格式、前端全局错误提示、SSE 断连提示 | 系统健壮性提升 |
| P8-5 | 端到端冒烟测试：完整走通登录→加载 C101→改进 ACO 求解→查看看板→对比 4 算法全流程 | 系统可演示 |
| P8-6 | 编写部署说明：本地启动步骤（后端 `python run.py` + 前端 `npm run dev`），环境要求 | 部署文档就绪 |

**依赖关系：** P8-1/P8-2 可并行（Nice-to-have，可跳过）；P8-3/P8-4 可并行；P8-5 在所有功能完成后；P8-6 最后

---

## Phase 依赖总览

```
Phase 0（项目初始化）
  → Phase 1（数据层）
    → Phase 2（算法核心）
      → Phase 3（后端 API）
  → Phase 4（前端骨架）← 可与 Phase 1~3 并行
    → Phase 5（前端业务页面）
      → Phase 6（决策看板与算法对比）
        → Phase 7（集成联调与验证）← 需要前后端均就绪
          → Phase 8（收尾与打磨）
```
