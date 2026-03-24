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
            <text>{{ task.sampleCount || 0 }}个样本</text>
          </view>
          <view class="info-item">
            <uni-icons type="calendar" size="16" color="#909399"></uni-icons>
            <text>{{ task.deadline || '无截止日期' }}</text>
          </view>
        </view>
        <view class="task-progress">
          <view class="progress-bar">
            <view class="progress-fill" :style="{ width: task.progress + '%' }"></view>
          </view>
          <view class="progress-text">{{ task.progress }}%</view>
        </view>
      </view>

      <view class="empty-tip" v-if="tasks.length === 0">
        <uni-icons type="info" size="48" color="#c0c4cc"></uni-icons>
        <view>暂无任务</view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'

export default {
  setup() {
    const currentTab = ref('all')

    const stats = reactive({
      pending: 3,
      inProgress: 2,
      completed: 8
    })

    const tasks = ref([])

    const getPriorityText = (priority) => {
      const map = { high: '高', medium: '中', low: '低' }
      return map[priority] || '中'
    }

    const changeTab = (tab) => {
      currentTab.value = tab
      loadTasks()
    }

    const loadTasks = async () => {
      // TODO: 从API加载任务
      tasks.value = [
        {
          id: '1',
          title: '应收账款抽凭任务',
          sampleCount: 25,
          priority: 'high',
          progress: 60,
          deadline: '2024-03-25'
        },
        {
          id: '2',
          title: '存货抽凭任务',
          sampleCount: 18,
          priority: 'medium',
          progress: 30,
          deadline: '2024-03-28'
        },
        {
          id: '3',
          title: '费用科目抽凭任务',
          sampleCount: 32,
          priority: 'low',
          progress: 100,
          deadline: '2024-03-20'
        }
      ]
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
      getPriorityText,
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

.empty-tip {
  text-align: center;
  padding: 80rpx 0;
  color: #c0c4cc;
}
</style>