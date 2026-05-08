<template>
  <view class="container">
    <!-- 基本信息 -->
    <view class="card">
      <view class="card-header">
        <view class="card-title">凭证信息</view>
        <view :class="['risk-tag', voucher.risk_level]" v-if="voucher.risk_level">
          {{ getRiskText(voucher.risk_level) }}
        </view>
      </view>

      <view class="info-row">
        <view class="info-label">凭证号</view>
        <view class="info-value">{{ voucher.voucher_no }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">凭证日期</view>
        <view class="info-value">{{ voucher.voucher_date }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">金额</view>
        <view class="info-value amount">¥{{ formatAmount(voucher.amount) }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">科目代码</view>
        <view class="info-value">{{ voucher.subject_code || '-' }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">科目名称</view>
        <view class="info-value">{{ voucher.subject_name || '-' }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">摘要</view>
        <view class="info-value">{{ voucher.description || '-' }}</view>
      </view>
      <view class="info-row">
        <view class="info-label">交易对手</view>
        <view class="info-value">{{ voucher.counterparty || '-' }}</view>
      </view>
    </view>

    <!-- 附件列表 -->
    <view class="card" v-if="attachments.length > 0">
      <view class="card-title">附件 ({{ attachments.length }})</view>
      <view class="attachment-list">
        <view class="attachment-item" v-for="item in attachments" :key="item.id" @click="viewAttachment(item)">
          <view class="attachment-icon">
            <uni-icons type="image" size="24" color="#409eff"></uni-icons>
          </view>
          <view class="attachment-info">
            <view class="attachment-name">{{ item.file_name }}</view>
            <view class="attachment-meta">{{ formatFileSize(item.file_size) }}</view>
          </view>
          <view class="attachment-action">
            <uni-icons type="right" size="18" color="#c0c4cc"></uni-icons>
          </view>
        </view>
      </view>
    </view>

    <!-- AI分析结果 -->
    <view class="card" v-if="voucher.ai_analysis">
      <view class="card-title">AI分析</view>
      <view class="ai-content">
        <view class="ai-item" v-if="voucher.ai_analysis.summary">
          <view class="ai-label">摘要分析</view>
          <view class="ai-value">{{ voucher.ai_analysis.summary }}</view>
        </view>
        <view class="ai-item" v-if="voucher.ai_analysis.risk_factors?.length">
          <view class="ai-label">风险因素</view>
          <view class="ai-tags">
            <view class="ai-tag" v-for="(factor, idx) in voucher.ai_analysis.risk_factors" :key="idx">
              {{ factor }}
            </view>
          </view>
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
import { ref, onMounted } from 'vue'
import { showToast, formatAmount as formatAmt } from '@/utils/index'
import { voucherApi } from '@/src/api.js'

export default {
  setup() {
    const voucher = ref({})
    const attachments = ref([])
    const loading = ref(false)
    const voucherId = ref(null)
    const projectId = ref(null)

    const formatAmount = (amount) => {
      return formatAmt(amount)
    }

    const getRiskText = (level) => {
      const map = { high: '高风险', medium: '中风险', low: '低风险' }
      return map[level] || ''
    }

    const formatFileSize = (size) => {
      if (!size) return '-'
      if (size < 1024) return size + ' B'
      if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
      return (size / (1024 * 1024)).toFixed(1) + ' MB'
    }

    const loadData = async () => {
      projectId.value = uni.getStorageSync('currentProjectId')
      if (!projectId.value || !voucherId.value) return

      loading.value = true
      try {
        // 加载凭证详情
        const detail = await voucherApi.getDetail(projectId.value, voucherId.value)
        voucher.value = detail || {}

        // 处理AI分析数据
        if (typeof voucher.value.ai_analysis === 'string') {
          try {
            voucher.value.ai_analysis = JSON.parse(voucher.value.ai_analysis)
          } catch {
            voucher.value.ai_analysis = null
          }
        }

        // 加载附件
        const attachRes = await voucherApi.getAttachments(projectId.value, voucherId.value)
        attachments.value = attachRes || []
      } catch (e) {
        console.error('加载凭证失败:', e)
        showToast('加载失败')
      } finally {
        loading.value = false
      }
    }

    const viewAttachment = (item) => {
      if (item.file_path) {
        // 预览图片
        const baseUrl = 'http://localhost:9000'
        const url = `${baseUrl}/api/files/${item.file_path}`
        uni.previewImage({
          urls: [url],
          current: url
        })
      } else {
        showToast('附件路径无效')
      }
    }

    onMounted(() => {
      const pages = getCurrentPages()
      const currentPage = pages[pages.length - 1]
      voucherId.value = currentPage.options?.id

      loadData()
    })

    return {
      voucher,
      attachments,
      loading,
      formatAmount,
      getRiskText,
      formatFileSize,
      viewAttachment
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

.risk-tag {
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
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
  max-width: 60%;
  text-align: right;
}

.info-value.amount {
  color: #f56c6c;
  font-weight: bold;
}

.attachment-list {
  margin-top: 10rpx;
}

.attachment-item {
  display: flex;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1px solid #f5f5f5;
}

.attachment-item:last-child {
  border-bottom: none;
}

.attachment-icon {
  width: 60rpx;
  height: 60rpx;
  background: #ecf5ff;
  border-radius: 8rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16rpx;
}

.attachment-info {
  flex: 1;
}

.attachment-name {
  font-size: 28rpx;
  color: #303133;
  margin-bottom: 4rpx;
}

.attachment-meta {
  font-size: 24rpx;
  color: #909399;
}

.ai-content {
  background: #f5f5f5;
  border-radius: 12rpx;
  padding: 16rpx;
}

.ai-item {
  margin-bottom: 16rpx;
}

.ai-item:last-child {
  margin-bottom: 0;
}

.ai-label {
  font-size: 26rpx;
  color: #606266;
  margin-bottom: 8rpx;
}

.ai-value {
  font-size: 28rpx;
  color: #303133;
  line-height: 1.6;
}

.ai-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}

.ai-tag {
  padding: 4rpx 12rpx;
  background: #ecf5ff;
  color: #409eff;
  border-radius: 4rpx;
  font-size: 24rpx;
}

.loading-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx;
  color: #909399;
}
</style>