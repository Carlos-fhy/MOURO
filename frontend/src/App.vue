<template>
  <!-- 登录页直接渲染，其余页面用布局包裹 -->
  <router-view v-if="$route.path === '/login'" />
  <AppLayout v-else />
</template>

<script setup>
import AppLayout from './components/layout/AppLayout.vue'
</script>

<style>
/* 全局样式重置 */
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', Arial, sans-serif;
}
</style>
