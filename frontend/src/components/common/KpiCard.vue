<template>
  <el-card shadow="hover" class="kpi-card">
    <div class="kpi-icon" :style="{ color }">
      <el-icon :size="32"><component :is="icon" /></el-icon>
    </div>
    <div class="kpi-info">
      <div class="kpi-value" :style="{ color }">{{ formattedValue }}</div>
      <div class="kpi-label">{{ label }}</div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: { type: String, default: 'DataLine' },
  label: { type: String, default: '' },
  value: { type: [Number, String], default: 0 },
  color: { type: String, default: '#409EFF' }
})

const formattedValue = computed(() => {
  if (typeof props.value === 'string') return props.value
  if (Number.isInteger(props.value)) return props.value
  return props.value.toFixed(2)
})
</script>

<style scoped>
.kpi-card {
  display: flex;
  align-items: center;
}
.kpi-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  width: 100%;
}
.kpi-icon {
  flex-shrink: 0;
}
.kpi-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}
.kpi-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
</style>
