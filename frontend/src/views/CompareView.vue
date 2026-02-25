<template>
  <div class="compare-view">
    <!-- 配置区 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header>对比配置</template>
      <el-form label-width="120px">
        <el-form-item label="选择算法">
          <el-checkbox-group v-model="selectedAlgos">
            <el-checkbox value="improved_aco" label="改进ACO" />
            <el-checkbox value="standard_aco" label="标准ACO" />
            <el-checkbox value="genetic" label="遗传算法" />
            <el-checkbox value="simulated_annealing" label="模拟退火" />
          </el-checkbox-group>
          <div v-if="selectedAlgos.length < 2" class="hint-text">
            请至少选择 2 个算法
          </div>
        </el-form-item>

        <el-form-item label="决策偏好 (λ)">
          <LambdaSlider v-model="lambdas" />
        </el-form-item>

        <el-form-item label="车辆载重 Q">
          <el-input-number v-model="Q" :min="100" :max="5000" :step="100" />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :disabled="selectedAlgos.length < 2 || !dataStore.customers.length || running"
            :loading="running"
            @click="handleStart"
          >
            启动对比运行
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- SSE 日志 -->
    <el-card v-if="logs.length" shadow="hover" style="margin-bottom: 16px">
      <template #header>运行日志</template>
      <SseLogBox :logs="logs" />
    </el-card>

    <!-- 对比结果区 -->
    <template v-if="compareResults.length">
      <!-- 柱状图 -->
      <el-card shadow="hover" style="margin-bottom: 16px">
        <template #header>指标对比</template>
        <v-chart class="bar-chart" :option="barOption" autoresize />
      </el-card>

      <!-- 收敛对比 -->
      <el-card shadow="hover" style="margin-bottom: 16px">
        <template #header>收敛曲线对比</template>
        <ConvergenceChart :multi-series="convergenceData" />
      </el-card>

      <!-- 性能指标表 -->
      <el-card shadow="hover">
        <template #header>性能指标</template>
        <el-table :data="compareResults" stripe border size="small">
          <el-table-column prop="algorithm" label="算法" width="120">
            <template #default="{ row }">{{ algoLabel(row.algorithm) }}</template>
          </el-table-column>
          <el-table-column label="最优Z" width="100">
            <template #default="{ row }">{{ row.best_z?.toFixed(4) }}</template>
          </el-table-column>
          <el-table-column label="平均Z" width="100">
            <template #default="{ row }">{{ row.avg_z?.toFixed(4) }}</template>
          </el-table-column>
          <el-table-column label="标准差" width="100">
            <template #default="{ row }">{{ row.std_z?.toFixed(4) }}</template>
          </el-table-column>
          <el-table-column label="车辆数" width="80" prop="vehicles_used" />
        </el-table>
      </el-card>
    </template>

    <el-alert
      v-if="!dataStore.customers.length"
      title="请先在数据管理页加载数据集"
      type="warning"
      show-icon
      :closable="false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useDataStore } from '../stores/data'
import { startCompare, getCompareResult } from '../api/compare'
import { createSseConnection } from '../utils/sse'
import LambdaSlider from '../components/common/LambdaSlider.vue'
import SseLogBox from '../components/common/SseLogBox.vue'
import ConvergenceChart from '../components/charts/ConvergenceChart.vue'

use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const dataStore = useDataStore()

const selectedAlgos = ref(['improved_aco', 'standard_aco'])
const lambdas = ref([0.33, 0.33, 0.34])
const Q = ref(1000)
const running = ref(false)
const logs = ref([])
const compareResults = ref([])

let eventSource = null

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})

const ALGO_LABELS = {
  improved_aco: '改进ACO',
  standard_aco: '标准ACO',
  genetic: '遗传算法',
  simulated_annealing: '模拟退火'
}

function algoLabel(key) {
  return ALGO_LABELS[key] || key
}

// 收敛曲线多系列数据
const convergenceData = computed(() => {
  const result = {}
  compareResults.value.forEach(r => {
    if (r.convergence) {
      result[algoLabel(r.algorithm)] = r.convergence
    }
  })
  return result
})

// 柱状图配置
const barOption = computed(() => {
  const algos = compareResults.value.map(r => algoLabel(r.algorithm))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['F1', "F2'", 'F3', 'Z'] },
    grid: { left: 60, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: algos },
    yAxis: { type: 'value' },
    series: [
      { name: 'F1', type: 'bar', data: compareResults.value.map(r => r.best_f1) },
      { name: "F2'", type: 'bar', data: compareResults.value.map(r => r.best_f2) },
      { name: 'F3', type: 'bar', data: compareResults.value.map(r => r.best_f3) },
      { name: 'Z', type: 'bar', data: compareResults.value.map(r => r.best_z) }
    ]
  }
})

async function handleStart() {
  running.value = true
  logs.value = []
  compareResults.value = []

  try {
    const res = await startCompare({
      algorithms: selectedAlgos.value,
      lambdas: lambdas.value,
      Q: Q.value
    })

    if (!res.success) {
      running.value = false
      return
    }

    connectSse(res.data.task_id)
  } catch {
    running.value = false
  }
}

function connectSse(taskId) {
  eventSource = createSseConnection(`/api/compare/stream/${taskId}`, {
    onMessage(data) {
      logs.value.push(data)
    },
    async onDone() {
      eventSource = null
      try {
        const res = await getCompareResult(taskId)
        if (res.success) {
          compareResults.value = res.data.results || []
          ElMessage.success('对比运行完成')
        }
      } catch {
        ElMessage.error('获取对比结果失败')
      } finally {
        running.value = false
      }
    },
    onError(msg) {
      logs.value.push({ type: 'error', message: msg })
      running.value = false
      eventSource = null
    }
  })
}
</script>

<style scoped>
.hint-text {
  font-size: 12px;
  color: #E6A23C;
  margin-top: 4px;
}
.bar-chart {
  width: 100%;
  height: 350px;
}
</style>
