<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">工作台</h2>
        <p class="page-subtitle">欢迎使用AI审计抽凭系统</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: linear-gradient(135deg, #409eff, #66b1ff)">
              <el-icon :size="28"><Folder /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.projectCount }}</div>
              <div class="stat-label">项目总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: linear-gradient(135deg, #67c23a, #95d475)">
              <el-icon :size="28"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.voucherCount }}</div>
              <div class="stat-label">凭证总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: linear-gradient(135deg, #e6a23c, #eebe77)">
              <el-icon :size="28"><DataAnalysis /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.sampleCount }}</div>
              <div class="stat-label">抽样数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: linear-gradient(135deg, #f56c6c, #f89898)">
              <el-icon :size="28"><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.alertCount }}</div>
              <div class="stat-label">合规预警</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近项目 -->
    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">最近项目</span>
          <el-button type="primary" @click="$router.push('/projects')">
            <el-icon><Plus /></el-icon>
            新建项目
          </el-button>
        </div>
      </template>

      <el-table :data="recentProjects" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="项目名称" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/projects/${row.id}`)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.status]">
              {{ getProjectStatusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="$router.push(`/projects/${row.id}`)">
              进入项目
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 待办任务 -->
    <el-card class="card-container">
      <template #header>
        <span class="card-title">待办任务</span>
      </template>

      <el-table :data="pendingTasks" style="width: 100%">
        <el-table-column prop="title" label="任务名称" min-width="200" />
        <el-table-column prop="assignee_name" label="负责人" width="120" />
        <el-table-column prop="priority" label="优先级" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.priority === 'high' ? 'blocked' : row.priority === 'medium' ? 'pending' : 'active']">
              {{ getPriorityLabel(row.priority) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止时间" width="180">
          <template #default="{ row }">
            {{ row.deadline ? formatDate(row.deadline) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.status]">
              {{ getTaskStatusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { projectApi, taskApi } from '@/api'
import {
  formatDate,
  getProjectStatusLabel,
  getTaskStatusLabel,
  getPriorityLabel
} from '@/utils/formatters'
import { useLoading } from '@/composables'

const { loading, withLoading } = useLoading()

const stats = ref({
  projectCount: 0,
  voucherCount: 0,
  sampleCount: 0,
  alertCount: 0
})

const recentProjects = ref([])
const pendingTasks = ref([])

const loadDashboard = async () => {
  await withLoading(async () => {
    try {
      const projectRes = await projectApi.getList({ page: 1, page_size: 5 })
      recentProjects.value = projectRes.items || []
      stats.value.projectCount = projectRes.total || 0
    } catch (error) {
      console.error(error)
    }
  })
}

onMounted(() => {
  loadDashboard()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.stat-card {
  transition: transform $transition-normal;

  &:hover {
    transform: translateY(-2px);
  }

  .stat-content {
    display: flex;
    align-items: center;
  }

  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: $border-radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    margin-right: $spacing-md;
    flex-shrink: 0;
  }

  .stat-info {
    .stat-value {
      font-size: 28px;
      font-weight: $font-weight-bold;
      color: $text-primary;
      line-height: 1;
    }

    .stat-label {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-top: $spacing-xs;
    }
  }
}
</style>