// 求解状态管理
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSolveStore = defineStore('solve', () => {
  // 算法选择
  const algorithm = ref('improved_aco')
  // λ 权重
  const lambdas = ref([0.33, 0.33, 0.34])
  // 车辆载重
  const Q = ref(1000)
  // 算法参数
  const params = ref({})
  // 任务ID
  const taskId = ref('')
  // 求解状态：idle / running / done / error
  const status = ref('idle')
  // SSE 日志
  const logs = ref([])

  function reset() {
    taskId.value = ''
    status.value = 'idle'
    logs.value = []
  }

  return { algorithm, lambdas, Q, params, taskId, status, logs, reset }
})
