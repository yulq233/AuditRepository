<template>
  <view class="container">
    <!-- 搜索 -->
    <view class="search-bar">
      <uni-search-bar placeholder="搜索凭证号/摘要" @confirm="onSearch" v-model="keyword" />
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
          <view class="voucher-desc">{{ item.description || '-' }}</view>
        </view>
        <view class="voucher-footer">
          <view class="voucher-amount" :class="{ large: item.amount > 100000 }">
            ¥{{ formatAmount(item.amount) }}
          </view>
          <view class="risk-tag" v-if="item.risk_level" :class="item.risk_level">
            {{ getRiskText(item.risk_level) }}
          </view>
        </view>
      </view>

      <view class="load-more" @click="loadMore" v-if="hasMore && !loading">
        加载更多
      </view>

      <view class="loading-tip" v-if="loading">
        <uni-icons type="spinner-cycle" size="24" color="#409eff"></uni-icons>
        <view>加载中...</view>
      </view>

      <view class="empty-tip" v-if="vouchers.length === 0 && !loading">
        <uni-icons type="info" size="48" color="#c0c4cc"></uni-icons>
        <view>暂无凭证</view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'
import { showToast, formatAmount as formatAmt } from '@/utils/index'
import { voucherApi } from '@/src/api.js'

export default {
  setup() {
    const vouchers = ref([])
    const hasMore = ref(true)
    const page = ref(1)
    const pageSize = 20
    const loading = ref(false)
    const keyword = ref('')
    const projectId = ref(null)

    const formatAmount = (amount) => {
      return formatAmt(amount)
    }

    const getRiskText = (level) => {
      const map = { high: '高', medium: '中', low: '低' }
      return map[level] || ''
    }

    const onSearch = (value) => {
      keyword.value = value.value || ''
      page.value = 1
      vouchers.value = []
      hasMore.value = true
      loadVouchers()
    }

    const loadVouchers = async () => {
      if (!projectId.value) {
        projectId.value = uni.getStorageSync('currentProjectId')
      }

      if (!projectId.value) {
        showToast('请先选择项目')
        return
      }

      loading.value = true
      try {
        const res = await voucherApi.getList(projectId.value, {
          page: page.value,
          page_size: pageSize,
          keyword: keyword.value
        })

        const items = res.items || []
        if (page.value === 1) {
          vouchers.value = items
        } else {
          vouchers.value = [...vouchers.value, ...items]
        }

        hasMore.value = items.length === pageSize
      } catch (e) {
        console.error('加载凭证失败:', e)
        showToast('加载失败')
      } finally {
        loading.value = false
      }
    }

    const loadMore = () => {
      if (!hasMore.value || loading.value) return
      page.value++
      loadVouchers()
    }

    const goDetail = (item) => {
      uni.navigateTo({ url: `/pages/vouchers/detail?id=${item.id}&projectId=${projectId.value}` })
    }

    onMounted(() => {
      loadVouchers()
    })

    return {
      vouchers,
      hasMore,
      loading,
      keyword,
      formatAmount,
      getRiskText,
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.voucher-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.voucher-amount {
  font-size: 32rpx;
  font-weight: bold;
  color: #303133;
}

.voucher-amount.large {
  color: #f56c6c;
}

.risk-tag {
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
}

.risk-tag.high {
  background: #fef0f0;
  color: #f56c6c;
}

.risk-tag.medium {
  background: #fdf6ec;
  color: #e6a23c;
}

.risk-tag.low {
  background: #f0f9eb;
  color: #67c23a;
}

.load-more {
  text-align: center;
  padding: 20rpx;
  color: #409eff;
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
</style>