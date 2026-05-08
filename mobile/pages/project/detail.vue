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
      <view class="detail-row">
        <view class="detail-label">创建时间</view>
        <view class="detail-value">{{ formatDate(project.created_at) }}</view>
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

    <!-- 最近抽样记录 -->
    <view class="card">
      <view class="card-header">
        <view class="card-title">最近抽样</view>
        <view class="card-more" @click="navigateTo('/pages/sampling/result')">查看全部</view>
      </view>
      <view class="record-list">
        <view class="record-item" v-for="item in recentRecords" :key="item.id" @click="goRecord(item)">
          <view class="record-info">
            <view class="record-name">{{ item.rule_name || '抽样任务' }}</view>
            <view class="record-time">{{ formatDate(item.created_at) }}</view>
          </view>
          <view class="record-stats">
            <text>{{ item.sample_size }}个样本</text>
          </view>
        </view>
        <view class="empty-tip" v-if="recentRecords.length === 0">
          暂无抽样记录
        </view>
      </view>
    </view>

    <view class="loading-tip" v-if="loading">
      <uni-icons type="spinner-cycle" size="24" color="#409eff"></uni-icons>
      <view>加载中...</view>
    </view>
  </view>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { showToast, formatDate as formatDateUtil } from '@/utils/index'
import { projectApi, voucherApi, samplingApi, taskApi } from '@/src/api.js'

export default {
  setup() {
    const project = ref({})
    const stats = reactive({
      voucherCount: 0,
      sampleCount: 0,
      completionRate: 0
    })
    const recentRecords = ref([])
    const loading = ref(false)
    const projectId = ref(null)

    const getStatusText = (status) => {
      const map = { active: '进行中', completed: '已完成', archived: '已归档' }
      return map[status] || status
    }

    const formatDate = (date) => {
      return formatDateUtil(date, 'YYYY-MM-DD')
    }

    const navigateTo = (url) => {
      uni.navigateTo({ url })
    }

    const goRecord = (item) => {
      uni.navigateTo({ url: `/pages/sampling/result?id=${item.id}` })
    }

    const loadData = async () => {
      // 获取项目ID
      const pages = getCurrentPages()
      const currentPage = pages[pages.length - 1]
      projectId.value = currentPage.options?.id

      if (!projectId.value) {
        projectId.value = uni.getStorageSync('currentProjectId')
      }

      if (!projectId.value) {
        showToast('项目不存在')
        return
      }

      // 保存当前项目ID
      uni.setStorageSync('currentProjectId', projectId.value)

      loading.value = true
      try {
        // 加载项目详情
        const projectData = await projectApi.getDetail(projectId.value)
        project.value = projectData || {}

        // 加载凭证统计
        try {
          const voucherStats = await voucherApi.getPopulationStats(projectId.value)
          stats.voucherCount = voucherStats.total_count || 0
        } catch (e) {
          console.log('加载凭证统计失败', e)
        }

        // 加载任务进度
        try {
          const progress = await taskApi.getProgress(projectId.value)
          stats.sampleCount = progress.total_samples || 0
          stats.completionRate = progress.completion_rate || 0
        } catch (e) {
          console.log('加载任务进度失败', e)
        }

        // 加载最近抽样记录
        try {
          const records = await samplingApi.getRecords(projectId.value)
          recentRecords.value = (records.items || records || []).slice(0, 5)
        } catch (e) {
          console.log('加载抽样记录失败', e)
        }
      } catch (e) {
        console.error('加载项目失败:', e)
        showToast('加载失败')
      } finally {
        loading.value = false
      }
    }

    onMounted(() => {
      loadData()
    })

    return {
      project,
      stats,
      recentRecords,
      loading,
      getStatusText,
      formatDate,
      navigateTo,
      goRecord
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

.status-tag {
  display: inline-block;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
}

.status-tag.active {
  background: #f0f9eb;
  color: #67c23a;
}

.status-tag.completed {
  background: #ecf5ff;
  color: #409eff;
}

.status-tag.archived {
  background: #f4f4f5;
  color: #909399;
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
  margin-bottom: 20rpx;
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

.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.card-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #303133;
}

.card-more {
  font-size: 24rpx;
  color: #409eff;
}

.record-list {
  margin-top: 10rpx;
}

.record-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1px solid #f5f5f5;
}

.record-item:last-child {
  border-bottom: none;
}

.record-name {
  font-size: 28rpx;
  color: #303133;
}

.record-time {
  font-size: 24rpx;
  color: #909399;
  margin-top: 4rpx;
}

.record-stats {
  font-size: 24rpx;
  color: #409eff;
}

.empty-tip {
  text-align: center;
  padding: 30rpx;
  color: #909399;
  font-size: 26rpx;
}

.loading-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60rpx;
  color: #909399;
}
</style>