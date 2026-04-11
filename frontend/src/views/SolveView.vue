<template>
  <div class="solve-view">
    <el-alert
      v-if="!dataStore.customers.length"
      title="请先在数据管理页加载数据集"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>求解配置</template>
          <el-form label-width="120px">
            <el-form-item label="选择算法">
              <el-radio-group v-model="solveStore.algorithm">
                <el-radio value="improved_aco">改进ACO</el-radio>
                <el-radio value="standard_aco">标准ACO</el-radio>
                <el-radio value="genetic">遗传算法</el-radio>
                <el-radio value="alns">自适应大邻域搜索（ALNS）</el-radio>
                <el-radio value="simulated_annealing">模拟退火</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="决策偏好 (λ)">
              <LambdaSlider v-model="solveStore.lambdas" />
            </el-form-item>

            <el-form-item label="车辆载重 Q">
              <el-input-number
                v-model="solveStore.Q"
                :min="100"
                :max="5000"
                :step="100"
              />
            </el-form-item>

            <el-form-item label="高级参数">
              <ParamPanel
                :algorithm="solveStore.algorithm"
                v-model="solveStore.params"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :disabled="!dataStore.customers.length || solveStore.status === 'running'"
                :loading="solveStore.status === 'running'"
                @click="handleStart"
              >
                启动智能排线
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>运行日志</template>
          <SseLogBox :logs="solveStore.logs" />
        </el-card>
      </el-col>
    </el-row>

    <template v-if="resultStore.routes.length">
      <el-alert
        v-if="resultStore.unreachable.length"
        :title="`存在 ${resultStore.unreachable.length} 个不可达客户`"
        type="error"
        show-icon
        :closable="false"
        style="margin-top: 20px"
      />

      <el-row :gutter="16" class="kpi-row" style="margin-top: 20px">
        <el-col :span="6">
          <KpiCard icon="Money" label="总成本 F1" :value="resultStore.f1" color="#409EFF" />
        </el-col>
        <el-col :span="6">
          <KpiCard icon="Timer" label="加权时间 F2'" :value="resultStore.f2" color="#E6A23C" />
        </el-col>
        <el-col :span="6">
          <KpiCard icon="WarningFilled" label="惩罚成本 F3" :value="resultStore.f3" color="#F56C6C" />
        </el-col>
        <el-col :span="6">
          <KpiCard icon="Van" label="车辆使用数" :value="resultStore.vehiclesUsed" color="#67C23A" />
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="14">
          <el-card shadow="hover">
            <template #header>
              <div style="display:flex;align-items:center;justify-content:space-between">
                <span>路线地图</span>
                <el-button size="small" @click="routeMapRef?.replay()">
                  <el-icon><RefreshRight /></el-icon>重播动画
                </el-button>
              </div>
            </template>
            <RouteMap
              ref="routeMapRef"
              :depot="dataStore.depot"
              :customers="dataStore.customers"
              :routes="resultStore.routes"
              :schedule="resultStore.schedule"
              :coord-mode="dataStore.mode"
              mode="route"
            />
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card shadow="hover" style="margin-bottom: 16px">
            <template #header>收敛曲线</template>
            <ConvergenceChart :data="resultStore.convergence" />
          </el-card>
          <el-card shadow="hover">
            <template #header>Pareto 散点图</template>
            <ParetoChart
              :current-f1="resultStore.f1"
              :current-f2="resultStore.f2"
            />
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="hover" style="margin-top: 16px">
        <template #header>调度明细</template>
        <ScheduleTable :schedule="resultStore.schedule" />
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, nextTick, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'
import { useDataStore } from '../stores/data'
import { useSolveStore } from '../stores/solve'
import { useResultStore } from '../stores/result'
import { startSolve, getResult } from '../api/solve'
import { createSseConnection } from '../utils/sse'
import LambdaSlider from '../components/common/LambdaSlider.vue'
import ParamPanel from '../components/common/ParamPanel.vue'
import SseLogBox from '../components/common/SseLogBox.vue'
import KpiCard from '../components/common/KpiCard.vue'
import RouteMap from '../components/map/RouteMap.vue'
import ConvergenceChart from '../components/charts/ConvergenceChart.vue'
import ParetoChart from '../components/charts/ParetoChart.vue'
import ScheduleTable from '../components/common/ScheduleTable.vue'

const dataStore = useDataStore()
const solveStore = useSolveStore()
const resultStore = useResultStore()
const routeMapRef = ref(null)

let eventSource = null

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})

async function handleStart() {
  solveStore.reset()
  resultStore.reset()
  solveStore.status = 'running'

  try {
    const res = await startSolve({
      algorithm: solveStore.algorithm,
      lambdas: solveStore.lambdas,
      Q: solveStore.Q,
      params: solveStore.params
    })

    if (!res.success) {
      solveStore.status = 'error'
      return
    }

    solveStore.taskId = res.data.task_id
    connectSse(res.data.task_id)
  } catch {
    solveStore.status = 'error'
  }
}

function connectSse(taskId) {
  eventSource = createSseConnection(`/api/solve/stream/${taskId}`, {
    onMessage(data) {
      if (data.type === 'heartbeat') return
      solveStore.logs.push(data)
    },
    async onDone(data) {
      solveStore.logs.push(data)
      solveStore.status = 'done'
      eventSource = null

      try {
        const res = await getResult(taskId)
        if (res.success) {
          resultStore.setResult(res.data)
          ElMessage.success('求解完成')
          await nextTick()
          document.querySelector('.solve-view .kpi-row')
            ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      } catch {
        ElMessage.error('获取结果失败')
      }
    },
    onError(msg) {
      solveStore.logs.push({ type: 'error', message: msg })
      solveStore.status = 'error'
      eventSource = null
      ElMessage.error(typeof msg === 'string' ? msg : 'SSE 连接异常')
    }
  })
}
</script>

<style scoped>
.kpi-row {
  scroll-margin-top: 16px;
}
</style>
