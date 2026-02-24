# 前端设计系统

## 1. 项目结构

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API 请求封装
│   │   ├── auth.js             # 登录接口
│   │   ├── data.js             # 数据加载接口
│   │   ├── solve.js            # 求解接口 + SSE
│   │   ├── compare.js          # 算法对比接口
│   │   └── request.js          # axios 实例与拦截器
│   ├── assets/                 # 静态资源（图片、字体）
│   ├── components/             # 通用组件
│   │   ├── layout/
│   │   │   ├── AppSidebar.vue  # 侧边栏导航
│   │   │   ├── AppHeader.vue   # 顶栏
│   │   │   └── AppLayout.vue   # 整体布局容器
│   │   ├── map/
│   │   │   └── RouteMap.vue    # Leaflet 路线地图
│   │   ├── charts/
│   │   │   ├── ConvergenceChart.vue  # 收敛曲线
│   │   │   └── ParetoChart.vue       # Pareto 散点图
│   │   └── common/
│   │       ├── KpiCard.vue     # KPI 数据卡片
│   │       ├── SseLogBox.vue   # SSE 日志终端框
│   │       ├── ParamPanel.vue  # 高级算法参数折叠面板
│   │       ├── LambdaSlider.vue # 三联动λ滑块
│   │       └── ScheduleTable.vue # 按车辆分组调度明细表
│   ├── views/                  # 页面级组件
│   │   ├── LoginView.vue
│   │   ├── DashboardView.vue
│   │   ├── DataManageView.vue
│   │   ├── SolveView.vue
│   │   ├── ResultView.vue
│   │   ├── CompareView.vue
│   │   └── HistoryView.vue
│   ├── stores/                 # Pinia 状态管理
│   │   ├── auth.js
│   │   ├── data.js
│   │   ├── solve.js
│   │   └── result.js
│   ├── router/
│   │   └── index.js            # 路由配置 + 导航守卫
│   ├── utils/
│   │   └── sse.js              # EventSource 封装
│   ├── App.vue
│   └── main.js
├── index.html
├── vite.config.js
└── package.json
```

## 2. 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| 组件文件 | PascalCase.vue | `RouteMap.vue`、`KpiCard.vue` |
| 页面文件 | PascalCase + View 后缀 | `SolveView.vue` |
| JS/TS 文件 | camelCase.js | `request.js`、`auth.js` |
| 组件标签 | PascalCase | `<RouteMap />` |
| Props | camelCase | `:routeData="data"` |
| Emits | kebab-case | `@solve-complete` |
| Pinia Store | use + 名称 + Store | `useAuthStore` |
| CSS 类名 | BEM 风格（可选） | `.kpi-card__value` |
| 常量 | UPPER_SNAKE_CASE | `MAX_ITERATIONS` |
| 代码变量/函数 | 英文 camelCase | `customerList`、`loadData()` |
| 界面文字/标签 | 中文 | `"启动智能排线"` |
| 代码注释 | 中文 | `// 计算欧氏距离` |

## 3. 组件设计规范

### 3.1 布局组件

```
AppLayout.vue
├── AppHeader.vue      （顶栏：系统名称 + 用户信息 + 退出按钮）
├── AppSidebar.vue     （侧边栏：el-menu + vue-router 联动）
└── <router-view />    （内容区：页面组件渲染）
```

- 侧边栏使用 `el-menu` 的 `router` 模式，`default-active` 绑定当前路由路径
- 布局采用 `el-container` + `el-aside` + `el-main`
- 登录页不显示侧边栏，使用独立布局

### 3.2 业务组件划分

| 组件 | 所属页面 | 职责 |
|------|---------|------|
| `RouteMap.vue` | ResultView、DataManageView | Leaflet 地图渲染路线/客户点 |
| `ConvergenceChart.vue` | ResultView、CompareView | Z 值收敛折线图 |
| `ParetoChart.vue` | ResultView | 多组 λ 结果散点图 |
| `KpiCard.vue` | ResultView | 单个 KPI 数据卡片（图标+数值+标签） |
| `SseLogBox.vue` | SolveView、CompareView | 终端风格日志滚动框 |
| `ParamPanel.vue` | SolveView | 高级算法参数折叠面板 |
| `LambdaSlider.vue` | SolveView | 三个联动滑块（总和=1） |
| `ScheduleTable.vue` | ResultView | 按车辆分组的调度明细表 |

## 4. Element Plus 使用规范

**主题色：**

| 用途 | 色值 | 说明 |
|------|------|------|
| 主色 | `#409EFF` | Element Plus 默认蓝，按钮/链接/高亮 |
| 成功 | `#67C23A` | 准时送达、算法完成 |
| 警告 | `#E6A23C` | 软时间窗违约 |
| 危险 | `#F56C6C` | 硬时间窗不可达、错误 |
| 信息 | `#909399` | 辅助文字 |

**常用组件约定：**

- 表单：统一使用 `el-form` + `el-form-item`，label 宽度 120px
- 表格：统一使用 `el-table`，开启 `stripe` 斑马纹，`border` 边框
- 按钮：主操作用 `type="primary"`，危险操作用 `type="danger"`
- 消息提示：成功用 `ElMessage.success`，错误用 `ElMessage.error`
- 加载状态：使用 `v-loading` 指令

## 5. ECharts 图表规范

**收敛曲线（ConvergenceChart）：**

```javascript
{
  xAxis: { type: 'category', name: '迭代次数' },
  yAxis: { type: 'value', name: '目标函数 Z' },
  series: [{ type: 'line', smooth: true }],
  tooltip: { trigger: 'axis' }
}
```

**Pareto 散点图（ParetoChart）：**

```javascript
{
  xAxis: { type: 'value', name: '总成本 F1' },
  yAxis: { type: 'value', name: '加权时间 F2\'' },
  series: [{
    type: 'scatter',
    symbolSize: 10,
    // 当前选中方案用红色大点标注
  }],
  tooltip: { trigger: 'item' }
}
```

**对比柱状图（CompareView）：**

```javascript
{
  xAxis: { type: 'category', data: ['改进ACO', '标准ACO', 'GA', 'SA'] },
  yAxis: { type: 'value' },
  series: [
    { name: 'F1', type: 'bar' },
    { name: 'F2\'', type: 'bar' },
    { name: 'F3', type: 'bar' },
    { name: 'Z', type: 'bar' }
  ]
}
```

## 6. Leaflet 地图规范

**底图：**

```javascript
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
})
```

**标记样式：**

| 节点类型 | 图标/样式 | 颜色 |
|---------|----------|------|
| 配送中心（Depot） | 方形图标或自定义 icon | 黑色 |
| 医疗客户 | 圆形 CircleMarker，半径 8 | 红色 `#F56C6C` |
| 生鲜客户 | 圆形 CircleMarker，半径 6 | 橙色 `#E6A23C` |
| 普通客户 | 圆形 CircleMarker，半径 5 | 蓝色 `#409EFF` |

**路线颜色方案（按车辆编号循环）：**

```javascript
const ROUTE_COLORS = [
  '#409EFF', '#67C23A', '#E6A23C', '#F56C6C',
  '#909399', '#B37FEB', '#36CFC9', '#FF85C0'
]
```

**交互：** 鼠标悬浮客户点弹出 `L.popup`，内容包含客户编号、应急等级、预计到达时间、时间窗状态。

## 7. SSE 通信规范

**封装模式（`utils/sse.js`）：**

```javascript
export function createSseConnection(url, { onMessage, onDone, onError }) {
  const token = localStorage.getItem('token')
  const eventSource = new EventSource(`${url}?token=${token}`)

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'done') {
      onDone(data)
      eventSource.close()
    } else if (data.type === 'error') {
      onError(data.message)
      eventSource.close()
    } else {
      onMessage(data)
    }
  }

  eventSource.onerror = (err) => {
    onError(err)
    eventSource.close()
  }

  return eventSource // 返回实例，供手动关闭
}
```

**重连策略：** 不做自动重连。算法运行是一次性任务，SSE 断开即视为异常，提示用户重新运行。

## 8. 状态管理方案（Pinia）

| Store | 关键 State | 说明 |
|-------|-----------|------|
| `useAuthStore` | `token`, `isLoggedIn` | 登录态，`localStorage` 持久化 |
| `useDataStore` | `mode`, `nodes`, `customers`, `matrixInfo` | 当前数据集 |
| `useSolveStore` | `algorithm`, `lambdas`, `Q`, `acoParams`, `taskId`, `status` | 求解配置与状态 |
| `useResultStore` | `routes`, `kpi`, `convergence`, `paretoPoints`, `schedule` | 求解结果 |

## 9. API 请求规范

**axios 实例（`api/request.js`）：**

```javascript
import axios from 'axios'

const request = axios.create({
  baseURL: '/api',       // 通过 Vite proxy 转发到 localhost:5000
  timeout: 30000
})

// 请求拦截：自动附加 Token
request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：统一错误处理
request.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response?.status === 401) {
      // 跳转登录页
    }
    return Promise.reject(err)
  }
)

export default request
```

## 10. 语言约定

| 位置 | 语言 |
|------|------|
| 界面标签、按钮文字、提示信息 | 中文 |
| 代码变量名、函数名、类名 | 英文 |
| 代码注释 | 中文 |
| 图表坐标轴标签、图例 | 中文 |
