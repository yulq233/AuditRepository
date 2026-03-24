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

    <!-- 执行按钮 -->
    <view class="action-area">
      <button type="primary" @click="executeSampling" :loading="loading">
        执行抽样
      </button>
    </view>
  </view>
</template>

<script>
import { ref, reactive } from 'vue'

export default {
  setup() {
    const ruleType = ref('random')
    const loading = ref(false)

    const params = reactive({
      percentage: 10,
      minAmount: null,
      maxAmount: null
    })

    const onPercentageChange = (e) => {
      params.percentage = e.detail.value
    }

    const executeSampling = async () => {
      loading.value = true
      try {
        // TODO: 调用API执行抽样
        await new Promise(resolve => setTimeout(resolve, 1500))
        uni.showToast({ title: '抽样完成', icon: 'success' })
        setTimeout(() => {
          uni.navigateTo({ url: '/pages/sampling/result' })
        }, 1000)
      } catch (error) {
        uni.showToast({ title: '抽样失败', icon: 'none' })
      } finally {
        loading.value = false
      }
    }

    return {
      ruleType,
      loading,
      params,
      onPercentageChange,
      executeSampling
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
</style>