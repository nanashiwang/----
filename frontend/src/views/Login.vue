<template>
  <div class="login-page">
    <div class="login-bg-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
      <div class="shape shape-3"></div>
    </div>
    <div class="login-card">
      <div class="login-brand">
        <div class="brand-icon">Q</div>
        <h2>QuantAgent</h2>
        <p class="brand-sub">Multi-Agent Quantitative Trading Platform</p>
      </div>
      <el-form :model="form" @submit.prevent="handleLogin" label-position="top" class="login-form">
        <el-form-item>
          <el-input v-model="form.username" placeholder="Username" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="Password" size="large" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" size="large" class="login-btn">
          {{ loading ? '...' : 'Sign In' }}
        </el-button>
      </el-form>
      <p class="hint">Configure INIT_ADMIN_USERNAME / INIT_ADMIN_PASSWORD env vars for first run</p>
    </div>
  </div>
</template>

<script setup>
import { ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { login } from '../api/auth'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = ref({ username: '', password: '' })

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('Please enter username and password')
    return
  }
  loading.value = true
  try {
    const res = await login(form.value)
    auth.setAuth(res.access_token, res.user)
    ElMessage.success('Welcome back!')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Login failed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex; justify-content: center; align-items: center;
  height: 100vh; position: relative; overflow: hidden;
  background: #0f0f1a;
}
.login-bg-shapes { position: absolute; inset: 0; z-index: 0; }
.shape {
  position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4;
  animation: float 20s ease-in-out infinite;
}
.shape-1 { width: 500px; height: 500px; background: #6366f1; top: -100px; right: -100px; }
.shape-2 { width: 400px; height: 400px; background: #ec4899; bottom: -50px; left: -100px; animation-delay: -7s; }
.shape-3 { width: 300px; height: 300px; background: #06b6d4; top: 50%; left: 50%; animation-delay: -14s; }

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

.login-card {
  position: relative; z-index: 1;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 48px 40px; border-radius: 24px; width: 420px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5);
}
.login-brand { text-align: center; margin-bottom: 36px; }
.brand-icon {
  width: 56px; height: 56px; border-radius: 16px; margin: 0 auto 16px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 800; color: #fff;
}
.login-brand h2 { color: #fff; font-size: 24px; margin: 0 0 4px; letter-spacing: -0.5px; }
.brand-sub { color: rgba(255, 255, 255, 0.45); font-size: 13px; margin: 0; }

.login-form :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px; box-shadow: none !important;
}
.login-form :deep(.el-input__inner) { color: #fff; }
.login-form :deep(.el-input__inner::placeholder) { color: rgba(255, 255, 255, 0.35); }
.login-form :deep(.el-input__prefix .el-icon) { color: rgba(255, 255, 255, 0.4); }

.login-btn {
  width: 100%; border-radius: 12px; font-size: 15px; font-weight: 600; letter-spacing: 0.5px;
  background: linear-gradient(135deg, #6366f1, #a855f7); border: none; height: 48px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.login-btn:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4); }

.hint { text-align: center; color: rgba(255, 255, 255, 0.3); font-size: 11px; margin-top: 20px; }
</style>
