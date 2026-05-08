<template>
  <view class="container">
    <!-- 顶部统计 -->
    <view class="stats-card">
      <view class="stat-item">
        <view class="stat-value">{{ stats.projectCount }}</view>
        <view class="stat-label">项目</view>
      </view>
      <view class="stat-item">
        <view class="stat-value">{{ stats.taskCount }}</view>
        <view class="stat-label">待办</view>
      </view>
      <view class="stat-item">
        <view class="stat-value">{{ stats.sampleCount }}</view>
        <view class="stat-label">样本</view>
      </view>
    </view>

    <!-- 快捷入口 -->
    <view class="card">
      <view class="card-title">快捷入口</view>
      <view class="quick-actions">
        <view class="action-item" @click="navigateTo('/pages/risk/index')">
          <view class="action-icon" style="background: linear-gradient(135deg, #409eff, #66b1ff)">
            <uni-icons type="bars" size="24" color="#fff"></uni-icons>
          </view>
          <view class="action-name">风险画像</view>
        </view>
        <view class="action-item" @click="navigateTo('/pages/sampling/execute')">
          <view class="action-icon" style="background: linear-gradient(135deg, #67c23a, #95d475)">
            <uni-icons type="plus" size="24" color="#fff"></uni-icons>
          </view>
          <view class="action-name">执行抽样</view>
        </view>
        <view class="action-item" @click="navigateTo('/pages/vouchers/list')">
          <view class="action-icon" style="background: linear-gradient(135deg, #e6a23c, #eebe77)">
            <uni-icons type="list" size="24" color="#fff"></uni-icons>
          </view>
          <view class="action-name">凭证列表</view>
        </view>
        <view class="action-item" @click="navigateTo('/pages/paper/index')">
          <view class="action-icon" style="background: linear-gradient(135deg, #f56c6c, #f89898)">
            <uni-icons type="paperclip" size="24" color="#fff"></uni-icons>
          </view>
          <view class="action-name">工作底稿</view>
        </view>
      </view>
    </view>

    <!-- 最近项目 -->
    <view class="card">
      <view class="card-header">
        <view class="card-title">最近项目</view>
        <view class="card-more" @click="navigateTo('/pages/project/list')">更多</view>
      </view>
      <view class="project-list">
        <view class="list-item" v-for="item in projects" :key="item.id" @click="goProject(item)">
          <view class="list-icon" :style="{ background: item.status === 'active' ? 'linear-gradient(135deg, #67c23a, #95d475)' : 'linear-gradient(135deg, #909399, #b1b3b8)' }">
            <uni-icons type="folder" size="28" color="#fff"></uni-icons>
          </view>
          <view class="list-info">
            <view class="list-title">{{ item.name }}</view>
            <view class="list-desc">{{ item.description || '暂无描述' }}</view>
          </view>
          <view class="list-action">
            <view :class="['status-tag', item.status]">{{ getStatusText(item.status) }}</view>
          </view>
        </view>
        <view class="empty-tip" v-if="projects.length === 0 && !loading">
          <uni-icons type="info" size="48" color="#c0c4cc"></uni-icons>
          <view class="empty-text">暂无项目</view>
        </view>
        <view class="loading-tip" v-if="loading">
          <uni-icons type="spinner-cycle" size="24" color="#409eff"></uni-icons>
          <view>加载中...</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { getStatusText, navigateTo, showToast } from '@/utils/index'
import { projectApi, taskApi } from '@/src/api.js'

export default {
  setup() {
    const stats = reactive({
      projectCount: 0,
      taskCount: 0,
      sampleCount: 0
    })

    const projects = ref([])
    const loading = ref(false)
    const currentProjectId = ref(null)

    const goProject = (item) => {
      currentProjectId.value = item.id
      uni.setStorageSync('currentProjectId', item.id)
      uni.navigateTo({ url: `/pages/project/detail?id=${item.id}` })
    }

    const loadData = async () => {
      loading.value = true
      try {
        // 加载项目列表
        const res = await projectApi.getList({ page: 1, page_size: 10 })
        projects.value = res.items || []
        stats.projectCount = res.total || projects.value.length

        // 设置当前项目
        if (projects.value.length > 0) {
          currentProjectId.value = projects.value[0].id
          uni.setStorageSync('currentProjectId', currentProjectId.value)

          // 加载任务进度
          try {
            const progress = await taskApi.getProgress(currentProjectId.value)
            stats.taskCount = progress.pending_count || 0
            stats.sampleCount = progress.total_samples || 0
          } catch (e) {
            console.log('加载任务进度失败', e)
          }
        }
      } catch (e) {
        console.error('加载数据失败:', e)
        showToast('加载数据失败')
      } finally {
        loading.value = false
      }
    }

    onMounted(() => {
      loadData()
    })

    return {
      stats,
      projects,
      loading,
      getStatusText,
      navigateTo,
      goProject
    }
  }
}
</script>

<style scoped>
.project-list {
  margin-top: 20rpx;
}

.list-icon {
  width: 80rpx;
  height: 80rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
  flex-shrink: 0;
}

.list-info {
  flex: 1;
  min-width: 0;
}

.list-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.list-desc {
  font-size: 24rpx;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.list-action {
  flex-shrink: 0;
  margin-left: 16rpx;
}

.loading-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx;
  color: #909399;
}
</style>