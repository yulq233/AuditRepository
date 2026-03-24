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
    </view>

    <!-- 样本列表 -->
    <view class="sample-list">
      <view class="sample-item" v-for="item in samples" :key="item.id">
        <view class="sample-header">
          <view class="sample-no">{{ item.voucher_no }}</view>
          <view class="sample-amount">¥{{ formatAmount(item.amount) }}</view>
        </view>
        <view class="sample-body">
          <view class="sample-subject">{{ item.subject_name }}</view>
          <view class="sample-desc">{{ item.description }}</view>
        </view>
        <view class="sample-footer">
          <view class="sample-reason">{{ item.reason }}</view>
        </view>
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

export default {
  setup() {
    const total = ref(0)
    const reviewed = ref(0)
    const samples = ref([])

    const formatAmount = (amount) => {
      if (!amount) return '0.00'
      return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
    }

    const exportResults = () => {
      uni.showToast({ title: '导出功能开发中', icon: 'none' })
    }

    const loadData = async () => {
      // TODO: 从API加载
      samples.value = [
        { id: '1', voucher_no: '记-015', subject_name: '应收账款', amount: 150000, description: '销售商品', reason: '金额抽样' },
        { id: '2', voucher_no: '记-028', subject_name: '应付账款', amount: 89000, description: '采购付款', reason: '金额抽样' },
        { id: '3', voucher_no: '记-042', subject_name: '银行存款', amount: 200000, description: '收到货款', reason: '金额抽样' }
      ]
      total.value = samples.value.length
      reviewed.value = 1
    }

    onMounted(() => {
      loadData()
    })

    return {
      total,
      reviewed,
      samples,
      formatAmount,
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
}

.sample-reason {
  font-size: 22rpx;
  color: #909399;
  background: #f5f5f5;
  padding: 8rpx 16rpx;
  border-radius: 8rpx;
  display: inline-block;
}

.action-area {
  padding: 20rpx 0;
}
</style>