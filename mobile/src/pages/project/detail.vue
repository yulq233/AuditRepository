<template>
  <view class="container">
    <view class="detail-card">
      <view class="detail-row">
        <view class="detail-label">项目名称</view>
        <view class="detail-value">{{ project.name }}</view>
      </view>
      <view class="detail-row">
        <view class="detail-label">项目描述</view>
        <view class="detail-value">{{ project.description || '暂无描述' }}</view>
      </view>
      <view class="detail-row">
        <view class="detail-label">项目状态</view>
        <view class="detail-value">
          <view class="status-tag" :class="project.status">{{ getStatusText(project.status) }}</view>
        </view>
      </view>
    </view>

    <!-- 统计数据 -->
    <view class="stats-card">
      <view class="stat-item">
        <view class="stat-value">{{ stats.voucherCount }}</view>
        <view class="stat-label">凭证数量</view>
      </view>
      <view class="stat-item">
        <view class="stat-value">{{ stats.sampleCount }}</view>
        <view class="stat-label">抽样数量</view>
      </view>
      <view class="stat-item">
        <view class="stat-value">{{ stats.completionRate }}%</view>
        <view class="stat-label">完成进度</view>
      </view>
    </view>

    <!-- 快捷操作 -->
    <view class="action-card">
      <view class="action-btn" @click="navigateTo('/pages/sampling/execute')">
        <uni-icons type="plus" size="20" color="#fff"></uni-icons>
        执行抽样
      </view>
      <view class="action-btn" @click="navigateTo('/pages/risk/index')">
        <uni-icons type="bars" size="20" color="#fff"></uni-icons>
        风险画像
      </view>
      <view class="action-btn" @click="navigateTo('/pages/paper/index')">
        <uni-icons type="paperclip" size="20" color="#fff"></uni-icons>
        工作底稿
      </view>
    </view>
  </view>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'

export default {
  setup() {
    const project = ref({})
    const stats = reactive({
      voucherCount: 0,
      sampleCount: 0,
      completionRate: 0
    })

    const getStatusText = (status) => {
      const map = { active: '进行中', completed: '已完成', archived: '已归档' }
      return map[status] || status
    }

    const navigateTo = (url) => {
      uni.navigateTo({ url })
    }

    const loadProject = async () => {
      // 获取项目ID
      const pages = getCurrentPages()
      const currentPage = pages[pages.length - 1]
      const projectId = currentPage.options?.id

      // TODO: 从API加载
      project.value = {
        id: projectId || '1',
        name: '2024年度审计项目',
        description: '年度财务报表审计项目',
        status: 'active'
      }
      stats.voucherCount = 1250
      stats.sampleCount = 186
      stats.completionRate = 68
    }

    onMounted(() => {
      loadProject()
    })

    return {
      project,
      stats,
      getStatusText,
      navigateTo
    }
  }
}
</script>

<style scoped>
.detail-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.detail-row {
  display: flex;
  padding: 16rpx 0;
  border-bottom: 1px solid #f5f5f5;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  width: 160rpx;
  font-size: 28rpx;
  color: #909399;
}

.detail-value {
  flex: 1;
  font-size: 28rpx;
  color: #303133;
}

.stats-card {
  display: flex;
  justify-content: space-around;
  background: #fff;
  padding: 30rpx 0;
  border-radius: 16rpx;
  margin-bottom: 20rpx;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 40rpx;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 24rpx;
  color: #909399;
  margin-top: 8rpx;
}

.action-card {
  display: flex;
  gap: 20rpx;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  background: #409eff;
  color: #fff;
  padding: 24rpx;
  border-radius: 12rpx;
  font-size: 26rpx;
}
</style>