<template>
  <view class="container">
    <!-- 用户信息 -->
    <view class="user-card">
      <view class="avatar">
        <uni-icons type="person" size="48" color="#fff"></uni-icons>
      </view>
      <view class="user-info">
        <view class="username">{{ username }}</view>
        <view class="user-role">审计员</view>
      </view>
    </view>

    <!-- 功能菜单 -->
    <view class="menu-card">
      <view class="menu-item" @click="navigateTo('/pages/paper/index')">
        <uni-icons type="paperclip" size="22" color="#409eff"></uni-icons>
        <view class="menu-text">工作底稿</view>
        <uni-icons type="right" size="16" color="#c0c4cc"></uni-icons>
      </view>
      <view class="menu-item" @click="navigateTo('/pages/risk/index')">
        <uni-icons type="bars" size="22" color="#e6a23c"></uni-icons>
        <view class="menu-text">风险画像</view>
        <uni-icons type="right" size="16" color="#c0c4cc"></uni-icons>
      </view>
      <view class="menu-item" @click="handleLogout">
        <uni-icons type="redo" size="22" color="#f56c6c"></uni-icons>
        <view class="menu-text">退出登录</view>
        <uni-icons type="right" size="16" color="#c0c4cc"></uni-icons>
      </view>
    </view>

    <!-- 关于 -->
    <view class="about-card">
      <view class="about-title">关于</view>
      <view class="about-text">
        AI审计抽凭助手 v1.0.0
      </view>
      <view class="about-text">
        基于大语言模型的智能审计抽样系统
      </view>
    </view>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  setup() {
    const username = ref('用户')

    const navigateTo = (url) => {
      uni.navigateTo({ url })
    }

    const handleLogout = () => {
      uni.showModal({
        title: '提示',
        content: '确定要退出登录吗？',
        success: (res) => {
          if (res.confirm) {
            // 清除登录状态
            uni.removeStorageSync('token')
            uni.removeStorageSync('username')
            // 跳转登录页
            uni.reLaunch({ url: '/pages/login/index' })
          }
        }
      })
    }

    onMounted(() => {
      username.value = uni.getStorageSync('username') || '用户'
    })

    return {
      username,
      navigateTo,
      handleLogout
    }
  }
}
</script>

<style scoped>
.user-card {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  padding: 40rpx;
  border-radius: 16rpx;
  margin-bottom: 20rpx;
}

.avatar {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 24rpx;
}

.username {
  font-size: 36rpx;
  font-weight: bold;
  color: #fff;
}

.user-role {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 8rpx;
}

.menu-card {
  background: #fff;
  border-radius: 16rpx;
  margin-bottom: 20rpx;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 28rpx 24rpx;
  border-bottom: 1px solid #f5f5f5;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-text {
  flex: 1;
  margin-left: 16rpx;
  font-size: 28rpx;
  color: #303133;
}

.about-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
}

.about-title {
  font-size: 28rpx;
  font-weight: bold;
  color: #303133;
  margin-bottom: 16rpx;
}

.about-text {
  font-size: 24rpx;
  color: #909399;
  margin-bottom: 8rpx;
}
</style>