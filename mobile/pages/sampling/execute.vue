<template>
  <view class="container">
    <!-- 规则选择 -->
    <view class="card">
      <view class="card-title">选择抽样方式</view>
      <view class="rule-options">
        <view class="rule-option" :class="{ active: ruleType === 'random' }" @click="ruleType = 'random'">
          <uni-icons type="shuffle" size="24"></uni-icons>
          <view>随机抽样</view>
        </view>
        <view class="rule-option" :class="{ active: ruleType === 'amount' }" @click="ruleType = 'amount'">
          <uni-icons type="wallet" size="24"></uni-icons>
          <view>金额抽样</view>
        </view>
        <view class="rule-option" :class="{ active: ruleType === 'ai' }" @click="ruleType = 'ai'">
          <uni-icons type="star" size="24"></uni-icons>
          <view>AI推荐</view>
        </view>
      </view>
    </view>

    <!-- 参数配置 -->
    <view class="card" v-if="ruleType === 'random'">
      <view class="card-title">随机抽样参数</view>
      <view class="param-row">
        <view class="param-label">抽样比例</view>
        <slider :value="params.percentage" @change="onPercentageChange" show-value min="1" max="50" />
      </view>
    </view>

    <view class="card" v-if="ruleType === 'amount'">
      <view class="card-title">金额抽样参数</view>
      <view class="param-row">
        <view class="param-label">最小金额</view>
        <input type="number" v-model="params.minAmount" placeholder="不填则不限" />
      </view>
      <view class="param-row">
        <view class="param-label">最大金额</view>
        <input type="number" v-model="params.maxAmount" placeholder="不填则不限" />
      </view>
    </view>

    <view class="card" v-if="ruleType === 'ai'">
      <view class="card-title">AI智能抽样</view>
      <view class="ai-desc">
        <uni-icons type="info" size="18" color="#909399"></uni-icons>
        <text>AI将根据凭证风险特征自动选择高风险样本</text>
      </view>
      <view class="param-row">
        <view class="param-label">样本数量</view>
        <input type="number" v-model="params.sampleSize" placeholder="建议20-50" />
      </view>
    </view>

    <!-- 执行按钮 -->
    <view class="action-area">
      <button type="primary" @click="executeSampling" :loading="loading">
        执行抽样
      </button>
    </view>

    <!-- 抽样记录 -->
    <view class="card">
      <view class="card-header">
        <view class="card-title">抽样记录</view>
        <view class="card-more" @click="navigateTo('/pages/sampling/result')">查看全部</view>
      </view>
      <view class="record-list">
        <view class="record-item" v-for="item in records" :key="item.id" @click="goResult(item)">
          <view class="record-info">
            <view class="record-name">{{ item.rule_name || '抽样任务' }}</view>
            <view class="record-time">{{ formatDate(item.created_at) }}</view>
          </view>
          <view class="record-stats">
            <text>{{ item.sample_size }}个样本</text>
          </view>
        </view>
        <view class="empty-tip" v-if="records.length === 0 && !loadingRecords">
          暂无抽样记录
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { showToast, formatDate as formatDateUtil, navigateTo } from '@/utils/index'
import { samplingApi, aiApi } from '@/src/api.js'

export default {
  setup() {
    const ruleType = ref('random')
    const loading = ref(false)
    const loadingRecords = ref(false)
    const records = ref([])
    const projectId = ref(null)

    const params = reactive({
      percentage: 10,
      minAmount: null,
      maxAmount: null,
      sampleSize: 30
    })

    const onPercentageChange = (e) => {
      params.percentage = e.detail.value
    }

    const formatDate = (date) => {
      return formatDateUtil(date, 'MM-DD HH:mm')
    }

    const executeSampling = async () => {
      if (!projectId.value) {
        projectId.value = uni.getStorageSync('currentProjectId')
      }

      if (!projectId.value) {
        showToast('请先选择项目')
        return
      }

      loading.value = true
      try {
        let result

        if (ruleType.value === 'ai') {
          // AI智能抽样
          result = await aiApi.intelligentSample(projectId.value, {
            sample_size: params.sampleSize || 30
          })
        } else {
          // 规则抽样
          const ruleData = {
            name: `${ruleType.value === 'random' ? '随机' : '金额'}抽样`,
            rule_type: ruleType.value
          }

          if (ruleType.value === 'random') {
            ruleData.rule_config = {
              percentage: params.percentage
            }
          } else {
            ruleData.rule_config = {
              min_amount: params.minAmount ? parseFloat(params.minAmount) : null,
              max_amount: params.maxAmount ? parseFloat(params.maxAmount) : null
            }
          }

          // 创建规则
          const rule = await samplingApi.createRule(projectId.value, ruleData)

          // 执行抽样
          result = await samplingApi.execute(projectId.value, {
            rule_ids: [rule.id]
          })
        }

        showToast('抽样完成')
        loadRecords()

        // 跳转到结果页
        if (result.record_id || result.id) {
          uni.navigateTo({
            url: `/pages/sampling/result?id=${result.record_id || result.id}`
          })
        }
      } catch (e) {
        console.error('抽样失败:', e)
        showToast('抽样失败: ' + (e.message || '未知错误'))
      } finally {
        loading.value = false
      }
    }

    const loadRecords = async () => {
      if (!projectId.value) {
        projectId.value = uni.getStorageSync('currentProjectId')
      }
      if (!projectId.value) return

      loadingRecords.value = true
      try {
        const res = await samplingApi.getRecords(projectId.value)
        records.value = (res.items || res || []).slice(0, 5)
      } catch (e) {
        console.error('加载记录失败:', e)
      } finally {
        loadingRecords.value = false
      }
    }

    const goResult = (item) => {
      uni.navigateTo({ url: `/pages/sampling/result?id=${item.id}` })
    }

    onMounted(() => {
      loadRecords()
    })

    return {
      ruleType,
      loading,
      loadingRecords,
      records,
      params,
      onPercentageChange,
      executeSampling,
      formatDate,
      navigateTo,
      goResult
    }
  }
}
</script>

<style scoped>
.card {
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-more {
  font-size: 24rpx;
  color: #409eff;
}

.rule-options {
  display: flex;
  gap: 20rpx;
}

.rule-option {
  flex: 1;
  text-align: center;
  padding: 24rpx;
  border: 2rpx solid #dcdfe6;
  border-radius: 12rpx;
  font-size: 26rpx;
  color: #606266;
}

.rule-option.active {
  border-color: #409eff;
  color: #409eff;
  background: #ecf5ff;
}

.ai-desc {
  display: flex;
  align-items: center;
  gap: 8rpx;
  font-size: 24rpx;
  color: #909399;
  margin-bottom: 20rpx;
}

.param-row {
  display: flex;
  align-items: center;
  padding: 16rpx 0;
}

.param-label {
  width: 160rpx;
  font-size: 28rpx;
  color: #606266;
}

.param-row input {
  flex: 1;
  padding: 16rpx;
  border: 1px solid #dcdfe6;
  border-radius: 8rpx;
}

.action-area {
  padding: 40rpx 0;
}

.record-list {
  margin-top: 20rpx;
}

.record-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20rpx 0;
  border-bottom: 1px solid #f5f5f5;
}

.record-item:last-child {
  border-bottom: none;
}

.record-name {
  font-size: 28rpx;
  color: #303133;
}

.record-time {
  font-size: 24rpx;
  color: #909399;
  margin-top: 4rpx;
}

.record-stats {
  font-size: 24rpx;
  color: #409eff;
}

.empty-tip {
  text-align: center;
  padding: 40rpx;
  color: #909399;
  font-size: 26rpx;
}
</style>