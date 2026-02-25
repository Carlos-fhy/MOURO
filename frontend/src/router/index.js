// 路由配置 + 导航守卫
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { title: '首页概览' }
  },
  {
    path: '/data',
    name: 'DataManage',
    component: () => import('../views/DataManageView.vue'),
    meta: { title: '数据管理' }
  },
  {
    path: '/solve',
    name: 'Solve',
    component: () => import('../views/SolveView.vue'),
    meta: { title: '任务求解' }
  },
  {
    path: '/result',
    name: 'Result',
    component: () => import('../views/ResultView.vue'),
    meta: { title: '决策看板' }
  },
  {
    path: '/compare',
    name: 'Compare',
    component: () => import('../views/CompareView.vue'),
    meta: { title: '算法对比' }
  },
  {
    path: '/benchmark',
    name: 'Benchmark',
    component: () => import('../views/BenchmarkView.vue'),
    meta: { title: '性能测试' }
  },
  {
    path: '/',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path === '/login') {
    // 已登录访问登录页，跳转首页
    token ? next('/dashboard') : next()
  } else if (to.meta.requiresAuth === false) {
    next()
  } else {
    // 未登录跳转登录页
    token ? next() : next('/login')
  }
})

export default router
