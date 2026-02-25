// 结果状态管理
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useResultStore = defineStore('result', () => {
  // 路线数据
  const routes = ref([])
  // KPI 指标
  const f1 = ref(0)
  const f2 = ref(0)
  const f3 = ref(0)
  const z = ref(0)
  const vehiclesUsed = ref(0)
  // 收敛曲线数据
  const convergence = ref([])
  // 调度明细
  const schedule = ref([])
  // 不可达客户
  const unreachable = ref([])

  function setResult(data) {
    routes.value = data.routes || []
    f1.value = data.f1 ?? 0
    f2.value = data.f2 ?? 0
    f3.value = data.f3 ?? 0
    z.value = data.z ?? 0
    vehiclesUsed.value = data.vehicles_used ?? 0
    convergence.value = data.convergence || []
    schedule.value = data.schedule || []
    unreachable.value = data.unreachable || []
  }

  function reset() {
    routes.value = []
    f1.value = 0
    f2.value = 0
    f3.value = 0
    z.value = 0
    vehiclesUsed.value = 0
    convergence.value = []
    schedule.value = []
    unreachable.value = []
  }

  return {
    routes, f1, f2, f3, z, vehiclesUsed,
    convergence, schedule, unreachable,
    setResult, reset
  }
})
