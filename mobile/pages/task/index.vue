<template>
  <view class="container">
    <!-- 任务统计 -->
    <view class="stats-container">
      <view class="stat-item">
        <view class="stat-value">{{ stats.pending }}</view>
        <view class="stat-label">待处理</view>
      </view>
      <view class="stat-item">
        <view class="stat-value">{{ stats.inProgress }}</view>
        <view class="stat-label">进行中</view>
      </view>
      <view class="stat-item">
        <view class="stat-value">{{ stats.completed }}</view>
        <view class="stat-label">已完成</view>
      </view>
    </view>

    <!-- 筛选标签 -->
    <view class="filter-tabs">
      <view class="tab-item" :class="{ active: currentTab === 'all' }" @click="changeTab('all')">
        全部
      </view>
      <view class="tab-item" :class="{ active: currentTab === 'pending' }" @click="changeTab('pending')">
        待处理
      </view>
      <view class="tab-item" :class="{ active: currentTab === 'in_progress' }" @click="changeTab('in_progress')">
        进行中
      </view>
      <view class="tab-item" :class="{ active: currentTab === 'completed' }" @click="changeTab('completed')">
        已完成
      </view>
    </view>

    <!-- 任务列表 -->
    <view class="task-list">
      <view class="task-item" v-for="task in tasks" :key="task.id" @click="goTaskDetail(task)">
        <view class="task-header">
          <view class="task-title">{{ task.title || '抽凭任务' }}</view>
          <view class="task-priority" :class="task.priority">
            {{ getPriorityText(task.priority) }}
          </view>
        </view>
        <view class="task-info">
          <view class="info-item">
            <uni-icons type="list" size="16" color="#909399"></uni-icons>
            <text>{{ task.sample_ids?.length || 0 }}个样本</text>
          </view>
          <view class="info-item">
            <uni-icons type="calendar" size="16" color="#909399"></uni-icons>
            <text>{{ task.deadline ? formatDate(task.deadline) : '无截止日期' }}</text>
          </view>
        </view>
        <view class="task-progress">
          <view class="progress-bar">
            <view class="progress-fill" :style="{ width: (task.progress || 0) + '%' }"></view>
          </view>
          <view class="progress-text">{{ task.progress || 0 }}%</view>
        </view>
        <view class="task-status">
          <view :class="['status-badge', task.status]">{{ getStatusText(task.status) }}</view>
        </view>
      </view>

      <view class="loading-tip" v-if="loading">
        <uni-icons type="spinner-cycle" size="24" color="#409eff"></uni-icons>
        <view>加载中...</view>
      </view>

      <view class="empty-tip" v-if="tasks.length === 0 && !loading">
        <uni-icons type="info" size="48" color="#c0c4cc"></uni-icons>
        <view>暂无任务</view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { showToast, formatDate as formatDateUtil } from '@/utils/index'
import { taskApi } from '@/src/api.js'

export default {
  setup() {
    const currentTab = ref('all')

    const stats = reactive({
      pending: 0,
      inProgress: 0,
      completed: 0
    })

    const tasks = ref([])
    const loading = ref(false)
    const projectId = ref(null)

    const getPriorityText = (priority) => {
      const map = { high: '高', medium: '中', low: '低' }
      return map[priority] || '中'
    }

    const getStatusText = (status) => {
      const map = {
        pending: '待处理',
        in_progress: '进行中',
        completed: '已完成',
        review: '待复核'
      }
      return map[status] || status
    }

    const formatDate = (date) => {
      return formatDateUtil(date, 'MM-DD')
    }

    const changeTab = (tab) => {
      currentTab.value = tab
      loadTasks()
    }

    const loadProgress = async () => {
      if (!projectId.value) return

      try {
        const progress = await taskApi.getProgress(projectId.value)
        stats.pending = progress.pending_count || 0
        stats.inProgress = progress.in_progress_count || 0
        stats.completed = progress.completed_count || 0
      } catch (e) {
        console.log('加载进度失败', e)
      }
    }

    const loadTasks = async () => {
      if (!projectId.value) {
        projectId.value = uni.getStorageSync('currentProjectId')
      }

      if (!projectId.value) {
        showToast('请先选择项目')
        return
      }

      loading.value = true
      try {
        const params = {}
        if (currentTab.value !== 'all') {
          params.status = currentTab.value
        }

        const res = await taskApi.getList(projectId.value, params)
        tasks.value = res.items || []

        // 更新统计
        await loadProgress()
      } catch (e) {
        console.error('加载任务失败:', e)
        showToast('加载失败')
      } finally {
        loading.value = false
      }
    }

    const goTaskDetail = (task) => {
      uni.navigateTo({ url: `/pages/task/detail?id=${task.id}` })
    }

    onMounted(() => {
      loadTasks()
    })

    return {
      currentTab,
      stats,
      tasks,
      loading,
      getPriorityText,
      getStatusText,
      formatDate,
      changeTab,
      goTaskDetail
    }
  }
}
</script>

<style scoped>
.stats-container {
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
  font-size: 44rpx;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 24rpx;
  color: #909399;
  margin-top: 8rpx;
}

.filter-tabs {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  padding: 10rpx;
  margin-bottom: 20rpx;
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  font-size: 26rpx;
  color: #606266;
  border-radius: 8rpx;
}

.tab-item.active {
  background: #409eff;
  color: #fff;
}

.task-list {
  margin-top: 20rpx;
}

.task-item {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.task-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #303133;
}

.task-priority {
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
}

.task-priority.high {
  background: #fef0f0;
  color: #f56c6c;
}

.task-priority.medium {
  background: #fdf6ec;
  color: #e6a23c;
}

.task-priority.low {
  background: #f0f9eb;
  color: #67c23a;
}

.task-info {
  display: flex;
  gap: 24rpx;
  margin-bottom: 16rpx;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
  font-size: 24rpx;
  color: #909399;
}

.task-progress {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 12rpx;
}

.progress-bar {
  flex: 1;
  height: 8rpx;
  background: #ebeef5;
  border-radius: 4rpx;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #409eff;
  border-radius: 4rpx;
}

.progress-text {
  font-size: 24rpx;
  color: #909399;
}

.task-status {
  display: flex;
  justify-content: flex-end;
}

.status-badge {
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
}

.status-badge.pending {
  background: #fdf6ec;
  color: #e6a23c;
}

.status-badge.in_progress {
  background: #ecf5ff;
  color: #409eff;
}

.status-badge.completed {
  background: #f0f9eb;
  color: #67c23a;
}

.loading-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx;
  color: #909399;
}

.empty-tip {
  text-align: center;
  padding: 80rpx 0;
  color: #c0c4cc;
}
</style>