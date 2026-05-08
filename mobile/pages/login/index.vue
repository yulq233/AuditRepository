<template>
  <view class="login-container">
    <view class="login-header">
      <view class="logo">
        <uni-icons type="bars" size="48" color="#409eff"></uni-icons>
      </view>
      <view class="title">AI审计抽凭助手</view>
      <view class="subtitle">智能抽样 · 风险分析</view>
    </view>

    <view class="login-form">
      <view class="form-item">
        <view class="form-label">用户名</view>
        <input
          class="form-input"
          v-model="form.username"
          placeholder="请输入用户名"
          type="text"
        />
      </view>

      <view class="form-item">
        <view class="form-label">密码</view>
        <input
          class="form-input"
          v-model="form.password"
          placeholder="请输入密码"
          type="password"
        />
      </view>

      <button class="login-btn" @click="handleLogin" :loading="loading">
        登录
      </button>

      <view class="register-link" @click="goRegister">
        还没有账号？立即注册
      </view>
    </view>

    <view class="login-footer">
      <view class="demo-tip">
        演示账号：admin / admin123
      </view>
    </view>
  </view>
</template>

<script>
import { ref, reactive } from 'vue'
import { showToast, showLoading, hideLoading } from '@/utils/index'
import { authApi, setToken } from '@/src/api.js'

export default {
  setup() {
    const loading = ref(false)
    const form = reactive({
      username: '',
      password: ''
    })

    const handleLogin = async () => {
      if (!form.username) {
        showToast('请输入用户名')
        return
      }
      if (!form.password) {
        showToast('请输入密码')
        return
      }

      loading.value = true
      showLoading('登录中...')

      try {
        const res = await authApi.login({
          username: form.username,
          password: form.password
        })

        if (res.access_token) {
          setToken(res.access_token)
          showToast('登录成功')

          // 跳转到首页
          setTimeout(() => {
            uni.switchTab({ url: '/pages/index/index' })
          }, 500)
        }
      } catch (e) {
        console.error('登录失败:', e)
        showToast('登录失败: ' + (e.message || '未知错误'))
      } finally {
        hideLoading()
        loading.value = false
      }
    }

    const goRegister = () => {
      showToast('请联系管理员开通账号')
    }

    return {
      loading,
      form,
      handleLogin,
      goRegister
    }
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  padding: 80rpx 40rpx;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}

.login-header {
  text-align: center;
  margin-bottom: 80rpx;
}

.logo {
  width: 120rpx;
  height: 120rpx;
  background: white;
  border-radius: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24rpx;
}

.title {
  font-size: 40rpx;
  font-weight: bold;
  color: white;
  margin-bottom: 12rpx;
}

.subtitle {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
}

.login-form {
  background: white;
  border-radius: 24rpx;
  padding: 48rpx 32rpx;
  box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.1);
}

.form-item {
  margin-bottom: 32rpx;
}

.form-label {
  font-size: 28rpx;
  color: #303133;
  margin-bottom: 16rpx;
}

.form-input {
  width: 100%;
  height: 88rpx;
  background: #f5f5f5;
  border-radius: 12rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
  box-sizing: border-box;
}

.login-btn {
  width: 100%;
  height: 88rpx;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 12rpx;
  font-size: 32rpx;
  font-weight: bold;
  margin-top: 24rpx;
}

.register-link {
  text-align: center;
  font-size: 26rpx;
  color: #409eff;
  margin-top: 32rpx;
}

.login-footer {
  margin-top: 60rpx;
  text-align: center;
}

.demo-tip {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.7);
}
</style>