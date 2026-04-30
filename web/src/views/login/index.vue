<template>
  <div class="login-container">
    <!-- 动态背景 -->
    <div class="bg-decoration">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
      <div class="bg-circle bg-circle-3"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card animate-scaleIn">
      <!-- Logo 区域 -->
      <div class="login-logo">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h1 class="logo-title">AI审计抽凭助手</h1>
        <p class="logo-subtitle">智能审计 · 高效抽凭 · 精准分析</p>
      </div>

      <!-- 标签切换 -->
      <div class="tab-container">
        <div
          :class="['tab-item', { active: activeTab === 'login' }]"
          @click="activeTab = 'login'"
        >
          登录
        </div>
        <div class="tab-divider"></div>
        <div
          :class="['tab-item', { active: activeTab === 'register' }]"
          @click="activeTab = 'register'"
        >
          注册
        </div>
      </div>

      <!-- 登录表单 -->
      <div v-show="activeTab === 'login'" class="form-container animate-fadeIn">
        <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" @submit.prevent="handleLogin">
          <el-form-item prop="username">
            <div class="input-wrapper">
              <el-icon class="input-icon"><User /></el-icon>
              <el-input v-model="loginForm.username" placeholder="请输入用户名" size="large" />
            </div>
          </el-form-item>
          <el-form-item prop="password">
            <div class="input-wrapper">
              <el-icon class="input-icon"><Lock /></el-icon>
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" show-password />
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" :loading="loading" @click="handleLogin" class="submit-btn">
              <span v-if="!loading">登 录</span>
              <span v-else>登录中...</span>
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 注册表单 -->
      <div v-show="activeTab === 'register'" class="form-container animate-fadeIn">
        <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" @submit.prevent="handleRegister">
          <el-form-item prop="username">
            <div class="input-wrapper">
              <el-icon class="input-icon"><User /></el-icon>
              <el-input v-model="registerForm.username" placeholder="请输入用户名" size="large" />
            </div>
          </el-form-item>
          <el-form-item prop="password">
            <div class="input-wrapper">
              <el-icon class="input-icon"><Lock /></el-icon>
              <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" size="large" show-password />
            </div>
          </el-form-item>
          <el-form-item prop="confirmPassword">
            <div class="input-wrapper">
              <el-icon class="input-icon"><Lock /></el-icon>
              <el-input v-model="registerForm.confirmPassword" type="password" placeholder="请确认密码" size="large" show-password />
            </div>
          </el-form-item>
          <el-form-item prop="fullName">
            <div class="input-wrapper">
              <el-icon class="input-icon"><UserFilled /></el-icon>
              <el-input v-model="registerForm.fullName" placeholder="请输入姓名" size="large" />
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" :loading="loading" @click="handleRegister" class="submit-btn">
              <span v-if="!loading">注 册</span>
              <span v-else>注册中...</span>
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 底部信息 -->
      <div class="login-footer">
        <p>© 2024 AI审计抽凭助手 · 让审计更智能</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, UserFilled } from '@element-plus/icons-vue'
import { authApi } from '@/api'

const router = useRouter()
const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref()
const registerFormRef = ref()

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  fullName: ''
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度3-50个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: (rule, value, callback) => {
      if (value !== registerForm.password) {
        callback(new Error('两次密码不一致'))
      } else {
        callback()
      }
    }, trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await authApi.login(loginForm)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('username', loginForm.username)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  const valid = await registerFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authApi.register({
      username: registerForm.username,
      password: registerForm.password,
      full_name: registerForm.fullName
    })
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    loginForm.username = registerForm.username
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.login-container {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1f36 0%, #2d3561 50%, #1a1f36 100%);
  position: relative;
  overflow: hidden;
}

// 动态背景装饰
.bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
  animation: float 8s ease-in-out infinite;
}

.bg-circle-1 {
  width: 600px;
  height: 600px;
  top: -200px;
  right: -100px;
  animation-delay: 0s;
}

.bg-circle-2 {
  width: 400px;
  height: 400px;
  bottom: -100px;
  left: -100px;
  animation-delay: -2s;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.12) 0%, transparent 70%);
}

.bg-circle-3 {
  width: 300px;
  height: 300px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -4s;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
}

// 登录卡片
.login-card {
  width: 480px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 48px 48px;
  box-shadow:
    0 25px 50px -12px rgba(0, 0, 0, 0.25),
    0 0 0 1px rgba(255, 255, 255, 0.1);
  position: relative;
  z-index: 1;
}

// Logo 区域
.login-logo {
  text-align: center;
  margin-bottom: 36px;
}

.logo-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 16px;
  color: white;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);

  svg {
    width: 32px;
    height: 32px;
  }
}

.logo-title {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.logo-subtitle {
  font-size: 14px;
  color: #6b7280;
  font-weight: 400;
}

// 标签切换
.tab-container {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
  gap: 8px;
}

.tab-item {
  font-size: 20px;
  font-weight: 500;
  color: #9ca3af;
  cursor: pointer;
  padding: 8px 16px;
  transition: all 0.3s ease;
  position: relative;

  &:hover {
    color: #6366f1;
  }

  &.active {
    color: #1f2937;
    font-weight: 600;

    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 24px;
      height: 3px;
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      border-radius: 2px;
    }
  }
}

.tab-divider {
  width: 1px;
  height: 20px;
  background: #e5e7eb;
  margin: 0 8px;
}

// 表单容器
.form-container {
  width: 100%;

  :deep(.el-form-item) {
    margin-bottom: 20px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  :deep(.el-form-item__error) {
    padding-top: 4px;
    font-size: 12px;
  }
}

// 输入框包装
.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;

  :deep(.el-input) {
    flex: 1;
    width: 100%;
  }

  :deep(.el-input__wrapper) {
    padding-left: 44px;
    padding-right: 16px;
    border-radius: 12px;
    background: #f9fafb;
    border: 1px solid transparent;
    box-shadow: none;
    transition: all 0.2s ease;
    height: 48px;
    box-sizing: border-box;

    &:hover {
      background: #fff;
      border-color: #e5e7eb;
    }

    &.is-focus {
      background: #fff;
      border-color: #6366f1;
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
  }

  :deep(.el-input__inner) {
    font-size: 15px;
    width: 100%;

    &::placeholder {
      color: #9ca3af;
    }
  }
}

.input-icon {
  position: absolute;
  left: 14px;
  font-size: 18px;
  color: #9ca3af;
  z-index: 1;
  pointer-events: none;
  transition: color 0.2s ease;
}

.input-wrapper:focus-within .input-icon {
  color: #6366f1;
}

// 提交按钮
.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border: none;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
  }

  &:active {
    transform: translateY(0);
  }
}

// 底部信息
.login-footer {
  margin-top: 32px;
  text-align: center;

  p {
    font-size: 12px;
    color: #9ca3af;
  }
}

// 动画
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

// 响应式
@media screen and (max-width: 480px) {
  .login-card {
    width: calc(100% - 32px);
    padding: 32px 24px;
    margin: 16px;
  }
}
</style>