<template>
  <div class="benchmark-page" v-loading="loading">
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      closable
      style="margin-bottom: 16px"
    />

    <template v-if="allData.length">
      <!-- 数据集切换 -->
      <el-tabs v-model="activeTab" type="border-card" class="dataset-tabs">
        <el-tab-pane
          v-for="(ds, idx) in allData"
          :key="idx"
          :label="ds.dataset"
          :name="String(idx)"
        >
          <!-- 数据集基本信息 -->
          <div class="dataset-info">
            <span>客户数：<strong>{{ ds.customer_count }}</strong></span>
            <span>车辆容量：<strong>{{ ds.vehicle_capacity }}</strong></span>
            <span>权重 λ：<strong>[{{ ds.lambdas.join(', ') }}]</strong></span>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 性能指标表 -->
      <el-card shadow="hover" style="margin-bottom: 16px">
        <template #header>算法性能指标汇总</template>
        <el-table :data="tableData" stripe border size="small">
          <el-table-column prop="name" label="算法" width="120" />
          <el-table-column prop="best_z" label="最优 Z" width="100" />
          <el-table-column prop="avg_z" label="平均 Z" width="100" />
          <el-table-column prop="std_z" label="标准差" width="100" />
          <el-table-column prop="best_f1" label="F1 (成本)" width="120" />
          <el-table-column prop="best_f2" label="F2' (时间)" width="120" />
          <el-table-column prop="best_f3" label="F3 (惩罚)" width="120" />
          <el-table-column prop="vehicles_used" label="车辆数" width="80" />
          <el-table-column prop="avg_time" label="耗时(s)" width="90" />
          <el-table-column label="准确率" width="100">
            <template #default="{ row }">
              <el-tag
                v-if="row.accuracy != null"
                :type="row.accuracy >= 80 ? 'success' : row.accuracy >= 60 ? 'warning' : 'danger'"
                size="small"
              >
                {{ row.accuracy }}%
              </el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 图表区域 -->
      <div class="charts-row">
        <el-card shadow="hover" class="chart-card">
          <template #header>目标函数对比 (F1 / F2' / F3)</template>
          <v-chart :option="objectiveBarOption" autoresize style="height: 360px" />
        </el-card>
        <el-card shadow="hover" class="chart-card">
          <template #header>vs OR-Tools 准确率</template>
          <v-chart :option="accuracyBarOption" autoresize style="height: 360px" />
        </el-card>
      </div>

      <div class="charts-row">
        <el-card shadow="hover" class="chart-card">
          <template #header>收敛曲线对比</template>
          <v-chart :option="convergenceOption" autoresize style="height: 360px" />
        </el-card>
        <el-card shadow="hover" class="chart-card">
          <template #header>不同 λ 配置下的 Pareto 近似解</template>
          <v-chart :option="paretoOption" autoresize style="height: 360px" />
        </el-card>
      </div>

      <el-card shadow="hover" style="margin-bottom: 16px">
        <template #header>平均运行耗时对比</template>
        <v-chart :option="timeBarOption" autoresize style="height: 300px" />
      </el-card>

      <!-- 跨数据集准确率汇总 -->
      <el-card shadow="hover" style="margin-bottom: 16px">
        <template #header>改进ACO 各数据集准确率汇总</template>
        <v-chart :option="crossDatasetOption" autoresize style="height: 300px" />
      </el-card>
    </template>

    <el-empty v-if="!allData.length && !loading" description="未找到基准测试数据" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'

const loading = ref(false)
const error = ref('')
const allData = ref([])
const activeTab = ref('0')

const COLORS = {
  '改进ACO': '#409EFF',
  '标准ACO': '#67C23A',
  '遗传算法': '#E6A23C',
  '模拟退火': '#F56C6C',
  'OR-Tools': '#909399'
}

// 当前选中的数据集
const data = computed(() => {
  const idx = parseInt(activeTab.value)
  return allData.value[idx] || null
})

onMounted(async () => {
  loading.value = true
  try {
    const res = await fetch('/benchmark.json')
    if (!res.ok) throw new Error('加载失败')
    const json = await res.json()
    // 兼容旧格式（单个对象）和新格式（数组）
    allData.value = Array.isArray(json) ? json : [json]
  } catch (e) {
    error.value = '无法加载基准测试数据：' + e.message
  } finally {
    loading.value = false
  }
})

// 表格数据
const tableData = computed(() => {
  if (!data.value) return []
  return Object.entries(data.value.algorithms).map(([name, algo]) => ({
    name,
    best_z: algo.best_z ?? '—',
    avg_z: algo.avg_z ?? '—',
    std_z: algo.std_z ?? '—',
    best_f1: algo.best_f1?.toFixed(2),
    best_f2: algo.best_f2?.toFixed(2),
    best_f3: algo.best_f3?.toFixed(2),
    vehicles_used: algo.vehicles_used,
    avg_time: algo.avg_time,
    accuracy: algo.accuracy_vs_ortools ?? null
  }))
})

// 算法名列表（不含 OR-Tools）
const algoNames = computed(() => {
  if (!data.value) return []
  return Object.keys(data.value.algorithms).filter(n => n !== 'OR-Tools')
})

// 全部算法名
const allNames = computed(() => {
  if (!data.value) return []
  return Object.keys(data.value.algorithms)
})

// 目标函数柱状图
const objectiveBarOption = computed(() => {
  if (!data.value) return {}
  const algos = data.value.algorithms
  const names = allNames.value
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['F1 (成本)', "F2' (时间)", 'F3 (惩罚)'] },
    grid: { left: 60, right: 20, bottom: 40, top: 50 },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 15 } },
    yAxis: { type: 'value', name: '数值' },
    series: [
      {
        name: 'F1 (成本)',
        type: 'bar',
        data: names.map(n => algos[n].best_f1),
        itemStyle: { color: '#409EFF' }
      },
      {
        name: "F2' (时间)",
        type: 'bar',
        data: names.map(n => algos[n].best_f2),
        itemStyle: { color: '#E6A23C' }
      },
      {
        name: 'F3 (惩罚)',
        type: 'bar',
        data: names.map(n => algos[n].best_f3),
        itemStyle: { color: '#F56C6C' }
      }
    ]
  }
})

// 准确率柱状图
const accuracyBarOption = computed(() => {
  if (!data.value) return {}
  const algos = data.value.algorithms
  const names = algoNames.value
  return {
    tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
    grid: { left: 60, right: 20, bottom: 40, top: 30 },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 15 } },
    yAxis: { type: 'value', name: '准确率 (%)', max: 100 },
    series: [{
      type: 'bar',
      data: names.map(n => ({
        value: algos[n].accuracy_vs_ortools,
        itemStyle: {
          color: algos[n].accuracy_vs_ortools >= 80 ? '#67C23A' : '#E6A23C'
        }
      })),
      label: { show: true, position: 'top', formatter: '{c}%' },
      markLine: {
        data: [{ yAxis: 80, name: '目标线 80%' }],
        lineStyle: { color: '#F56C6C', type: 'dashed' },
        label: { formatter: '目标 80%' }
      }
    }]
  }
})

// 收敛曲线
const convergenceOption = computed(() => {
  if (!data.value) return {}
  const algos = data.value.algorithms
  const series = []
  for (const [name, algo] of Object.entries(algos)) {
    if (!algo.convergence || algo.convergence.length === 0) continue
    series.push({
      name,
      type: 'line',
      smooth: true,
      data: algo.convergence.map(p => [p[0], p[1]]),
      lineStyle: { color: COLORS[name] || '#909399' },
      itemStyle: { color: COLORS[name] || '#909399' },
      showSymbol: false
    })
  }
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(s => s.name) },
    grid: { left: 60, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'value', name: '迭代次数' },
    yAxis: { type: 'value', name: 'Z 值' },
    series
  }
})

// Pareto 散点图
const paretoOption = computed(() => {
  if (!data.value || !data.value.pareto_points) return {}
  const points = data.value.pareto_points
  return {
    tooltip: {
      trigger: 'item',
      formatter: p => {
        const d = points[p.dataIndex]
        return `${d.name}<br/>λ=[${d.lambdas.join(',')}]<br/>` +
          `F1=${d.f1.toFixed(1)}<br/>F2'=${d.f2.toFixed(1)}<br/>` +
          `F3=${d.f3.toFixed(1)}<br/>Z=${d.z.toFixed(4)}<br/>车辆=${d.vehicles_used}`
      }
    },
    grid: { left: 70, right: 30, bottom: 50, top: 30 },
    xAxis: { type: 'value', name: 'F1 (经济成本)' },
    yAxis: { type: 'value', name: "F2' (加权完工时间)" },
    series: [{
      type: 'scatter',
      symbolSize: 16,
      data: points.map(p => [p.f1, p.f2]),
      label: {
        show: true,
        formatter: p => points[p.dataIndex].name,
        position: 'top'
      },
      itemStyle: {
        color: p => {
          const colors = ['#409EFF', '#E6A23C', '#67C23A']
          return colors[p.dataIndex % colors.length]
        }
      }
    }]
  }
})

// 耗时对比柱状图
const timeBarOption = computed(() => {
  if (!data.value) return {}
  const algos = data.value.algorithms
  const names = allNames.value
  return {
    tooltip: { trigger: 'axis', formatter: '{b}: {c}s' },
    grid: { left: 60, right: 20, bottom: 40, top: 20 },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 15 } },
    yAxis: { type: 'value', name: '耗时 (秒)' },
    series: [{
      type: 'bar',
      data: names.map(n => ({
        value: algos[n].avg_time,
        itemStyle: { color: COLORS[n] || '#909399' }
      })),
      label: { show: true, position: 'top', formatter: '{c}s' }
    }]
  }
})

// 跨数据集：改进ACO 准确率汇总
const crossDatasetOption = computed(() => {
  if (!allData.value.length) return {}
  const labels = []
  const values = []
  for (const ds of allData.value) {
    const acc = ds.algorithms?.['改进ACO']?.accuracy_vs_ortools
    if (acc != null) {
      labels.push(ds.dataset.replace('Solomon ', ''))
      values.push(acc)
    }
  }
  return {
    tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
    grid: { left: 60, right: 20, bottom: 40, top: 20 },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value', name: '准确率 (%)', max: 100 },
    series: [{
      type: 'bar',
      data: values.map(v => ({
        value: v,
        itemStyle: { color: v >= 80 ? '#67C23A' : v >= 60 ? '#E6A23C' : '#F56C6C' }
      })),
      label: { show: true, position: 'top', formatter: '{c}%' },
      markLine: {
        data: [{ yAxis: 80, name: '目标 80%' }],
        lineStyle: { color: '#F56C6C', type: 'dashed' },
        label: { formatter: '目标 80%' }
      }
    }]
  }
})
</script>

<style scoped>
.dataset-tabs {
  margin-bottom: 16px;
}
.dataset-info {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  padding: 4px 0;
}
.charts-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}
.chart-card {
  flex: 1;
  min-width: 0;
}
</style>
