<template>
  <div class="page-container page-enter">
    <div class="page-header">
      <div>
        <h2 class="page-title">工作台</h2>
        <p class="page-subtitle">欢迎使用AI审计抽凭系统</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="24" class="stat-row">
      <el-col :xs="12" :sm="6" v-for="(stat, index) in statCards" :key="stat.key">
        <el-card shadow="hover" class="stat-card hover-lift stagger-item" :style="{ animationDelay: `${index * 0.1}s` }">
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: stat.gradient }">
              <el-icon :size="28"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats[stat.key] }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近项目 -->
    <el-card class="card-container project-card card-enter">
      <template #header>
        <div class="card-header">
          <div class="card-header-left">
            <span class="card-title">最近项目</span>
            <span class="card-badge">{{ recentProjects.length }}</span>
          </div>
          <el-button type="primary" @click="$router.push('/projects')">
            <el-icon><Plus /></el-icon>
            新建项目
          </el-button>
        </div>
      </template>

      <el-table :data="recentProjects" style="width: 100%" v-loading="loading" class="enhanced-table">
        <el-table-column prop="name" label="项目名称" min-width="200">
          <template #default="{ row }">
            <div class="project-name-cell">
              <div class="project-icon">
                <el-icon><Folder /></el-icon>
              </div>
              <el-link type="primary" @click="$router.push(`/projects/${row.id}`)">
                {{ row.name }}
              </el-link>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="{ row }">
            <span class="desc-text">{{ row.description || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <span :class="['status-tag', row.status]">
              <span class="status-dot"></span>
              {{ getProjectStatusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span class="time-text">
              <el-icon><Clock /></el-icon>
              {{ formatDate(row.created_at) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link @click="$router.push(`/projects/${row.id}`)">
              进入项目
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="recentProjects.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无项目，点击上方按钮创建" :image-size="80" />
      </div>
    </el-card>

    <!-- 待办任务 -->
    <el-card class="card-container task-card card-enter">
      <template #header>
        <div class="card-header">
          <div class="card-header-left">
            <span class="card-title">待办任务</span>
            <span class="card-badge badge-warning" v-if="pendingTasks.length">{{ pendingTasks.length }}</span>
          </div>
        </div>
      </template>

      <el-table :data="pendingTasks" style="width: 100%" class="enhanced-table">
        <el-table-column prop="title" label="任务名称" min-width="200">
          <template #default="{ row }">
            <div class="task-title-cell">
              <el-icon class="task-icon"><Document /></el-icon>
              {{ row.title }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="assignee_name" label="负责人" width="120" align="center">
          <template #default="{ row }">
            <div class="assignee-cell">
              <el-avatar :size="24" class="assignee-avatar">{{ row.assignee_name?.charAt(0) }}</el-avatar>
              <span>{{ row.assignee_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100" align="center">
          <template #default="{ row }">
            <span :class="['priority-tag', row.priority]">
              {{ getPriorityLabel(row.priority) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止时间" width="180">
          <template #default="{ row }">
            <span class="time-text">
              <el-icon><Clock /></el-icon>
              {{ row.deadline ? formatDate(row.deadline) : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <span :class="['status-tag', row.status]">
              <span class="status-dot"></span>
              {{ getTaskStatusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="pendingTasks.length === 0" class="empty-state">
        <el-empty description="暂无待办任务" :image-size="80" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { projectApi, taskApi } from '@/api'
import { Folder, Document, DataAnalysis, Warning, Plus, Clock } from '@element-plus/icons-vue'
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

const statCards = [
  { key: 'projectCount', label: '项目总数', icon: Folder, gradient: 'linear-gradient(135deg, #6366f1, #818cf8)' },
  { key: 'voucherCount', label: '凭证总数', icon: Document, gradient: 'linear-gradient(135deg, #10b981, #34d399)' },
  { key: 'sampleCount', label: '抽样数量', icon: DataAnalysis, gradient: 'linear-gradient(135deg, #f59e0b, #fbbf24)' },
  { key: 'alertCount', label: '合规预警', icon: Warning, gradient: 'linear-gradient(135deg, #ef4444, #f87171)' }
]

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

// 统计卡片行间距
.stat-row {
  margin-bottom: $spacing-xl;
}

.stat-card {
  transition: all $transition-normal;
  border-radius: $border-radius-xl;
  border: 1px solid $border-lighter;
  overflow: hidden;

  &:hover {
    transform: translateY(-6px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);

    .stat-icon {
      transform: scale(1.1);
    }
  }

  .stat-content {
    display: flex;
    align-items: center;
    padding: 8px 0;
  }

  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: $border-radius-xl;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    margin-right: $spacing-lg;
    flex-shrink: 0;
    transition: transform 0.3s ease;
  }

  .stat-info {
    .stat-value {
      font-size: 32px;
      font-weight: $font-weight-bold;
      color: $text-primary;
      line-height: 1;
      letter-spacing: -1px;
    }

    .stat-label {
      font-size: 13px;
      color: $text-secondary;
      margin-top: 6px;
      font-weight: 500;
    }
  }
}

// 卡片间距
.project-card {
  margin-bottom: $spacing-xl;
}

.task-card {
  margin-bottom: $spacing-lg;
}

// 卡片头部增强
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.card-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 600;
  background: $primary-lighter;
  color: $primary-color;
  border-radius: $border-radius-full;

  &.badge-warning {
    background: $warning-lighter;
    color: $warning-color;
  }
}

// 项目名称单元格
.project-name-cell {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .project-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: $primary-lighter;
    color: $primary-color;
    border-radius: $border-radius-md;
    flex-shrink: 0;
  }
}

// 任务标题单元格
.task-title-cell {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .task-icon {
    color: $text-secondary;
  }
}

// 负责人单元格
.assignee-cell {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  justify-content: center;

  .assignee-avatar {
    background: $gradient-primary;
    color: white;
    font-size: 12px;
    font-weight: 600;
  }
}

// 描述文字
.desc-text {
  color: $text-secondary;
  font-size: 14px;
}

// 时间文字
.time-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: $text-secondary;
  font-size: 13px;
  font-family: 'SF Mono', 'Monaco', monospace;

  .el-icon {
    font-size: 14px;
  }
}

// 状态标签增强
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: $border-radius-full;
  font-size: 12px;
  font-weight: 600;

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }

  &.active {
    background: $success-lighter;
    color: $success-color;
  }

  &.completed {
    background: $primary-lighter;
    color: $primary-color;
  }

  &.pending {
    background: $warning-lighter;
    color: $warning-color;
  }

  &.blocked, &.high {
    background: $danger-lighter;
    color: $danger-color;
  }

  &.medium {
    background: $warning-lighter;
    color: $warning-color;
  }

  &.low {
    background: $success-lighter;
    color: $success-color;
  }
}

// 优先级标签
.priority-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: $border-radius-full;
  font-size: 12px;
  font-weight: 600;

  &.high {
    background: $danger-lighter;
    color: $danger-color;
  }

  &.medium {
    background: $warning-lighter;
    color: $warning-color;
  }

  &.low {
    background: $success-lighter;
    color: $success-color;
  }
}

// 空状态
.empty-state {
  padding: $spacing-xxl;
}

// 增强表格
.enhanced-table {
  :deep(.el-table__cell) {
    transition: background $transition-fast;
  }

  :deep(.el-table__row) {
    &:hover {
      .project-icon {
        background: $primary-color;
        color: white;
      }
    }
  }
}
</style>