<template>
  <div class="sidebar-container">
    <div class="sidebar-title">
      <el-icon :size="24"><Van /></el-icon>
      <span>MOURO 智能配送</span>
    </div>
    <el-menu
      :default-active="$route.path"
      router
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409EFF"
    >
      <el-menu-item index="/dashboard">
        <el-icon><HomeFilled /></el-icon>
        <span>首页概览</span>
      </el-menu-item>
      <el-menu-item index="/data">
        <el-icon><FolderOpened /></el-icon>
        <span>数据管理</span>
      </el-menu-item>
      <el-menu-item index="/solve">
        <el-icon><Cpu /></el-icon>
        <span>任务求解</span>
      </el-menu-item>
      <el-menu-item index="/benchmark">
        <el-icon><Histogram /></el-icon>
        <span>性能测试</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup>
</script>

<style scoped>
.sidebar-container {
  height: 100%;
}
.sidebar-title {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.el-menu {
  border-right: none;
}
</style>
