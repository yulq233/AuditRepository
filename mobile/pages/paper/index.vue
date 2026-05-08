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
            <view class="meta-item">{{ getPaperTypeText(item.paper_type) }}</view>
            <view class="meta-item">{{ formatDate(item.created_at) }}</view>
          </view>
        </view>
        <view class="paper-action">
          <uni-icons type="right" size="20" color="#c0c4cc"></uni-icons>
        </view>
      </view>

      <view class="loading-tip" v-if="loading">
        <uni-icons type="spinner-cycle" size="24" color="#409eff"></uni-icons>
        <view>加载中...</view>
      </view>

      <view class="empty-tip" v-if="papers.length === 0 && !loading">
        <uni-icons type="info" size="48" color="#c0c4cc"></uni-icons>
        <view>暂无工作底稿</view>
        <view class="empty-hint">点击下方按钮生成底稿</view>
      </view>
    </view>

    <!-- 生成按钮 -->
    <view class="action-area">
      <button type="primary" @click="showGenerateMenu">生成底稿</button>
    </view>

    <!-- 生成底稿弹窗 -->
    <uni-popup ref="popup" type="bottom">
      <view class="popup-content">
        <view class="popup-title">选择底稿类型</view>
        <view class="popup-list">
          <view class="popup-item" v-for="type in paperTypes" :key="type.value" @click="generatePaper(type.value)">
            <view class="popup-item-name">{{ type.label }}</view>
            <view class="popup-item-desc">{{ type.desc }}</view>
          </view>
        </view>
        <view class="popup-cancel" @click="closePopup">取消</view>
      </view>
    </uni-popup>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'
import { showToast, formatDate as formatDateUtil } from '@/utils/index'
import { paperApi } from '@/src/api.js'

export default {
  setup() {
    const papers = ref([])
    const loading = ref(false)
    const generating = ref(false)
    const projectId = ref(null)
    const popup = ref(null)

    const paperTypes = [
      { value: 'sampling_summary', label: '抽样汇总表', desc: '汇总抽样情况统计' },
      { value: 'substantive_test', label: '实质性测试底稿', desc: '科目实质性测试记录' },
      { value: 'risk_assessment', label: '风险评估底稿', desc: '项目风险评估总结' }
    ]

    const getPaperTypeText = (type) => {
      const map = {
        sampling_summary: '抽样汇总表',
        substantive_test: '实质性测试',
        risk_assessment: '风险评估'
      }
      return map[type] || type || '未知类型'
    }

    const formatDate = (date) => {
      return formatDateUtil(date, 'YYYY-MM-DD')
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
        const res = await paperApi.getList(projectId.value)
        papers.value = res.items || res || []
      } catch (e) {
        console.error('加载底稿失败:', e)
        showToast('加载失败')
      } finally {
        loading.value = false
      }
    }

    const viewPaper = (item) => {
      // 预览底稿
      showToast('预览功能开发中')
    }

    const showGenerateMenu = () => {
      popup.value?.open()
    }

    const closePopup = () => {
      popup.value?.close()
    }

    const generatePaper = async (paperType) => {
      closePopup()

      if (!projectId.value) {
        projectId.value = uni.getStorageSync('currentProjectId')
      }

      if (!projectId.value) {
        showToast('请先选择项目')
        return
      }

      generating.value = true
      showToast('正在生成底稿...')

      try {
        await paperApi.generate(projectId.value, {
          paper_type: paperType,
          title: `${getPaperTypeText(paperType)} - ${formatDateUtil(new Date(), 'YYYY-MM-DD')}`
        })

        showToast('生成成功')
        loadData()
      } catch (e) {
        console.error('生成底稿失败:', e)
        showToast('生成失败')
      } finally {
        generating.value = false
      }
    }

    onMounted(() => {
      loadData()
    })

    return {
      papers,
      loading,
      generating,
      paperTypes,
      popup,
      getPaperTypeText,
      formatDate,
      loadData,
      viewPaper,
      showGenerateMenu,
      closePopup,
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

.loading-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx;
  color: #909399;
}

.empty-tip {
  text-align: center;
  padding: 80rpx 0;
  color: #c0c4cc;
}

.empty-hint {
  font-size: 24rpx;
  margin-top: 16rpx;
}

.action-area {
  padding: 20rpx 0;
}

.popup-content {
  background: #fff;
  border-radius: 24rpx 24rpx 0 0;
  padding: 24rpx;
}

.popup-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #303133;
  text-align: center;
  margin-bottom: 24rpx;
}

.popup-list {
  margin-bottom: 24rpx;
}

.popup-item {
  padding: 24rpx;
  border-bottom: 1px solid #f5f5f5;
}

.popup-item:last-child {
  border-bottom: none;
}

.popup-item-name {
  font-size: 30rpx;
  color: #303133;
  margin-bottom: 8rpx;
}

.popup-item-desc {
  font-size: 24rpx;
  color: #909399;
}

.popup-cancel {
  text-align: center;
  padding: 24rpx;
  color: #909399;
  border-top: 1px solid #f5f5f5;
}
</style>