<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">审计轨迹</h2>
      <p class="page-subtitle">完整记录所有操作历史</p>
    </div>

    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">操作日志</span>
          <el-button type="primary" @click="loadTrail">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="项目">
          <el-select v-model="filters.projectId" placeholder="选择项目" style="width: 200px" clearable @change="loadTrail">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="filters.action" placeholder="全部" clearable style="width: 150px" @change="loadTrail">
            <el-option label="创建抽样" value="sample.created" />
            <el-option label="复核样本" value="sample.reviewed" />
            <el-option label="凭证上传" value="voucher.uploaded" />
            <el-option label="规则执行" value="rule.executed" />
            <el-option label="结果导出" value="result.exported" />
            <el-option label="AI分析" value="ai.analyzed" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="loadTrail"
          />
        </el-form-item>
      </el-form>

      <el-table :data="trails" style="width: 100%" v-loading="loading">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at, 'YYYY-MM-DD HH:mm:ss') }}
          </template>
        </el-table-column>
        <el-table-column prop="user_id" label="操作人" width="120">
          <template #default="{ row }">
            {{ row.user_id || '系统' }}
          </template>
        </el-table-column>
        <el-table-column prop="action" label="操作类型" width="150">
          <template #default="{ row }">
            {{ getActionLabel(row.action) }}
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="对象类型" width="120">
          <template #default="{ row }">
            {{ row.target_type || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="details" label="操作详情" min-width="250">
          <template #default="{ row }">
            <el-text truncated>{{ formatDetails(row.details) }}</el-text>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" width="150">
          <template #default="{ row }">
            {{ row.reason || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="130">
          <template #default="{ row }">
            {{ row.ip_address || '-' }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadTrail"
          @current-change="loadTrail"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { formatDate } from '@/utils/formatters'
import { projectApi, auditTrailApi } from '@/api'

const loading = ref(false)
const projects = ref([])
const trails = ref([])

const filters = reactive({
  projectId: '',
  action: '',
  dateRange: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const getActionLabel = (action) => {
  const map = {
    'sample.created': '创建抽样',
    'sample.reviewed': '复核样本',
    'voucher.uploaded': '凭证上传',
    'voucher.deleted': '凭证删除',
    'rule.created': '创建规则',
    'rule.executed': '规则执行',
    'result.exported': '结果导出',
    'ai.analyzed': 'AI分析',
    'project.created': '创建项目',
    'project.updated': '更新项目',
    'task.assigned': '任务分派',
    'task.completed': '任务完成',
    'paper.generated': '底稿生成',
    'matching.performed': '匹配执行',
    'compliance.checked': '合规检查'
  }
  return map[action] || action || '-'
}

const formatDetails = (details) => {
  if (!details) return '-'
  if (typeof details === 'string') {
    try {
      details = JSON.parse(details)
    } catch {
      return details
    }
  }
  if (typeof details === 'object') {
    const keys = Object.keys(details)
    if (keys.length === 0) return '-'
    return keys.slice(0, 3).map(k => `${k}: ${details[k]}`).join(', ')
  }
  return String(details)
}

const loadProjects = async () => {
  try {
    const res = await projectApi.getList({ page: 1, page_size: 100 })
    projects.value = res.items || []
    if (projects.value.length > 0 && !filters.projectId) {
      filters.projectId = localStorage.getItem('currentProjectId') || projects.value[0].id
    }
  } catch (e) {
    console.error('加载项目列表失败:', e)
  }
}

const loadTrail = async () => {
  if (!filters.projectId) {
    trails.value = []
    return
  }

  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }

    if (filters.action) {
      params.action = filters.action
    }

    if (filters.dateRange && filters.dateRange.length === 2) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }

    const res = await auditTrailApi.query(filters.projectId, params)
    trails.value = res.items || []
    pagination.total = res.total || 0
  } catch (e) {
    console.error('加载审计轨迹失败:', e)
    trails.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadProjects()
  loadTrail()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: $spacing-md;
}

.pagination-container {
  margin-top: $spacing-md;
  display: flex;
  justify-content: flex-end;
}

:deep(.el-table) {
  .el-table__body-wrapper {
    overflow-x: auto;
  }

  .el-table__cell .cell {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}
</style>