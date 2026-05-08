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

    <!-- 操作按钮 -->
    <view class="action-bar">
      <button type="primary" size="mini" @click="generateProfiles" :loading="generating">
        {{ generating ? '生成中...' : '生成风险画像' }}
      </button>
      <button size="mini" @click="loadData">刷新</button>
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
            <view class="factor-tag" v-for="(factor, idx) in getRiskFactors(item.risk_factors)" :key="idx">
              {{ factor }}
            </view>
          </view>
        </view>
      </view>

      <view class="loading-tip" v-if="loading">
        <uni-icons type="spinner-cycle" size="24" color="#409eff"></uni-icons>
        <view>加载中...</view>
      </view>

      <view class="empty-tip" v-if="profiles.length === 0 && !loading">
        <uni-icons type="info" size="48" color="#c0c4cc"></uni-icons>
        <view>暂无风险画像数据</view>
        <view class="empty-hint">点击上方"生成风险画像"按钮开始分析</view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { showToast } from '@/utils/index'
import { riskApi } from '@/src/api.js'

export default {
  setup() {
    const riskStats = reactive({ high: 0, medium: 0, low: 0 })
    const profiles = ref([])
    const loading = ref(false)
    const generating = ref(false)
    const projectId = ref(null)

    const getRiskText = (level) => {
      const map = { high: '高风险', medium: '中风险', low: '低风险' }
      return map[level] || level
    }

    const getRiskColor = (level) => {
      const map = { high: '#f56c6c', medium: '#e6a23c', low: '#67c23a' }
      return map[level] || '#909399'
    }

    const getRiskFactors = (factors) => {
      if (!factors) return []
      if (typeof factors === 'string') {
        try {
          factors = JSON.parse(factors)
        } catch {
          return []
        }
      }
      if (Array.isArray(factors)) {
        return factors.slice(0, 3).map(f => f.name || f)
      }
      return []
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
        const res = await riskApi.getSubjects(projectId.value)
        profiles.value = res || []

        // 统计风险等级
        riskStats.high = 0
        riskStats.medium = 0
        riskStats.low = 0
        profiles.value.forEach(p => {
          if (p.risk_level && riskStats.hasOwnProperty(p.risk_level)) {
            riskStats[p.risk_level]++
          }
        })
      } catch (e) {
        console.error('加载风险画像失败:', e)
        showToast('加载失败')
      } finally {
        loading.value = false
      }
    }

    const generateProfiles = async () => {
      if (!projectId.value) {
        projectId.value = uni.getStorageSync('currentProjectId')
      }

      if (!projectId.value) {
        showToast('请先选择项目')
        return
      }

      generating.value = true
      try {
        showToast('正在生成风险画像...')
        await riskApi.generateSubjects(projectId.value)
        showToast('生成完成')
        await loadData()
      } catch (e) {
        console.error('生成风险画像失败:', e)
        showToast('生成失败')
      } finally {
        generating.value = false
      }
    }

    onMounted(() => {
      loadData()
    })

    return {
      riskStats,
      profiles,
      loading,
      generating,
      getRiskText,
      getRiskColor,
      getRiskFactors,
      loadData,
      generateProfiles
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

.action-bar {
  display: flex;
  gap: 20rpx;
  padding: 0 0 20rpx;
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
  flex-wrap: wrap;
  gap: 8rpx;
}

.factor-tag {
  padding: 4rpx 12rpx;
  background: #f5f5f5;
  border-radius: 4rpx;
  font-size: 22rpx;
  color: #606266;
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
  padding: 60rpx 0;
  color: #909399;
}

.empty-hint {
  font-size: 24rpx;
  color: #c0c4cc;
  margin-top: 16rpx;
}
</style>