# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**语言约束：所有回答、汇报、注释、提交信息一律使用中文。代码变量名/函数名/类名使用英文。**

## 项目上下文

MOURO（Multi-Objective Urban Route Optimization）是南京林业大学本科毕业设计项目，构建一个考虑应急程度与客户需求的城市配送多目标路径优化系统。

### 核心用户场景

1. 用户加载 Solomon 基准算例或首尔仿真数据 → 配置算法参数和决策偏好(λ) → 一键启动改进蚁群算法求解 → 在决策看板查看路线地图、KPI、收敛曲线
2. 用户选择多个算法（改进ACO/标准ACO/GA/SA）在同一数据集上对比运行 → 查看柱状图、收敛对比、性能指标表
3. 用户调整 λ 权重（省钱/抢时间/均衡/自定义）→ 观察 Pareto 近似前沿上不同方案的权衡关系

### 硬性约束

- 目标函数：`Z = λ₁F1* + λ₂F2'* + λ₃F3*`，λ₁+λ₂+λ₃=1，Min-Max 归一化
- F1 = 纯经济成本（固定+距离，含回程），F2' = 加权完工时间 Σ(ω_ei × t_arrive_i)，F3 = 时间窗惩罚 Σ P_i(t)
- 应急等级：medical(ω=2.0, 硬时间窗)、fresh(ω=1.5, 紧软时间窗)、normal(ω=1.0, 宽松软时间窗)
- 惩罚系数与应急等级挂钩：α_i = α_base × ω_ei，β_i = β_base × ω_ei
- 硬时间窗早到等待、迟到不可行(概率=0)；软时间窗早到立即服务+惩罚
- 单配送中心、同质车队、无限车辆数、容量约束 Q
- 车辆必须返回 depot；回程距离计入 F1，不计入 F2'
- 锚点校验准确率 >80%（vs OR-Tools 精确解）
- 前端 Vue 3 + Element Plus + ECharts + Leaflet/OSM；后端 Flask + SQLite；SSE 实时推送
- 本地部署，单管理员账号 JWT 认证

## 核心文档索引

| 文档 | 路径 | 查阅场景 |
|------|------|---------|
| 产品需求 | `docs/PRD.md` | 目标函数公式、约束条件、MVP 边界、数据方案 |
| 应用流程 | `docs/APP_FLOW.md` | 页面路由、用户流程、前后端交互时序、Pinia Store 设计 |
| 技术栈 | `docs/TECH_STACK.md` | 依赖包版本、架构图、浏览器兼容性 |
| 前端规范 | `docs/FRONTEND_GUIDELINES.md` | 组件设计、命名规范、Element Plus/ECharts/Leaflet 用法、SSE 封装 |
| 后端结构 | `docs/BACKEND_STRUCTURE.md` | 目录结构、蓝图划分、API 接口清单、SQLite 表结构、算法基类 |
| 实现计划 | `docs/IMPLEMENTATION_PLAN.md` | Phase 0~8 步骤编号、依赖关系、当前进度 |
| 进度追踪 | `progress.txt` | 当前所处 Phase、已完成步骤、下一步任务 |

## 每次会话的工作流程

### 1. 启动检查（每次会话必做）

```
读取 progress.txt → 确认当前 Phase 和步骤编号 → 读取对应文档章节
```

- 若 `progress.txt` 不存在，从 `docs/IMPLEMENTATION_PLAN.md` 确认起点并创建它
- 格式示例：
  ```
  当前阶段: Phase 2 - 算法核心
  已完成: P2-1, P2-2, P2-3
  进行中: P2-4 (Ant 类实现)
  阻塞项: 无
  下一步: P2-5
  备注: Ant 类的硬时间窗等待逻辑需要特别注意
  ```

### 2. 模式选择

| 条件 | 模式 | 说明 |
|------|------|------|
| 用户提问或需要澄清 | Ask | 直接回答，引用文档章节 |
| 任务超过 3 步 | Plan | 先列步骤清单，用户确认后再动手 |
| 明确的编码任务（≤3步） | Agent | 直接实施，完成后更新 progress.txt |
| 运行报错或行为异常 | Debug | 先读错误日志，定位根因，再修复 |

### 3. 实施规则

- 动手前必须引用相关文档段落，例如："根据 `BACKEND_STRUCTURE.md` 第6节算法基类定义..."
- 每完成一个步骤编号（如 P2-4），立即更新 `progress.txt`
- 跨 Phase 边界时，回顾上一 Phase 的产出是否完整

## 编码规范

### 命名约定

| 类别 | 规则 | 示例 |
|------|------|------|
| Python 模块 | snake_case.py | `solomon_parser.py`、`improved_aco.py` |
| Python 类 | PascalCase | `BaseAlgorithm`、`SolutionResult` |
| Python 函数/变量 | snake_case | `calculate_distance`、`best_z_value` |
| Vue 组件文件 | PascalCase.vue | `RouteMap.vue`、`KpiCard.vue` |
| Vue 页面文件 | PascalCase + View 后缀 | `SolveView.vue` |
| JS 文件 | camelCase.js | `request.js`、`auth.js` |
| Props | camelCase | `:routeData="data"` |
| Emits | kebab-case | `@solve-complete` |
| Pinia Store | use + 名称 + Store | `useAuthStore` |
| 常量 | UPPER_SNAKE_CASE | `MAX_ITERATIONS` |

### 代码风格

- Python 单个函数不超过 50 行；超过则拆分为私有辅助函数
- Vue 单个组件 `<script setup>` 不超过 150 行；超过则抽取 composable 或子组件
- 所有代码注释使用中文
- 每个 Python 模块顶部写一行中文模块说明注释
- 每个公开函数/方法写中文 docstring，说明参数和返回值
- 算法核心代码（`algorithm/` 目录）中关键公式步骤必须加注释标注对应的数学公式编号（参考 `PRD.md` 第3节）

### 错误处理

- 后端 API：所有接口统一返回 `{"success": bool, "data": ..., "message": "..."}` 格式
- 后端异常：用 Flask `errorhandler` 捕获，返回对应 HTTP 状态码 + JSON 错误信息
- 前端请求：axios 响应拦截器统一处理，401 跳转登录页，其余用 `ElMessage.error` 提示
- 算法运行异常：通过 SSE 推送 `{"type": "error", "message": "..."}` 通知前端
- 前端组件：所有异步操作必须配合 `v-loading` 指令显示加载状态

### 测试要求

| 场景 | 是否必须写测试 | 测试类型 |
|------|--------------|---------|
| 数据解析器（solomon_parser、seoul_parser） | 是 | 单元测试：验证节点数、坐标、T_max |
| 目标函数计算（F1/F2'/F3/Z） | 是 | 单元测试：用手算小算例验证 |
| 算法输出格式（每个算法的 solve 方法） | 是 | 单元测试：5 节点小算例验证 SolutionResult 字段完整 |
| API 接口 | 是 | 集成测试：Flask test client 走通完整流程 |
| 前端组件 | 否 | 本科毕设不要求前端测试 |
| 工具函数（distance.py、normalize.py） | 是 | 单元测试 |

## 禁止事项

1. **不要假设未文档化的内容** — 所有数学公式、业务规则、数据格式以六份文档为准。遇到文档未覆盖的情况，先问用户
2. **不要擅自升级依赖版本** — 版本锁定在 `TECH_STACK.md` 第2~3节，修改版本前必须获得用户确认
3. **不要省略错误处理和加载状态** — 每个 API 调用必须有 try/catch + loading 状态，参考上方错误处理规范
4. **不要在一个函数中处理多个职责** — 解析数据、计算目标函数、更新信息素是三件事，不要混在一起
5. **不要跳过 progress.txt 更新** — 每完成一个步骤编号必须更新，这是跨会话的唯一记忆
6. **不要修改已通过测试的算法核心逻辑** — 除非用户明确要求或测试失败，不要"优化"已工作的代码
7. **不要使用文档未列出的第三方库** — 前后端依赖清单是封闭的，新增依赖需用户批准
8. **不要硬编码业务参数** — 所有默认值从 `config.py` 的 `Config` 类读取（参考 `BACKEND_STRUCTURE.md` 第9节）
9. **不要在算法中使用随机种子以外的不确定性来源** — numpy random 必须支持 seed 参数以保证可复现
10. **不要生成英文回复** — 所有对话、注释、提交信息使用中文

## 子代理使用规则

### 何时拆分子代理

| 场景 | 是否拆分 | 原因 |
|------|---------|------|
| 探索代码库结构或搜索关键字 | 是（Explore 代理） | 避免主线程上下文被搜索结果污染 |
| 并行实现互不依赖的模块（如 P2-8/P2-9/P2-10 三个对照算法） | 是（多个 Agent 并行） | 加速开发，各算法无依赖 |
| 运行测试套件 | 是（Bash 代理） | 测试输出可能很长，隔离到子代理 |
| 单文件内的小修改（<50行） | 否 | 直接在主线程操作更高效 |
| 需要读取多份文档做决策 | 否 | 主线程需要完整上下文来做判断 |

### 子代理输入输出格式

- 启动子代理时，prompt 必须包含：任务目标、相关文件路径、预期输出格式
- 子代理完成后，主线程用中文简要总结结果，不要原样转发大段输出
- 示例 prompt：`"实现 backend/app/algorithm/genetic.py，遗传算法类继承 BaseAlgorithm（见 base.py），实现 solve 方法。参考 PRD.md 第3节目标函数定义。完成后运行 pytest tests/test_genetic.py -v 并报告结果。"`

### 保持主线程上下文干净

- 大段代码搜索结果、测试输出、文件列表等交给子代理处理
- 主线程只保留：用户指令 → 决策判断 → 文件读写 → progress.txt 更新
- 如果单次会话涉及超过 5 个文件的修改，优先用 Plan 模式列出清单再逐个实施

## 开发命令速查

```bash
# 后端
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
python run.py                                    # 启动 Flask（端口 5000）
python -m pytest tests/ -v                       # 运行全部测试
python -m pytest tests/test_aco.py -v            # 运行单个测试

# 前端
cd frontend
npm install
npm run dev                                      # 启动 Vite 开发服务器（端口 5173）
npm run build                                    # 生产构建
```
