<template>
  <v-chart class="convergence-chart" :option="chartOption" autoresize />
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  // 单系列：[[iteration, z], ...]
  data: { type: Array, default: () => [] },
  // 多系列对比模式：{ '改进ACO': [[iter, z], ...], ... }
  multiSeries: { type: Object, default: null }
})

const chartOption = computed(() => {
  const series = []
  const legendData = []

  if (props.multiSeries) {
    // 多算法对比模式
    for (const [name, points] of Object.entries(props.multiSeries)) {
      legendData.push(name)
      series.push({
        name,
        type: 'line',
        smooth: true,
        data: points.map(p => [p[0], p[1]])
      })
    }
  } else if (props.data.length) {
    // 单系列模式
    series.push({
      name: '目标函数 Z',
      type: 'line',
      smooth: true,
      data: props.data.map(p => [p[0], p[1]]),
      areaStyle: { opacity: 0.1 }
    })
    legendData.push('目标函数 Z')
  }

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: legendData },
    grid: { left: 60, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'value', name: '迭代次数' },
    yAxis: { type: 'value', name: '目标函数 Z' },
    series
  }
})
</script>

<style scoped>
.convergence-chart {
  width: 100%;
  height: 300px;
}
</style>
