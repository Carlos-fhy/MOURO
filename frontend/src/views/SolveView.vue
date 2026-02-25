<template>
  <div class="solve-view">
    <!-- 前置检查 -->
    <el-alert
      v-if="!dataStore.customers.length"
      title="请先在数据管理页加载数据集"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-row :gutter="20">
      <!-- 左侧：配置区 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>求解配置</template>
          <el-form label-width="120px">
            <!-- 算法选择 -->
            <el-form-item label="选择算法">
              <el-radio-group v-model="solveStore.algorithm">
                <el-radio value="improved_aco">改进ACO</el-radio>
                <el-radio value="standard_aco">标准ACO</el-radio>
                <el-radio value="genetic">遗传算法</el-radio>
                <el-radio value="simulated_annealing">模拟退火</el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- 决策偏好 -->
            <el-form-item label="决策偏好 (λ)">
              <LambdaSlider v-model="solveStore.lambdas" />
            </el-form-item>

            <!-- 车辆载重 -->
            <el-form-item label="车辆载重 Q">
              <el-input-number
                v-model="solveStore.Q"
                :min="100"
                :max="5000"
                :step="100"
              />
            </el-form-item>

            <!-- 高级参数 -->
            <el-form-item label="高级参数">
              <ParamPanel
                :algorithm="solveStore.algorithm"
                v-model="solveStore.params"
              />
            </el-form-item>

            <!-- 启动按钮 -->
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

      <!-- 右侧：日志区 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>运行日志</template>
          <SseLogBox :logs="solveStore.logs" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useDataStore } from '../stores/data'
import { useSolveStore } from '../stores/solve'
import { useResultStore } from '../stores/result'
import { startSolve, getResult } from '../api/solve'
import { createSseConnection } from '../utils/sse'
import LambdaSlider from '../components/common/LambdaSlider.vue'
import ParamPanel from '../components/common/ParamPanel.vue'
import SseLogBox from '../components/common/SseLogBox.vue'

const router = useRouter()
const dataStore = useDataStore()
const solveStore = useSolveStore()
const resultStore = useResultStore()

let eventSource = null

onUnmounted(() => {
  // 组件卸载时关闭 SSE 连接
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})

async function handleStart() {
  solveStore.reset()
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
      solveStore.logs.push(data)
    },
    async onDone(data) {
      solveStore.logs.push(data)
      solveStore.status = 'done'
      eventSource = null

      // 拉取完整结果
      try {
        const res = await getResult(taskId)
        if (res.success) {
          resultStore.setResult(res.data)
          ElMessage.success('求解完成，正在跳转决策看板')
          router.push('/result')
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
.solve-view {
  max-width: 1200px;
}
</style>
