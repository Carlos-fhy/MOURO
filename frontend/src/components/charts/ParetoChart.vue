<template>
  <v-chart class="pareto-chart" :option="chartOption" autoresize />
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([ScatterChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  // 历史方案点：[{ f1, f2 }, ...]
  points: { type: Array, default: () => [] },
  // 当前方案
  currentF1: { type: Number, default: null },
  currentF2: { type: Number, default: null }
})

const chartOption = computed(() => {
  const series = []

  // 历史方案散点
  if (props.points.length) {
    series.push({
      name: '历史方案',
      type: 'scatter',
      symbolSize: 10,
      data: props.points.map(p => [p.f1, p.f2]),
      itemStyle: { color: '#409EFF' }
    })
  }

  // 当前方案红点高亮
  if (props.currentF1 !== null && props.currentF2 !== null) {
    series.push({
      name: '当前方案',
      type: 'scatter',
      symbolSize: 16,
      data: [[props.currentF1, props.currentF2]],
      itemStyle: { color: '#F56C6C' }
    })
  }

  return {
    tooltip: {
      trigger: 'item',
      formatter: p => `F1: ${p.data[0].toFixed(2)}<br/>F2': ${p.data[1].toFixed(2)}`
    },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'value', name: '总成本 F1' },
    yAxis: { type: 'value', name: "加权时间 F2'" },
    series
  }
})
</script>

<style scoped>
.pareto-chart {
  width: 100%;
  height: 300px;
}
</style>
