<template>
  <view class="container">
    <!-- 任务基本信息 -->
    <view class="card">
      <view class="card-title">任务信息</view>
      <view class="info-row">
        <view class="info-label">任务名称</view>
        <view class="info-value">{{ task.title || '抽凭任务' }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">负责人</view>
        <view class="info-value">{{ task.assignee_name || '-' }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">优先级</view>
        <view class="info-value">
          <view :class="['priority-tag', task.priority]">{{ getPriorityText(task.priority) }}</view>
        </view>
      </view>
      <view class="info-row">
        <view class="info-label">状态</view>
        <view class="info-value">
          <view :class="['status-tag', task.status]">{{ getStatusText(task.status) }}</view>
        </view>
      </view>
      <view class="info-row">
        <view class="info-label">截止时间</view>
        <view class="info-value">{{ task.deadline ? formatDate(task.deadline) : '-' }}</view>
      </view>
    </view>

    <!-- 进度信息 -->
    <view class="card">
      <view class="card-title">进度</view>
      <view class="progress-info">
        <view class="progress-bar">
          <view class="progress-fill" :style="{ width: (task.progress || 0) + '%' }"></view>
        </view>
        <view class="progress-text">{{ task.progress || 0 }}%</view>
      </view>
      <view class="sample-count">
        样本数量：{{ task.sample_ids?.length || 0 }} 个
      </view>
    </view>

    <!-- 样本列表 -->
    <view class="card" v-if="samples.length > 0">
      <view class="card-title">样本列表</view>
      <view class="sample-list">
        <view class="sample-item" v-for="item in samples" :key="item.id">
          <view class="sample-no">{{ item.voucher_no }}</view>
          <view class="sample-amount">¥{{ formatAmount(item.amount) }}</view>
        </view>
      </view>
    </view>

    <!-- 操作按钮 -->
    <view class="action-area" v-if="task.status !== 'completed'">
      <button class="btn-primary" @click="updateStatus('in_progress')" v-if="task.status === 'pending'">
        开始处理
      </button>
      <button class="btn-success" @click="updateStatus('completed')" v-if="task.status === 'in_progress'">
        完成任务
      </button>
    </view>

    <view class="loading-tip" v-if="loading">
      <uni-icons type="spinner-cycle" size="24" color="#409eff"></uni-icons>
      <view>加载中...</view>
    </view>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'
import { showToast, formatDate as formatDateUtil, formatAmount as formatAmt } from '@/utils/index'
import { taskApi, samplingApi } from '@/src/api.js'

export default {
  setup() {
    const task = ref({})
    const samples = ref([])
    const loading = ref(false)
    const taskId = ref(null)
    const projectId = ref(null)

    const formatDate = (date) => {
      return formatDateUtil(date, 'YYYY-MM-DD')
    }

    const formatAmount = (amount) => {
      return formatAmt(amount)
    }

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

    const loadData = async () => {
      projectId.value = uni.getStorageSync('currentProjectId')
      if (!projectId.value || !taskId.value) return

      loading.value = true
      try {
        const res = await taskApi.getList(projectId.value, { task_id: taskId.value })
        const tasks = res.items || res || []
        task.value = tasks.find(t => t.id === taskId.value) || {}

        // 加载样本
        if (task.value.sample_ids?.length > 0) {
          const recordDetail = await samplingApi.getRecordDetail(projectId.value, task.value.record_id)
          samples.value = recordDetail.samples?.filter(s => task.value.sample_ids.includes(s.id)) || []
        }
      } catch (e) {
        console.error('加载任务失败:', e)
        showToast('加载失败')
      } finally {
        loading.value = false
      }
    }

    const updateStatus = async (status) => {
      if (!projectId.value || !taskId.value) return

      try {
        await taskApi.updateStatus(projectId.value, taskId.value, { status })
        showToast('状态已更新')
        task.value.status = status
        if (status === 'completed') {
          task.value.progress = 100
        }
      } catch (e) {
        showToast('更新失败')
      }
    }

    onMounted(() => {
      const pages = getCurrentPages()
      const currentPage = pages[pages.length - 1]
      taskId.value = currentPage.options?.id

      loadData()
    })

    return {
      task,
      samples,
      loading,
      formatDate,
      formatAmount,
      getPriorityText,
      getStatusText,
      updateStatus
    }
  }
}
</script>

<style scoped>
.container {
  padding: 20rpx;
}

.card {
  background: white;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.card-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #303133;
  margin-bottom: 20rpx;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 12rpx 0;
  border-bottom: 1px solid #f5f5f5;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 28rpx;
  color: #909399;
}

.info-value {
  font-size: 28rpx;
  color: #303133;
}

.priority-tag {
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
}

.priority-tag.high {
  background: #fef0f0;
  color: #f56c6c;
}

.priority-tag.medium {
  background: #fdf6ec;
  color: #e6a23c;
}

.priority-tag.low {
  background: #f0f9eb;
  color: #67c23a;
}

.status-tag {
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
}

.status-tag.pending {
  background: #fdf6ec;
  color: #e6a23c;
}

.status-tag.in_progress {
  background: #ecf5ff;
  color: #409eff;
}

.status-tag.completed {
  background: #f0f9eb;
  color: #67c23a;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

.progress-bar {
  flex: 1;
  height: 16rpx;
  background: #ebeef5;
  border-radius: 8rpx;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #409eff;
  border-radius: 8rpx;
}

.progress-text {
  font-size: 28rpx;
  color: #409eff;
  font-weight: bold;
}

.sample-count {
  font-size: 26rpx;
  color: #606266;
}

.sample-list {
  margin-top: 10rpx;
}

.sample-item {
  display: flex;
  justify-content: space-between;
  padding: 16rpx 0;
  border-bottom: 1px solid #f5f5f5;
}

.sample-item:last-child {
  border-bottom: none;
}

.sample-no {
  font-size: 28rpx;
  color: #303133;
}

.sample-amount {
  font-size: 28rpx;
  color: #f56c6c;
  font-weight: bold;
}

.action-area {
  padding: 20rpx 0;
}

.btn-primary, .btn-success {
  width: 100%;
  height: 88rpx;
  border: none;
  border-radius: 12rpx;
  font-size: 32rpx;
  font-weight: bold;
  color: white;
}

.btn-primary {
  background: #409eff;
}

.btn-success {
  background: #67c23a;
}

.loading-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx;
  color: #909399;
}
</style>