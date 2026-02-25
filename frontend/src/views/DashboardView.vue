<template>
  <div class="dashboard">
    <!-- 顶部 Hero 区域 -->
    <div class="hero">
      <div class="hero-text">
        <h1>MOURO 多目标城市配送路径优化系统</h1>
        <p class="hero-desc">
          基于改进蚁群算法，综合考虑<span class="hl">经济成本</span>、
          <span class="hl">配送时效</span>与<span class="hl">时间窗惩罚</span>，
          为城市末端配送场景提供智能路径规划方案。
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="$router.push('/data')">
            <el-icon><FolderOpened /></el-icon>加载数据
          </el-button>
          <el-button size="large" @click="$router.push('/solve')">
            <el-icon><Cpu /></el-icon>开始求解
          </el-button>
        </div>
      </div>
      <div class="hero-formula">
        <div class="formula-card">
          <div class="formula-label">综合目标函数</div>
          <div class="formula">Z = λ₁F₁* + λ₂F₂'* + λ₃F₃*</div>
          <div class="formula-sub">Min-Max 归一化 · λ₁+λ₂+λ₃=1</div>
        </div>
      </div>
    </div>

    <!-- 系统能力数字 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" v-for="item in stats" :key="item.label">
        <div class="stat-card">
          <div class="stat-value" :style="{ color: item.color }">{{ item.value }}</div>
          <div class="stat-label">{{ item.label }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 工作流程 -->
    <el-card shadow="hover" class="section-card">
      <template #header>
        <div class="section-header">
          <el-icon><Guide /></el-icon>
          <span>系统工作流程</span>
        </div>
      </template>
      <div class="workflow">
        <div class="wf-step" v-for="(step, i) in workflow" :key="i">
          <div class="wf-icon" :style="{ background: step.color }">
            <el-icon :size="24" color="#fff"><component :is="step.icon" /></el-icon>
          </div>
          <div class="wf-title">{{ step.title }}</div>
          <div class="wf-desc">{{ step.desc }}</div>
          <div class="wf-arrow" v-if="i < workflow.length - 1">→</div>
        </div>
      </div>
    </el-card>

    <!-- 三个目标函数说明 -->
    <el-row :gutter="16" class="section-card">
      <el-col :span="8" v-for="obj in objectives" :key="obj.name">
        <el-card shadow="hover" class="obj-card">
          <div class="obj-icon" :style="{ background: obj.bg }">
            <el-icon :size="28" :color="obj.color"><component :is="obj.icon" /></el-icon>
          </div>
          <h3>{{ obj.name }}</h3>
          <p class="obj-formula">{{ obj.formula }}</p>
          <p class="obj-desc">{{ obj.desc }}</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- 技术亮点 -->
    <el-card shadow="hover" class="section-card">
      <template #header>
        <div class="section-header">
          <el-icon><Cpu /></el-icon>
          <span>算法改进亮点</span>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="6" v-for="feat in features" :key="feat.title">
          <div class="feat-item">
            <div class="feat-tag" :style="{ color: feat.color, borderColor: feat.color }">
              {{ feat.tag }}
            </div>
            <div class="feat-title">{{ feat.title }}</div>
            <div class="feat-desc">{{ feat.desc }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
const stats = [
  { value: '4', label: '求解算法', color: '#409EFF' },
  { value: '3', label: '优化目标', color: '#E6A23C' },
  { value: '3', label: '应急等级', color: '#F56C6C' },
  { value: '6+', label: '基准算例', color: '#67C23A' },
]

const workflow = [
  { icon: 'FolderOpened', title: '加载数据', desc: 'Solomon 算例 / 首尔仿真', color: '#409EFF' },
  { icon: 'Setting', title: '配置参数', desc: '算法选择 / λ权重 / 载重', color: '#E6A23C' },
  { icon: 'Cpu', title: '智能求解', desc: 'SSE 实时推送迭代进度', color: '#67C23A' },
  { icon: 'DataAnalysis', title: '结果分析', desc: '路线地图 / KPI / 收敛曲线', color: '#F56C6C' },
]

const objectives = [
  {
    name: 'F₁ 经济成本',
    formula: 'F₁ = Σ(固定成本 + 距离成本)',
    desc: '包含车辆固定调度费用和行驶里程费用，含回程距离',
    icon: 'Money',
    color: '#409EFF',
    bg: '#ecf5ff',
  },
  {
    name: "F₂' 加权完工时间",
    formula: "F₂' = Σ(ωᵢ × tᵢ)",
    desc: '按应急权重加权的客户到达时间总和，医疗急件权重最高',
    icon: 'Timer',
    color: '#E6A23C',
    bg: '#fdf6ec',
  },
  {
    name: 'F₃ 时间窗惩罚',
    formula: 'F₃ = Σ Pᵢ(t)',
    desc: '早到或迟到产生的惩罚成本，惩罚系数与应急等级挂钩',
    icon: 'WarningFilled',
    color: '#F56C6C',
    bg: '#fef0f0',
  },
]

const features = [
  {
    tag: '双信息素',
    title: '成本 + 时间双矩阵',
    desc: 'τ_cost 和 τ_time 独立挥发与沉积',
    color: '#409EFF',
  },
  {
    tag: '双启发式',
    title: '距离 + 时间双引导',
    desc: 'η_cost=1/dᵢⱼ 与 η_time=1/tᵢⱼ',
    color: '#67C23A',
  },
  {
    tag: '精英策略',
    title: '全局最优信息素更新',
    desc: '仅最优解的边获得信息素增量',
    color: '#E6A23C',
  },
  {
    tag: '局部搜索',
    title: '2-opt + Relocate',
    desc: '路线内优化 + 路线间客户迁移',
    color: '#F56C6C',
  },
]
</script>

<style scoped>
.dashboard {
  max-width: 1100px;
  margin: 0 auto;
}

/* Hero */
.hero {
  display: flex;
  align-items: center;
  gap: 40px;
  padding: 32px 0 24px;
}
.hero-text {
  flex: 1;
}
.hero-text h1 {
  font-size: 26px;
  color: #1d2129;
  margin: 0 0 12px;
  font-weight: 700;
}
.hero-desc {
  color: #606266;
  line-height: 1.8;
  font-size: 15px;
  margin: 0 0 20px;
}
.hero-desc .hl {
  color: #409EFF;
  font-weight: 600;
}
.hero-actions {
  display: flex;
  gap: 12px;
}
.hero-formula {
  flex-shrink: 0;
}
.formula-card {
  background: #1d2129;
  border-radius: 16px;
  padding: 28px 32px;
  text-align: center;
  color: #fff;
  min-width: 260px;
  border: 1px solid #3a3f47;
}
.formula-label {
  font-size: 13px;
  opacity: 0.85;
  margin-bottom: 12px;
}
.formula {
  font-size: 22px;
  font-weight: 700;
  font-family: 'Georgia', serif;
  letter-spacing: 1px;
}
.formula-sub {
  font-size: 12px;
  opacity: 0.7;
  margin-top: 10px;
}

/* Stats */
.stats-row {
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.stat-value {
  font-size: 36px;
  font-weight: 700;
}
.stat-label {
  color: #909399;
  font-size: 13px;
  margin-top: 4px;
}

/* Section */
.section-card {
  margin-bottom: 20px;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

/* Workflow */
.workflow {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
  padding: 8px 0;
}
.wf-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  position: relative;
  flex: 1;
}
.wf-icon {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}
.wf-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
.wf-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.wf-arrow {
  position: absolute;
  right: -12px;
  top: 16px;
  font-size: 20px;
  color: #c0c4cc;
  font-weight: 700;
}

/* Objectives */
.obj-card {
  text-align: center;
  padding: 8px 0;
}
.obj-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
}
.obj-card h3 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #303133;
}
.obj-formula {
  font-family: 'Georgia', serif;
  color: #606266;
  font-size: 14px;
  margin: 0 0 6px;
}
.obj-desc {
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
}

/* Features */
.feat-item {
  text-align: center;
  padding: 12px 0;
}
.feat-tag {
  display: inline-block;
  border: 1.5px solid;
  border-radius: 12px;
  padding: 2px 12px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}
.feat-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.feat-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}
</style>
