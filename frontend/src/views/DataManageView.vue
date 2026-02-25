<template>
  <div class="data-manage" v-loading="loading">
    <!-- 数据源选择区 -->
    <el-card shadow="hover" class="config-card">
      <el-form label-width="100px">
        <el-form-item label="数据模式">
          <el-radio-group v-model="dataStore.mode" @change="handleModeChange">
            <el-radio value="solomon">Solomon 基准算例</el-radio>
            <el-radio value="seoul">首尔仿真数据</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="选择实例">
          <el-select
            v-model="dataStore.instance"
            placeholder="请选择数据实例"
            style="width: 240px"
          >
            <el-option
              v-for="item in instanceList"
              :key="item.name || item"
              :label="item.name || item"
              :value="item.name || item"
            />
          </el-select>
        </el-form-item>

        <!-- 仿真模式：应急等级比例 -->
        <template v-if="dataStore.mode === 'seoul'">
          <el-form-item label="医疗急件 %">
            <el-input-number v-model="ratio.medical" :min="0" :max="100" />
          </el-form-item>
          <el-form-item label="生鲜 %">
            <el-input-number v-model="ratio.fresh" :min="0" :max="100" />
          </el-form-item>
          <el-form-item label="普通 %">
            <el-input-number v-model="ratio.normal" :min="0" :max="100" />
          </el-form-item>
          <el-form-item v-if="ratioSum !== 100">
            <el-text type="danger">比例总和须为 100（当前 {{ ratioSum }}）</el-text>
          </el-form-item>
        </template>

        <el-form-item>
          <el-button
            type="primary"
            :disabled="!dataStore.instance || (dataStore.mode === 'seoul' && ratioSum !== 100)"
            @click="handleLoad"
          >
            加载数据
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据预览区 -->
    <div class="preview-area" v-if="dataStore.customers.length">
      <div class="preview-left">
        <el-card shadow="hover" class="map-card">
          <template #header>客户分布预览</template>
          <RouteMap
            :depot="dataStore.depot"
            :customers="dataStore.customers"
            :coord-mode="dataStore.mode"
            mode="preview"
          />
        </el-card>
      </div>
      <div class="preview-right">
        <el-card shadow="hover">
          <template #header>
            客户列表（共 {{ dataStore.customers.length }} 个）
          </template>
          <el-table
            :data="dataStore.customers"
            stripe
            border
            height="450"
            size="small"
          >
            <el-table-column prop="id" label="编号" width="60" />
            <el-table-column label="坐标" width="120">
              <template #default="{ row }">
                ({{ row.x_coord?.toFixed(1) }}, {{ row.y_coord?.toFixed(1) }})
              </template>
            </el-table-column>
            <el-table-column prop="demand_weight" label="需求量" width="80" />
            <el-table-column label="时间窗" width="120">
              <template #default="{ row }">
                [{{ row.early_time }}, {{ row.late_time }}]
              </template>
            </el-table-column>
            <el-table-column label="应急等级" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="levelTagType(row.emergency_level)"
                  size="small"
                >
                  {{ levelLabel(row.emergency_level) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>

    <!-- 未加载提示 -->
    <el-empty v-if="!dataStore.customers.length && !loading" description="请选择数据实例并加载" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useDataStore } from '../stores/data'
import { getSolomonList, getSeoulList, loadDataset, getCustomers, getDepot } from '../api/data'
import RouteMap from '../components/map/RouteMap.vue'

const dataStore = useDataStore()
const loading = ref(false)
const ratio = ref({ medical: 10, fresh: 20, normal: 70 })

const ratioSum = computed(() => ratio.value.medical + ratio.value.fresh + ratio.value.normal)

const instanceList = computed(() => {
  return dataStore.mode === 'solomon' ? dataStore.solomonList : dataStore.seoulList
})

onMounted(async () => {
  await fetchLists()
})

async function fetchLists() {
  try {
    const [solRes, seoulRes] = await Promise.all([
      getSolomonList(),
      getSeoulList().catch(() => ({ success: true, data: { instances: [] } }))
    ])
    if (solRes.success) dataStore.solomonList = solRes.data.instances
    if (seoulRes.success) dataStore.seoulList = seoulRes.data?.instances || []
  } catch {
    // 错误已由拦截器处理
  }
}

function handleModeChange() {
  dataStore.instance = ''
  dataStore.reset()
}

async function handleLoad() {
  loading.value = true
  try {
    const params = {
      mode: dataStore.mode,
      instance: dataStore.instance
    }
    if (dataStore.mode === 'seoul') {
      params.emergency_ratio = { ...ratio.value }
    }
    const res = await loadDataset(params)
    if (res.success) {
      // 拉取客户和depot详情
      const [custRes, depotRes] = await Promise.all([getCustomers(), getDepot()])
      if (custRes.success) dataStore.customers = custRes.data.customers
      if (depotRes.success) dataStore.depot = depotRes.data.depot
      dataStore.matrixInfo = res.data.matrix_summary || null
      ElMessage.success('数据加载成功')
    }
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function levelTagType(level) {
  const map = { medical: 'danger', fresh: 'warning', normal: '' }
  return map[level] || ''
}

function levelLabel(level) {
  const map = { medical: '医疗急件', fresh: '生鲜', normal: '普通' }
  return map[level] || level
}
</script>

<style scoped>
.config-card {
  margin-bottom: 20px;
}
.preview-area {
  display: flex;
  gap: 20px;
}
.preview-left {
  flex: 1;
}
.preview-right {
  flex: 1;
}
.map-card :deep(.el-card__body) {
  padding: 0;
  height: 450px;
}
</style>
