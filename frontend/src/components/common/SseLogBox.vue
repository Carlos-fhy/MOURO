<template>
  <div class="sse-log-box" ref="logBox">
    <div v-for="(log, idx) in logs" :key="idx" class="log-line">
      {{ formatLog(log) }}
    </div>
    <div v-if="!logs.length" class="log-empty">等待算法启动...</div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  logs: { type: Array, default: () => [] }
})

const logBox = ref(null)

// 日志更新时自动滚动到底部
watch(() => props.logs.length, () => {
  nextTick(() => {
    if (logBox.value) {
      logBox.value.scrollTop = logBox.value.scrollHeight
    }
  })
})

// 格式化日志消息
function formatLog(log) {
  if (typeof log === 'string') return log
  if (log.type === 'status') {
    if (log.phase === 'construct') {
      return `[迭代 ${log.iteration}] 构解进度 ${log.done}/${log.total}`
    }
    if (log.phase === 'local_search') {
      return `[迭代 ${log.iteration}] 局部搜索 ${log.done === 0 ? '开始' : '完成'}`
    }
    return `[迭代 ${log.iteration}] ${log.phase ?? '阶段'} ${log.done ?? '-'} / ${log.total ?? '-'}`
  }
  if (log.type === 'progress') {
    return `[迭代 ${log.iteration}] Z=${log.best_z?.toFixed(4) ?? '-'} F1=${log.best_f1?.toFixed(1) ?? '-'} F2'=${log.best_f2?.toFixed(1) ?? '-'} F3=${log.best_f3?.toFixed(1) ?? '-'} 车辆=${log.vehicles_used ?? '-'}`
  }
  if (log.type === 'done') {
    return `✓ 求解完成，共 ${log.total_iterations} 轮迭代${log.early_stopped ? '（早停）' : ''}`
  }
  if (log.type === 'error') {
    return `✗ 错误：${log.message}`
  }
  // 对比模式的进度
  if (log.algorithm) {
    return `[${log.algorithm}] 迭代 ${log.iteration} Z=${log.best_z?.toFixed(4) ?? '-'}`
  }
  return JSON.stringify(log)
}
</script>

<style scoped>
.sse-log-box {
  background-color: #1e1e1e;
  color: #67C23A;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 12px;
  height: 300px;
  overflow-y: auto;
  border-radius: 4px;
}
.log-line {
  white-space: pre-wrap;
  word-break: break-all;
}
.log-empty {
  color: #909399;
}
</style>
