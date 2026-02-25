// 数据状态管理
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useDataStore = defineStore('data', () => {
  // 数据模式：solomon / seoul
  const mode = ref('solomon')
  // 当前实例名
  const instance = ref('')
  // 配送中心
  const depot = ref(null)
  // 客户列表
  const customers = ref([])
  // 距离矩阵摘要
  const matrixInfo = ref(null)
  // Solomon 算例列表
  const solomonList = ref([])
  // 首尔数据集列表
  const seoulList = ref([])

  function reset() {
    instance.value = ''
    depot.value = null
    customers.value = []
    matrixInfo.value = null
  }

  return {
    mode, instance, depot, customers, matrixInfo,
    solomonList, seoulList, reset
  }
})
