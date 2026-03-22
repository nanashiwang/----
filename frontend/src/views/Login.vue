<template>
  <div class="login-page">
    <div class="login-bg-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
      <div class="shape shape-3"></div>
    </div>

    <div class="login-card">
      <div class="login-brand">
        <div class="brand-icon">QA</div>
        <h2>QuantAgent</h2>
        <p class="brand-sub">量化交易协同控制台</p>
      </div>

      <div class="mode-switch">
        <button
          type="button"
          class="mode-switch__item"
          :class="{ 'is-active': mode === 'login' }"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          type="button"
          class="mode-switch__item"
          :class="{ 'is-active': mode === 'register' }"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <div class="mode-copy">
        <h3>{{ mode === 'login' ? '欢迎回来' : '创建新账号' }}</h3>
        <p>
          {{
            mode === 'login'
              ? '登录后可继续查看推荐、回测和行情数据。'
              : '注册成功后会自动登录，并直接进入个人中心，方便你修改用户名和密码。'
          }}
        </p>
      </div>

      <el-form
        v-if="mode === 'login'"
        :model="loginForm"
        @submit.prevent="handleLogin"
        label-position="top"
        class="login-form"
      >
        <el-form-item>
          <el-input v-model="loginForm.username" placeholder="请输入用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" size="large" class="login-btn">
          {{ loading ? '登录中...' : '立即登录' }}
        </el-button>
      </el-form>

      <el-form
        v-else
        :model="registerForm"
        @submit.prevent="handleRegister"
        label-position="top"
        class="login-form"
      >
        <el-form-item>
          <el-input v-model="registerForm.username" placeholder="请输入用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请设置密码，至少 6 位"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" size="large" class="login-btn">
          {{ loading ? '注册中...' : '注册并进入系统' }}
        </el-button>
      </el-form>

      <p class="hint">
        {{
          mode === 'login'
            ? '没有账号？点击上方“注册”即可创建普通用户。'
            : '注册后的账号默认为普通用户，如需管理员权限请由管理员在后台授权。'
        }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'

import { login, register as registerUser } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const mode = ref('login')
const loading = ref(false)
const loginForm = ref({ username: '', password: '' })
const registerForm = ref({ username: '', password: '', confirmPassword: '' })

function switchMode(nextMode) {
  mode.value = nextMode
}

function resetRegisterForm() {
  registerForm.value = { username: '', password: '', confirmPassword: '' }
}

async function handleLogin() {
  if (!loginForm.value.username.trim() || !loginForm.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    const res = await login({
      username: loginForm.value.username.trim(),
      password: loginForm.value.password,
    })
    auth.setAuth(res.access_token, res.user)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  const username = registerForm.value.username.trim()
  const password = registerForm.value.password
  const confirmPassword = registerForm.value.confirmPassword

  if (!username) {
    ElMessage.warning('请输入用户名')
    return
  }

  if (!password) {
    ElMessage.warning('请输入密码')
    return
  }

  if (password.length < 6) {
    ElMessage.warning('密码长度不能少于 6 位')
    return
  }

  if (password !== confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  loading.value = true
  try {
    await registerUser({ username, password })
    const loginRes = await login({ username, password })
    auth.setAuth(loginRes.access_token, loginRes.user)
    resetRegisterForm()
    loginForm.value = { username, password: '' }
    ElMessage.success('注册成功，已自动登录')
    router.push('/profile')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  overflow: hidden;
  background: #08121d;
}

.login-bg-shapes {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(88px);
  opacity: 0.46;
  animation: float 20s ease-in-out infinite;
}

.shape-1 {
  top: -120px;
  right: -90px;
  width: 480px;
  height: 480px;
  background: #2a7fff;
}

.shape-2 {
  left: -90px;
  bottom: -80px;
  width: 360px;
  height: 360px;
  background: #17b897;
  animation-delay: -7s;
}

.shape-3 {
  top: 46%;
  left: 48%;
  width: 280px;
  height: 280px;
  background: #f3b356;
  animation-delay: -12s;
}

@keyframes float {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }

  33% {
    transform: translate(28px, -24px) scale(1.04);
  }

  66% {
    transform: translate(-16px, 18px) scale(0.96);
  }
}

.login-card {
  position: relative;
  z-index: 1;
  width: min(460px, calc(100vw - 32px));
  padding: 42px 36px 30px;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 28px 84px rgba(0, 0, 0, 0.36);
  backdrop-filter: blur(26px);
  -webkit-backdrop-filter: blur(26px);
}

.login-brand {
  margin-bottom: 24px;
  text-align: center;
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  margin: 0 auto 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, #2a7fff, #17b897);
  color: #fff;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.login-brand h2 {
  margin: 0 0 6px;
  color: #f9fcff;
  font-size: 26px;
  letter-spacing: -0.03em;
}

.brand-sub {
  margin: 0;
  color: rgba(255, 255, 255, 0.62);
  font-size: 13px;
}

.mode-switch {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 6px;
  margin-bottom: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.06);
}

.mode-switch__item {
  height: 42px;
  border: none;
  border-radius: 14px;
  background: transparent;
  color: rgba(255, 255, 255, 0.72);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-switch__item.is-active {
  background: linear-gradient(135deg, rgba(42, 127, 255, 0.92), rgba(23, 184, 151, 0.88));
  color: #fff;
  box-shadow: 0 12px 24px rgba(23, 184, 151, 0.18);
}

.mode-copy {
  margin-bottom: 20px;
}

.mode-copy h3 {
  margin: 0 0 8px;
  color: #f7fbff;
  font-size: 20px;
}

.mode-copy p {
  margin: 0;
  color: rgba(255, 255, 255, 0.62);
  line-height: 1.7;
  font-size: 13px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.07);
  box-shadow: none !important;
}

.login-form :deep(.el-input__inner) {
  color: #fff;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.34);
}

.login-form :deep(.el-input__prefix .el-icon),
.login-form :deep(.el-input__suffix .el-icon) {
  color: rgba(255, 255, 255, 0.42);
}

.login-btn {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #2a7fff, #17b897);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.02em;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 30px rgba(23, 184, 151, 0.26);
}

.hint {
  margin: 18px 0 0;
  color: rgba(255, 255, 255, 0.42);
  text-align: center;
  font-size: 12px;
  line-height: 1.7;
}
</style>
