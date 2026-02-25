<template>
  <div class="lambda-slider">
    <div class="presets">
      <el-button size="small" @click="applyPreset('cost')">省钱优先</el-button>
      <el-button size="small" @click="applyPreset('time')">抢时间</el-button>
      <el-button size="small" @click="applyPreset('balance')">均衡</el-button>
    </div>
    <div class="slider-row" v-for="(item, idx) in sliders" :key="idx">
      <span class="slider-label">{{ item.label }}</span>
      <el-slider
        :model-value="modelValue[idx]"
        :min="0"
        :max="1"
        :step="0.01"
        :show-tooltip="true"
        style="flex: 1"
        @input="val => handleChange(idx, val)"
      />
      <span class="slider-value">{{ modelValue[idx].toFixed(2) }}</span>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Array, default: () => [0.33, 0.33, 0.34] }
})
const emit = defineEmits(['update:modelValue'])

const sliders = [
  { label: 'λ₁ 成本' },
  { label: 'λ₂ 时效' },
  { label: 'λ₃ 惩罚' }
]

// 预设方案
const PRESETS = {
  cost: [0.7, 0.15, 0.15],
  time: [0.15, 0.7, 0.15],
  balance: [0.33, 0.33, 0.34]
}

function applyPreset(key) {
  emit('update:modelValue', [...PRESETS[key]])
}

// 调整一个滑块时，另两个按比例缩放保证总和=1
function handleChange(idx, newVal) {
  const values = [...props.modelValue]
  const oldVal = values[idx]
  const diff = newVal - oldVal
  values[idx] = newVal

  // 计算其余两个的总和
  const otherIndices = [0, 1, 2].filter(i => i !== idx)
  const otherSum = otherIndices.reduce((s, i) => s + values[i], 0)

  if (otherSum > 0) {
    // 按比例分配差值
    otherIndices.forEach(i => {
      values[i] = Math.max(0, values[i] - diff * (values[i] / otherSum))
    })
  } else {
    // 其余都为0，平分剩余
    const remain = 1 - newVal
    otherIndices.forEach(i => {
      values[i] = remain / 2
    })
  }

  // 修正浮点误差，确保总和=1
  const total = values.reduce((s, v) => s + v, 0)
  if (Math.abs(total - 1) > 0.001) {
    values[otherIndices[0]] += 1 - total
  }

  // 限制范围 [0, 1]
  values.forEach((v, i) => {
    values[i] = Math.round(Math.max(0, Math.min(1, v)) * 100) / 100
  })

  emit('update:modelValue', values)
}
</script>

<style scoped>
.presets {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
}
.slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.slider-label {
  width: 70px;
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
}
.slider-value {
  width: 40px;
  text-align: right;
  font-size: 13px;
  color: #303133;
  flex-shrink: 0;
}
</style>
