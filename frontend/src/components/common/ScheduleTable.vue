<template>
  <el-table
    :data="schedule"
    stripe
    border
    size="small"
    :row-class-name="rowClassName"
  >
    <el-table-column prop="vehicle_id" label="车辆号" width="80" />
    <el-table-column prop="customer_id" label="客户编号" width="80" />
    <el-table-column label="到达时刻" width="100">
      <template #default="{ row }">
        {{ row.arrival_time?.toFixed(1) }}
      </template>
    </el-table-column>
    <el-table-column label="卸货重量" width="100">
      <template #default="{ row }">
        {{ row.demand?.toFixed(1) }}
      </template>
    </el-table-column>
    <el-table-column label="惩罚" width="100">
      <template #default="{ row }">
        <span :class="row.penalty > 0 ? 'penalty-warn' : ''">
          {{ row.penalty?.toFixed(2) }}
        </span>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="80">
      <template #default="{ row }">
        <el-tag :type="statusType(row.status)" size="small">
          {{ statusLabel(row.status) }}
        </el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
defineProps({
  schedule: { type: Array, default: () => [] }
})

function statusType(status) {
  const map = { on_time: 'success', early: 'warning', late: 'danger' }
  return map[status] || 'info'
}

function statusLabel(status) {
  const map = { on_time: '准时', early: '早到', late: '迟到' }
  return map[status] || status
}

function rowClassName({ row }) {
  if (row.status === 'late') return 'row-late'
  return ''
}
</script>

<style scoped>
.penalty-warn {
  color: #F56C6C;
  font-weight: 600;
}
:deep(.row-late) {
  background-color: #fef0f0 !important;
}
</style>
