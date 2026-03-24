<template>
  <view class="container">
    <!-- 搜索 -->
    <view class="search-bar">
      <uni-search-bar placeholder="搜索凭证号/摘要" @confirm="onSearch" />
    </view>

    <!-- 凭证列表 -->
    <view class="voucher-list">
      <view class="voucher-item" v-for="item in vouchers" :key="item.id" @click="goDetail(item)">
        <view class="voucher-header">
          <view class="voucher-no">{{ item.voucher_no }}</view>
          <view class="voucher-date">{{ item.voucher_date }}</view>
        </view>
        <view class="voucher-body">
          <view class="voucher-subject">{{ item.subject_name }}</view>
          <view class="voucher-desc">{{ item.description }}</view>
        </view>
        <view class="voucher-footer">
          <view class="voucher-amount" :class="{ large: item.amount > 100000 }">
            ¥{{ formatAmount(item.amount) }}
          </view>
        </view>
      </view>

      <view class="load-more" @click="loadMore" v-if="hasMore">
        加载更多
      </view>

      <view class="empty-tip" v-if="vouchers.length === 0">
        暂无凭证
      </view>
    </view>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  setup() {
    const vouchers = ref([])
    const hasMore = ref(true)
    const page = ref(1)

    const formatAmount = (amount) => {
      if (!amount) return '0.00'
      return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
    }

    const onSearch = (value) => {
      page.value = 1
      loadVouchers(value)
    }

    const loadVouchers = async (keyword = '') => {
      // TODO: 从API加载
      vouchers.value = [
        { id: '1', voucher_no: '记-001', voucher_date: '2024-03-01', subject_name: '银行存款', description: '收到货款', amount: 50000 },
        { id: '2', voucher_no: '记-002', voucher_date: '2024-03-02', subject_name: '应收账款', description: '销售商品', amount: 120000 },
        { id: '3', voucher_no: '记-003', voucher_date: '2024-03-03', subject_name: '管理费用', description: '办公费', amount: 5000 }
      ]
    }

    const loadMore = () => {
      page.value++
      // TODO: 加载更多
    }

    const goDetail = (item) => {
      uni.navigateTo({ url: `/pages/vouchers/detail?id=${item.id}` })
    }

    onMounted(() => {
      loadVouchers()
    })

    return {
      vouchers,
      hasMore,
      formatAmount,
      onSearch,
      loadMore,
      goDetail
    }
  }
}
</script>

<style scoped>
.search-bar {
  margin-bottom: 20rpx;
}

.voucher-item {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.voucher-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.voucher-no {
  font-size: 30rpx;
  font-weight: bold;
  color: #303133;
}

.voucher-date {
  font-size: 24rpx;
  color: #909399;
}

.voucher-body {
  margin-bottom: 16rpx;
}

.voucher-subject {
  font-size: 26rpx;
  color: #606266;
  margin-bottom: 8rpx;
}

.voucher-desc {
  font-size: 24rpx;
  color: #909399;
}

.voucher-footer {
  display: flex;
  justify-content: flex-end;
}

.voucher-amount {
  font-size: 32rpx;
  font-weight: bold;
  color: #303133;
}

.voucher-amount.large {
  color: #f56c6c;
}

.load-more {
  text-align: center;
  padding: 20rpx;
  color: #409eff;
}

.empty-tip {
  text-align: center;
  padding: 60rpx;
  color: #909399;
}
</style>