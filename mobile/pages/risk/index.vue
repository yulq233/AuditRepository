<template>
  <view class="container">
    <!-- 风险分布图 -->
    <view class="chart-card">
      <view class="card-title">风险等级分布</view>
      <view class="risk-summary">
        <view class="risk-item">
          <view class="risk-dot high"></view>
          <view class="risk-text">高风险 {{ riskStats.high }}个</view>
        </view>
        <view class="risk-item">
          <view class="risk-dot medium"></view>
          <view class="risk-text">中风险 {{ riskStats.medium }}个</view>
        </view>
        <view class="risk-item">
          <view class="risk-dot low"></view>
          <view class="risk-text">低风险 {{ riskStats.low }}个</view>
        </view>
      </view>
    </view>

    <!-- 科目风险列表 -->
    <view class="list-card">
      <view class="card-title">科目风险画像</view>
      <view class="profile-list">
        <view class="profile-item" v-for="item in profiles" :key="item.id">
          <view class="profile-header">
            <view class="subject-info">
              <view class="subject-code">{{ item.subject_code }}</view>
              <view class="subject-name">{{ item.subject_name }}</view>
            </view>
            <view class="risk-tag" :class="item.risk_level">
              {{ getRiskText(item.risk_level) }}
            </view>
          </view>
          <view class="profile-score">
            <view class="score-bar">
              <view class="score-fill" :style="{ width: item.risk_score + '%', background: getRiskColor(item.risk_level) }"></view>
            </view>
            <view class="score-value">{{ item.risk_score?.toFixed(1) }}</view>
          </view>
          <view class="profile-factors">
            <view class="factor-tag" v-for="(factor, idx) in (item.risk_factors || []).slice(0, 3)" :key="idx">
              {{ factor.name }}
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'

export default {
  setup() {
    const riskStats = reactive({ high: 0, medium: 0, low: 0 })
    const profiles = ref([])

    const getRiskText = (level) => {
      const map = { high: '高风险', medium: '中风险', low: '低风险' }
      return map[level] || level
    }

    const getRiskColor = (level) => {
      const map = { high: '#f56c6c', medium: '#e6a23c', low: '#67c23a' }
      return map[level] || '#909399'
    }

    const loadData = async () => {
      // TODO: 从API加载
      profiles.value = [
        { id: '1', subject_code: '1122', subject_name: '应收账款', risk_level: 'high', risk_score: 78.5, risk_factors: [{ name: '金额重要性' }, { name: '业务复杂' }] },
        { id: '2', subject_code: '1405', subject_name: '库存商品', risk_level: 'medium', risk_score: 52.3, risk_factors: [{ name: '金额重要性' }] },
        { id: '3', subject_code: '2202', subject_name: '应付账款', risk_level: 'medium', risk_score: 48.7, risk_factors: [{ name: '业务复杂' }] }
      ]

      profiles.value.forEach(p => {
        riskStats[p.risk_level]++
      })
    }

    onMounted(() => {
      loadData()
    })

    return {
      riskStats,
      profiles,
      getRiskText,
      getRiskColor
    }
  }
}
</script>

<style scoped>
.chart-card {
  background: #fff;
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

.risk-summary {
  display: flex;
  justify-content: space-around;
}

.risk-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.risk-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
}

.risk-dot.high { background: #f56c6c; }
.risk-dot.medium { background: #e6a23c; }
.risk-dot.low { background: #67c23a; }

.risk-text {
  font-size: 24rpx;
  color: #606266;
}

.list-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
}

.profile-item {
  padding: 20rpx 0;
  border-bottom: 1px solid #f5f5f5;
}

.profile-item:last-child {
  border-bottom: none;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}

.subject-code {
  font-size: 24rpx;
  color: #909399;
}

.subject-name {
  font-size: 28rpx;
  color: #303133;
  margin-top: 4rpx;
}

.profile-score {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 12rpx;
}

.score-bar {
  flex: 1;
  height: 12rpx;
  background: #f5f5f5;
  border-radius: 6rpx;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 6rpx;
}

.score-value {
  font-size: 24rpx;
  color: #909399;
}

.profile-factors {
  display: flex;
  gap: 8rpx;
}

.factor-tag {
  padding: 4rpx 12rpx;
  background: #f5f5f5;
  border-radius: 4rpx;
  font-size: 22rpx;
  color: #606266;
}
</style>