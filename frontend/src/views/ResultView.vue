<template>
  <div class="result-view">
    <!-- 不可达客户告警 -->
    <el-alert
      v-if="resultStore.unreachable.length"
      :title="`存在 ${resultStore.unreachable.length} 个不可达客户`"
      type="error"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <!-- KPI 卡片行 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6">
        <KpiCard icon="Money" label="总成本 F1" :value="resultStore.f1" color="#409EFF" />
      </el-col>
      <el-col :span="6">
        <KpiCard icon="Timer" label="加权时间 F2'" :value="resultStore.f2" color="#E6A23C" />
      </el-col>
      <el-col :span="6">
        <KpiCard icon="WarningFilled" label="惩罚成本 F3" :value="resultStore.f3" color="#F56C6C" />
      </el-col>
      <el-col :span="6">
        <KpiCard icon="Van" label="车辆使用数" :value="resultStore.vehiclesUsed" color="#67C23A" />
      </el-col>
    </el-row>

    <!-- 地图 + 收敛曲线 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>路线地图</template>
          <RouteMap
            :depot="dataStore.depot"
            :customers="dataStore.customers"
            :routes="resultStore.routes"
            :schedule="resultStore.schedule"
            :coord-mode="dataStore.mode"
            mode="route"
          />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover" style="margin-bottom: 16px">
          <template #header>收敛曲线</template>
          <ConvergenceChart :data="resultStore.convergence" />
        </el-card>
        <el-card shadow="hover">
          <template #header>Pareto 散点图</template>
          <ParetoChart
            :current-f1="resultStore.f1"
            :current-f2="resultStore.f2"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 调度明细表 -->
    <el-card shadow="hover" style="margin-top: 16px">
      <template #header>调度明细</template>
      <ScheduleTable :schedule="resultStore.schedule" />
    </el-card>

    <!-- 无数据提示 -->
    <el-empty
      v-if="!resultStore.routes.length"
      description="暂无求解结果，请先在任务求解页运行算法"
    />
  </div>
</template>

<script setup>
import { useDataStore } from '../stores/data'
import { useResultStore } from '../stores/result'
import KpiCard from '../components/common/KpiCard.vue'
import RouteMap from '../components/map/RouteMap.vue'
import ConvergenceChart from '../components/charts/ConvergenceChart.vue'
import ParetoChart from '../components/charts/ParetoChart.vue'
import ScheduleTable from '../components/common/ScheduleTable.vue'

const dataStore = useDataStore()
const resultStore = useResultStore()
</script>

<style scoped>
.kpi-row {
  margin-bottom: 0;
}
</style>
