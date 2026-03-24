<template>
  <view class="container">
    <!-- 底稿列表 -->
    <view class="paper-list">
      <view class="paper-item" v-for="item in papers" :key="item.id" @click="viewPaper(item)">
        <view class="paper-icon">
          <uni-icons type="paperclip" size="28" color="#409eff"></uni-icons>
        </view>
        <view class="paper-info">
          <view class="paper-title">{{ item.title }}</view>
          <view class="paper-meta">
            <view class="meta-item">{{ item.paper_type }}</view>
            <view class="meta-item">{{ item.created_at }}</view>
          </view>
        </view>
        <view class="paper-action">
          <uni-icons type="right" size="20" color="#c0c4cc"></uni-icons>
        </view>
      </view>

      <view class="empty-tip" v-if="papers.length === 0">
        <uni-icons type="info" size="48" color="#c0c4cc"></uni-icons>
        <view>暂无工作底稿</view>
      </view>
    </view>

    <!-- 生成按钮 -->
    <view class="action-area">
      <button type="primary" @click="generatePaper">生成底稿</button>
    </view>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  setup() {
    const papers = ref([])

    const viewPaper = (item) => {
      uni.showToast({ title: '查看底稿功能开发中', icon: 'none' })
    }

    const generatePaper = () => {
      uni.showActionSheet({
        itemList: ['抽样汇总表', '实质性测试底稿', '风险评估底稿'],
        success: (res) => {
          const types = ['sampling_summary', 'substantive_test', 'risk_assessment']
          // TODO: 调用API生成底稿
          uni.showToast({ title: '生成中...', icon: 'loading' })
          setTimeout(() => {
            uni.showToast({ title: '生成成功', icon: 'success' })
            loadData()
          }, 1500)
        }
      })
    }

    const loadData = async () => {
      // TODO: 从API加载
      papers.value = [
        { id: '1', title: '2024年度抽样汇总表', paper_type: '抽样汇总表', created_at: '2024-03-20' },
        { id: '2', title: '应收账款实质性测试', paper_type: '实质性测试', created_at: '2024-03-18' }
      ]
    }

    onMounted(() => {
      loadData()
    })

    return {
      papers,
      viewPaper,
      generatePaper
    }
  }
}
</script>

<style scoped>
.paper-item {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.paper-icon {
  width: 80rpx;
  height: 80rpx;
  background: #ecf5ff;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
}

.paper-info {
  flex: 1;
}

.paper-title {
  font-size: 28rpx;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8rpx;
}

.paper-meta {
  display: flex;
  gap: 16rpx;
}

.meta-item {
  font-size: 24rpx;
  color: #909399;
}

.empty-tip {
  text-align: center;
  padding: 80rpx 0;
  color: #c0c4cc;
}

.action-area {
  padding: 20rpx 0;
}
</style>