<template>
  <div class="dashboard-container">
    <el-card class="intro-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon :size="24"><Van /></el-icon>
          <span>MOURO 多目标城市配送路径优化系统</span>
        </div>
      </template>
      <p>基于改进蚁群算法，综合考虑经济成本、配送时效与时间窗惩罚，为城市配送场景提供智能路径规划方案。</p>
      <p>支持 Solomon 基准算例与首尔仿真数据，提供多算法对比分析能力。</p>
    </el-card>

    <div class="quick-entry">
      <el-card shadow="hover" class="entry-card" @click="$router.push('/data')">
        <el-icon :size="40" color="#409EFF"><FolderOpened /></el-icon>
        <h3>加载数据</h3>
        <p>选择 Solomon 算例或首尔数据集</p>
      </el-card>
      <el-card shadow="hover" class="entry-card" @click="$router.push('/solve')">
        <el-icon :size="40" color="#67C23A"><Cpu /></el-icon>
        <h3>开始求解</h3>
        <p>配置算法参数，启动智能排线</p>
      </el-card>
      <el-card shadow="hover" class="entry-card" @click="$router.push('/compare')">
        <el-icon :size="40" color="#E6A23C"><TrendCharts /></el-icon>
        <h3>算法对比</h3>
        <p>多算法性能对比分析</p>
      </el-card>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.dashboard-container {
  max-width: 900px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}
.intro-card p {
  color: #606266;
  line-height: 1.8;
  margin: 4px 0;
}
.quick-entry {
  display: flex;
  gap: 20px;
  margin-top: 24px;
}
.entry-card {
  flex: 1;
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s;
}
.entry-card:hover {
  transform: translateY(-4px);
}
.entry-card h3 {
  margin: 12px 0 4px;
  color: #303133;
}
.entry-card p {
  color: #909399;
  font-size: 13px;
  margin: 0;
}
</style>
