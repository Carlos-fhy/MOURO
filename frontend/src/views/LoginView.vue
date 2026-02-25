<template>
  <div class="login-page">
    <!-- 左侧品牌区 -->
    <div class="login-brand">
      <div class="brand-content">
        <div class="brand-logo">
          <svg viewBox="0 0 48 48" width="42" height="42" fill="none">
            <path d="M24 4L6 14v20l18 10 18-10V14L24 4z" stroke="#fff" stroke-width="2" fill="none"/>
            <path d="M24 4v40M6 14l18 10 18-10M6 34l18-10 18 10" stroke="#fff" stroke-width="1.5" opacity=".4"/>
            <circle cx="24" cy="24" r="4" fill="#fff" opacity=".9"/>
          </svg>
          <span class="brand-name">MOURO</span>
        </div>
        <h1 class="brand-title">城市配送路径优化系统</h1>
        <p class="brand-desc">
          基于改进蚁群算法的多目标车辆路径规划，<br/>
          兼顾经济成本、配送时效与应急响应。
        </p>
        <div class="brand-tags">
          <span>多目标优化</span>
          <span>应急分级</span>
          <span>智能调度</span>
        </div>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="login-form-side">
      <div class="form-wrapper">
        <h2 class="form-title">登录</h2>
        <p class="form-subtitle">请输入管理员账号以继续</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="0"
          size="large"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="用户名"
              :prefix-icon="User"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="login-btn"
              @click="handleLogin"
            >
              登 录
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)

const form = ref({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await login(form.value.username, form.value.password)
    if (res.success) {
      authStore.setToken(res.data.token)
      ElMessage.success('登录成功')
      router.push('/dashboard')
    } else {
      ElMessage.error(res.message || '登录失败')
    }
  } catch {
    // 错误已由响应拦截器处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
}

/* 左侧品牌区 */
.login-brand {
  flex: 1;
  background: #1a1f2e;
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 60px;
  position: relative;
}
.brand-content {
  max-width: 380px;
}
.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 36px;
}
.brand-name {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 3px;
}
.brand-title {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.4;
  margin: 0 0 16px;
}
.brand-desc {
  font-size: 14px;
  line-height: 1.8;
  color: rgba(255, 255, 255, .55);
  margin: 0 0 32px;
}
.brand-tags {
  display: flex;
  gap: 10px;
}
.brand-tags span {
  padding: 4px 14px;
  border: 1px solid rgba(255, 255, 255, .18);
  border-radius: 20px;
  font-size: 12px;
  color: rgba(255, 255, 255, .6);
}
.brand-footer {
  position: absolute;
  bottom: 32px;
  font-size: 12px;
  color: rgba(255, 255, 255, .3);
  margin: 0;
}

/* 右侧表单区 */
.login-form-side {
  width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}
.form-wrapper {
  width: 320px;
}
.form-title {
  font-size: 24px;
  font-weight: 600;
  color: #1d2129;
  margin: 0 0 8px;
}
.form-subtitle {
  font-size: 13px;
  color: #86909c;
  margin: 0 0 36px;
}
.login-btn {
  width: 100%;
  margin-top: 8px;
}
</style>
