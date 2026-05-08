<template>
  <view class="container">
    <!-- 统计 -->
    <view class="stats-card">
      <view class="stat-item">
        <view class="stat-value">{{ total }}</view>
        <view class="stat-label">样本总数</view>
      </view>
      <view class="stat-item">
        <view class="stat-value">{{ reviewed }}</view>
        <view class="stat-label">已复核</view>
      </view>
      <view class="stat-item">
        <view class="stat-value">{{ highRisk }}</view>
        <view class="stat-label">高风险</view>
      </view>
    </view>

    <!-- 样本列表 -->
    <view class="sample-list">
      <view class="sample-item" v-for="item in samples" :key="item.id">
        <view class="sample-header">
          <view class="sample-no">{{ item.voucher_no }}</view>
          <view class="sample-amount" :class="{ large: item.amount > 100000 }">
            ¥{{ formatAmount(item.amount) }}
          </view>
        </view>
        <view class="sample-body">
          <view class="sample-subject">{{ item.subject_name || '-' }}</view>
          <view class="sample-desc">{{ item.description || '-' }}</view>
        </view>
        <view class="sample-footer">
          <view class="sample-reason" v-if="item.reason">{{ item.reason }}</view>
          <view class="risk-badge" v-if="item.risk_level" :class="item.risk_level">
            {{ getRiskText(item.risk_level) }}
          </view>
        </view>
      </view>

      <view class="loading-tip" v-if="loading">
        <uni-icons type="spinner-cycle" size="24" color="#409eff"></uni-icons>
        <view>加载中...</view>
      </view>

      <view class="empty-tip" v-if="samples.length === 0 && !loading">
        <uni-icons type="info" size="48" color="#c0c4cc"></uni-icons>
        <view>暂无样本数据</view>
      </view>
    </view>

    <!-- 导出按钮 -->
    <view class="action-area">
      <button type="primary" @click="exportResults">导出结果</button>
    </view>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'
import { showToast, formatAmount as formatAmt } from '@/utils/index'
import { samplingApi } from '@/src/api.js'

export default {
  setup() {
    const total = ref(0)
    const reviewed = ref(0)
    const highRisk = ref(0)
    const samples = ref([])
    const loading = ref(false)
    const recordId = ref(null)
    const projectId = ref(null)

    const formatAmount = (amount) => {
      return formatAmt(amount)
    }

    const getRiskText = (level) => {
      const map = { high: '高风险', medium: '中风险', low: '低风险' }
      return map[level] || ''
    }

    const loadData = async () => {
      if (!projectId.value) {
        projectId.value = uni.getStorageSync('currentProjectId')
      }

      if (!projectId.value) {
        showToast('请先选择项目')
        return
      }

      loading.value = true
      try {
        let recordData

        if (recordId.value) {
          // 加载指定记录
          recordData = await samplingApi.getRecordDetail(projectId.value, recordId.value)
        } else {
          // 加载最新记录
          const records = await samplingApi.getRecords(projectId.value)
          const items = records.items || records || []
          if (items.length > 0) {
            recordId.value = items[0].id
            recordData = await samplingApi.getRecordDetail(projectId.value, recordId.value)
          }
        }

        if (recordData) {
          samples.value = recordData.samples || []
          total.value = recordData.sample_size || samples.value.length
          reviewed.value = samples.value.filter(s => s.test_status === 'completed').length
          highRisk.value = samples.value.filter(s => s.risk_level === 'high').length
        }
      } catch (e) {
        console.error('加载数据失败:', e)
        showToast('加载失败')
      } finally {
        loading.value = false
      }
    }

    const exportResults = async () => {
      if (!projectId.value || !recordId.value) {
        showToast('暂无数据可导出')
        return
      }

      showToast('导出功能开发中')
    }

    onMounted(() => {
      // 获取URL参数
      const pages = getCurrentPages()
      const currentPage = pages[pages.length - 1]
      const options = currentPage.options || {}
      recordId.value = options.id

      loadData()
    })

    return {
      total,
      reviewed,
      highRisk,
      samples,
      loading,
      formatAmount,
      getRiskText,
      exportResults
    }
  }
}
</script>

<style scoped>
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
  font-size: 44rpx;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 24rpx;
  color: #909399;
  margin-top: 8rpx;
}

.sample-item {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.sample-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}

.sample-no {
  font-size: 30rpx;
  font-weight: bold;
  color: #303133;
}

.sample-amount {
  font-size: 30rpx;
  font-weight: bold;
  color: #303133;
}

.sample-amount.large {
  color: #f56c6c;
}

.sample-subject {
  font-size: 26rpx;
  color: #606266;
  margin-bottom: 8rpx;
}

.sample-desc {
  font-size: 24rpx;
  color: #909399;
  margin-bottom: 12rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sample-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sample-reason {
  font-size: 22rpx;
  color: #909399;
  background: #f5f5f5;
  padding: 8rpx 16rpx;
  border-radius: 8rpx;
}

.risk-badge {
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
}

.risk-badge.high {
  background: #fef0f0;
  color: #f56c6c;
}

.risk-badge.medium {
  background: #fdf6ec;
  color: #e6a23c;
}

.risk-badge.low {
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
  padding: 60rpx;
  color: #909399;
}

.action-area {
  padding: 20rpx 0;
}
</style>