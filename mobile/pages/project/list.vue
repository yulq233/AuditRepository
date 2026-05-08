<template>
  <view class="container">
    <!-- 搜索栏 -->
    <view class="search-bar">
      <uni-search-bar placeholder="搜索项目" @confirm="onSearch" v-model="keyword" />
    </view>

    <!-- 项目列表 -->
    <view class="project-list">
      <view class="project-item" v-for="item in projects" :key="item.id" @click="goDetail(item)">
        <view class="project-icon">
          <uni-icons type="folder" size="28" :color="item.status === 'active' ? '#67c23a' : '#909399'"></uni-icons>
        </view>
        <view class="project-info">
          <view class="project-name">{{ item.name }}</view>
          <view class="project-desc">{{ item.description || '暂无描述' }}</view>
          <view class="project-meta">
            <view class="meta-item">
              <uni-icons type="calendar" size="14" color="#909399"></uni-icons>
              <text>{{ formatDate(item.created_at) }}</text>
            </view>
          </view>
        </view>
        <view class="project-status">
          <view :class="['status-tag', item.status]">{{ getStatusText(item.status) }}</view>
        </view>
      </view>

      <view class="load-more" @click="loadMore" v-if="hasMore && !loading">
        加载更多
      </view>

      <view class="loading-tip" v-if="loading">
        <uni-icons type="spinner-cycle" size="24" color="#409eff"></uni-icons>
        <view>加载中...</view>
      </view>

      <view class="empty-tip" v-if="projects.length === 0 && !loading">
        <uni-icons type="info" size="48" color="#c0c4cc"></uni-icons>
        <view>暂无项目</view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'
import { showToast, formatDate as formatDateUtil } from '@/utils/index'
import { projectApi } from '@/src/api.js'

export default {
  setup() {
    const projects = ref([])
    const keyword = ref('')
    const page = ref(1)
    const hasMore = ref(true)
    const loading = ref(false)

    const formatDate = (date) => {
      return formatDateUtil(date, 'YYYY-MM-DD')
    }

    const getStatusText = (status) => {
      const map = { active: '进行中', completed: '已完成', archived: '已归档' }
      return map[status] || status
    }

    const loadProjects = async () => {
      loading.value = true
      try {
        const res = await projectApi.getList({
          page: page.value,
          page_size: 20,
          keyword: keyword.value
        })

        const items = res.items || []
        if (page.value === 1) {
          projects.value = items
        } else {
          projects.value = [...projects.value, ...items]
        }

        hasMore.value = items.length === 20
      } catch (e) {
        console.error('加载项目失败:', e)
        showToast('加载失败')
      } finally {
        loading.value = false
      }
    }

    const onSearch = (value) => {
      keyword.value = value.value || ''
      page.value = 1
      hasMore.value = true
      loadProjects()
    }

    const loadMore = () => {
      if (!hasMore.value || loading.value) return
      page.value++
      loadProjects()
    }

    const goDetail = (item) => {
      uni.setStorageSync('currentProjectId', item.id)
      uni.navigateTo({ url: `/pages/project/detail?id=${item.id}` })
    }

    onMounted(() => {
      loadProjects()
    })

    return {
      projects,
      keyword,
      hasMore,
      loading,
      formatDate,
      getStatusText,
      onSearch,
      loadMore,
      goDetail
    }
  }
}
</script>

<style scoped>
.container {
  padding: 20rpx;
}

.search-bar {
  margin-bottom: 20rpx;
}

.project-item {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.project-icon {
  width: 80rpx;
  height: 80rpx;
  background: #f5f5f5;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
}

.project-info {
  flex: 1;
  min-width: 0;
}

.project-name {
  font-size: 30rpx;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-desc {
  font-size: 24rpx;
  color: #909399;
  margin-bottom: 8rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  display: flex;
  gap: 16rpx;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4rpx;
  font-size: 22rpx;
  color: #909399;
}

.project-status {
  flex-shrink: 0;
  margin-left: 16rpx;
}

.status-tag {
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
}

.status-tag.active {
  background: #f0f9eb;
  color: #67c23a;
}

.status-tag.completed {
  background: #ecf5ff;
  color: #409eff;
}

.status-tag.archived {
  background: #f4f4f5;
  color: #909399;
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