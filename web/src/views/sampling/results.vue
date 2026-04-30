<template>
  <div class="page-container">
    <!-- 页面标题区 -->
    <div class="page-title-section">
      <div class="title-content">
        <h1 class="main-title">抽样记录</h1>
        <p class="sub-title">查看抽样执行记录和样本明细</p>
      </div>
      <div class="title-actions">
        <el-select
          v-model="projectId"
          placeholder="选择项目"
          class="project-select"
          @change="onProjectChange"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
      </div>
    </div>

    <!-- 抽样记录列表 -->
    <div class="table-section">
      <!-- 无项目提示 -->
      <div v-if="!projectId" class="empty-state">
        <el-empty description="请先选择项目" :image-size="100" />
      </div>
      <!-- 无数据提示 -->
      <div v-else-if="!loading && records.length === 0" class="empty-state">
        <el-empty description="暂无抽样记录" :image-size="100" />
      </div>
      <!-- 数据列表 -->
      <template v-else>
        <!-- 表格工具栏 -->
        <div class="table-toolbar">
          <div class="toolbar-left">
            <el-button
              type="danger"
              plain
              size="small"
              :loading="batchDeleting"
              :disabled="selectedRecords.length === 0"
              @click="handleBatchDelete"
            >
              <el-icon><Delete /></el-icon>
              批量删除
            </el-button>
            <span class="data-count">共 {{ records.length }} 条记录</span>
            <span v-if="selectedRecords.length > 0" class="selected-count">
              已选中 {{ selectedRecords.length }} 条
            </span>
          </div>
        </div>

        <!-- 表格 -->
        <div class="table-container">
          <el-table
            :data="records"
            class="sampling-table"
            v-loading="loading"
            row-key="id"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="55" align="center" />
            <el-table-column prop="rule_name" label="抽样名称" min-width="126" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="rule-name">{{ row.rule_name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="rule_type" label="抽样类型" min-width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="getRuleTypeTag(row.rule_type)">
                  {{ getRuleTypeName(row.rule_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="sample_size" label="样本数量" width="100" align="center">
              <template #default="{ row }">
                <span class="sample-count">{{ row.sample_size }}</span>
              </template>
            </el-table-column>
            <el-table-column label="风险分布" width="220">
              <template #default="{ row }">
                <div class="risk-distribution">
                  <span class="risk-item high">
                    <span class="risk-dot"></span>
                    高 {{ row.high_risk_count }}
                  </span>
                  <span class="risk-item medium">
                    <span class="risk-dot"></span>
                    中 {{ row.medium_risk_count }}
                  </span>
                  <span class="risk-item low">
                    <span class="risk-dot"></span>
                    低 {{ row.low_risk_count }}
                  </span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" min-width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
                  {{ row.status === 'completed' ? '已完成' : '处理中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="抽样时间" min-width="180">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="viewDetail(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { samplingApi, projectApi } from '@/api'

const router = useRouter()
const loading = ref(false)
const projects = ref([])
const records = ref([])
const projectId = ref(localStorage.getItem('currentProjectId') || '')
const selectedRecords = ref([]) // 选中的抽样记录
const batchDeleting = ref(false) // 批量删除加载状态

const getRuleTypeName = (type) => {
  const types = {
    'random': '随机抽样',
    'amount': '金额抽样',
    'subject': '科目抽样',
    'date': '日期抽样',
    'stratified': '分层抽样',
    'risk_stratified': '风险分层抽样',
    'ai': 'AI智能抽样'
  }
  return types[type] || type
}

const getRuleTypeTag = (type) => {
  const tags = {
    'random': 'primary',
    'amount': 'success',
    'subject': 'warning',
    'date': 'info',
    'stratified': 'warning',
    'risk_stratified': 'danger',
    'ai': 'danger',
    'monetary_unit': 'success',
    'systematic': 'info'
  }
  return tags[type] || 'info'
}

const formatTime = (time) => {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

const loadProjects = async () => {
  try {
    const res = await projectApi.getList({ page: 1, page_size: 100 })
    projects.value = res.items || []

    // 验证当前项目是否有效
    if (projectId.value) {
      const exists = projects.value.some(p => p.id === projectId.value)
      if (!exists) {
        projectId.value = ''
        localStorage.removeItem('currentProjectId')
      }
    }
  } catch (error) {
    console.error(error)
  }
}

const onProjectChange = (val) => {
  localStorage.setItem('currentProjectId', val)
  loadRecords()
}

const loadRecords = async () => {
  if (!projectId.value) {
    records.value = []
    return
  }

  loading.value = true
  try {
    const res = await samplingApi.getRecords(projectId.value)
    records.value = res || []
  } catch (error) {
    console.error(error)
    // 项目不存在时清空项目选择，不显示错误提示
    if (error.response?.status === 404 || error.detail?.includes('不存在')) {
      projectId.value = ''
      localStorage.removeItem('currentProjectId')
      records.value = []
    } else {
      ElMessage.error('加载抽样记录失败')
    }
  } finally {
    loading.value = false
  }
}

const viewDetail = (record) => {
  router.push({
    path: '/sampling/detail',
    query: {
      projectId: projectId.value,
      recordId: record.id
    }
  })
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedRecords.value = selection
}

// 批量删除
const handleBatchDelete = async () => {
  if (selectedRecords.value.length === 0) {
    ElMessage.warning('请先选择要删除的记录')
    return
  }

  try {
    const confirm = await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRecords.value.length} 条抽样记录吗？删除后无法恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    if (confirm) {
      batchDeleting.value = true
      const deletePromises = selectedRecords.value.map(record =>
        samplingApi.deleteRecord(projectId.value, record.id)
      )

      await Promise.all(deletePromises)
      ElMessage.success(`成功删除 ${selectedRecords.value.length} 条记录`)

      // 清空选择并刷新列表
      selectedRecords.value = []
      await loadRecords()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  } finally {
    batchDeleting.value = false
  }
}

onMounted(async () => {
  await loadProjects()
  loadRecords()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

/* 覆盖页面容器边距，参考凭证管理页面 */
.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

// 页面标题区
.page-title-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-lg;
  padding-bottom: $spacing-lg;
  border-bottom: 1px solid $border-light;

  .title-content {
    .main-title {
      font-size: 24px;
      font-weight: 700;
      color: $text-primary;
      margin: 0 0 4px 0;
    }

    .sub-title {
      font-size: 14px;
      color: $text-secondary;
      margin: 0;
    }
  }

  .project-select {
    width: 220px;
  }
}

// 表格区域
.table-section {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #f3f4f6;

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .data-count {
      font-size: 14px;
      color: #6b7280;
    }

    .selected-count {
      font-size: 14px;
      color: #ef4444;
      font-weight: 500;
    }
  }

  }

.table-container {
  padding: 0;
  overflow-x: auto;
}

.empty-state {
  padding: 48px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

// 抽样表格样式
.sampling-table {
  width: 100%;

  :deep(.el-table__header th) {
    background: #f9fafb !important;
    font-weight: 600;
    color: #374151;
    font-size: 13px;
    padding: 16px 20px;

    .cell {
      white-space: nowrap;
      overflow: visible;
    }
  }

  :deep(.el-table__body td) {
    padding: 18px 20px;
    border-bottom: 1px solid #f3f4f6;

    .cell {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  :deep(.el-table__row) {
    transition: background 0.15s;

    &:hover > td {
      background: #fafbfc !important;
    }
  }
}

.rule-name {
  font-weight: 500;
  color: #1f2937;
}

.sample-count {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-weight: 600;
  color: $primary-color;
}

// 风险分布
.risk-distribution {
  display: flex;
  gap: 12px;

  .risk-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;

    .risk-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
    }

    &.high {
      color: #ef4444;
      .risk-dot { background: #ef4444; }
    }

    &.medium {
      color: #f59e0b;
      .risk-dot { background: #f59e0b; }
    }

    &.low {
      color: #10b981;
      .risk-dot { background: #10b981; }
    }
  }
}
</style>
