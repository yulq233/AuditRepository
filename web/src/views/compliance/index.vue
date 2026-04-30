<template>
  <div class="page-container">
    <!-- 页面标题 -->
    <div class="page-title-section">
      <div class="title-content">
        <h1 class="main-title">合规检查</h1>
        <p class="sub-title">凭证合规性自动检查与预警管理</p>
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

    <!-- 统计卡片 -->
    <div class="stats-section" v-loading="statsLoading">
      <div class="stat-card">
        <div class="stat-icon total">
          <el-icon :size="24"><Document /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.total || 0 }}</div>
          <div class="stat-label">预警总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon pending">
          <el-icon :size="24"><Warning /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value pending">{{ statistics.pending || 0 }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon resolved">
          <el-icon :size="24"><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value resolved">{{ statistics.resolved || 0 }}</div>
          <div class="stat-label">已处理</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon high">
          <el-icon :size="24"><InfoFilled /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value high">{{ statistics.by_severity?.high || 0 }}</div>
          <div class="stat-label">高风险</div>
        </div>
      </div>
    </div>

    <!-- 检查规则 -->
    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">检查规则</span>
          <el-button type="primary" @click="runCheck" :loading="checkLoading">
            <el-icon><Warning /></el-icon>
            执行检查
          </el-button>
        </div>
      </template>

      <el-checkbox-group v-model="selectedRules" class="rules-grid">
        <el-checkbox
          v-for="rule in rules"
          :key="rule.code"
          :label="rule.code"
          class="rule-checkbox"
        >
          <div class="rule-info">
            <span class="rule-name">{{ rule.name }}</span>
            <span :class="['rule-severity', rule.severity]">
              {{ getSeverityLabel(rule.severity) }}
            </span>
          </div>
        </el-checkbox>
      </el-checkbox-group>
    </el-card>

    <!-- 预警列表 -->
    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">预警列表</span>
          <div class="header-filters">
            <el-select
              v-model="filterSeverity"
              placeholder="严重程度"
              clearable
              class="filter-select"
              @change="loadAlerts"
            >
              <el-option label="严重" value="critical" />
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
              <el-option label="信息" value="info" />
            </el-select>
            <el-select
              v-model="filterResolved"
              placeholder="处理状态"
              clearable
              class="filter-select"
              @change="loadAlerts"
            >
              <el-option label="待处理" :value="false" />
              <el-option label="已处理" :value="true" />
            </el-select>
            <el-tag type="danger" v-if="alerts.length > 0">{{ alerts.length }} 条预警</el-tag>
          </div>
        </div>
      </template>

      <!-- 无数据提示 -->
      <div v-if="!projectId" class="empty-state">
        <el-empty description="请先选择项目" :image-size="100" />
      </div>
      <div v-else-if="!loading && alerts.length === 0" class="empty-state">
        <el-empty description="暂无预警数据" :image-size="100" />
      </div>

      <!-- 预警表格 -->
      <el-table
        v-else
        :data="alerts"
        class="alerts-table"
        v-loading="loading"
      >
        <el-table-column prop="voucher_no" label="凭证号" width="140">
          <template #default="{ row }">
            <span class="voucher-no">{{ row.voucher_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rule_name" label="规则" width="120" />
        <el-table-column prop="severity" label="严重程度" width="100" align="center">
          <template #default="{ row }">
            <span :class="['severity-tag', row.severity]">
              {{ getSeverityLabel(row.severity) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="alert_message" label="预警信息" min-width="280" show-overflow-tooltip />
        <el-table-column prop="created_at" label="发现时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="is_resolved" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_resolved ? 'success' : 'warning'" size="small">
              {{ row.is_resolved ? '已处理' : '待处理' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_resolved"
              type="primary"
              link
              size="small"
              @click="resolveAlert(row)"
            >
              标记处理
            </el-button>
            <span v-else class="resolved-text">-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, Document, CircleCheck, InfoFilled } from '@element-plus/icons-vue'
import { complianceApi, projectApi } from '@/api'

const loading = ref(false)
const statsLoading = ref(false)
const checkLoading = ref(false)
const projects = ref([])
const projectId = ref(localStorage.getItem('currentProjectId') || '')
const rules = ref([])
const selectedRules = ref([])
const alerts = ref([])
const statistics = ref({})
const filterSeverity = ref('')
const filterResolved = ref(null)

const getSeverityLabel = (severity) => {
  const map = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低',
    info: '信息'
  }
  return map[severity] || severity
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
  loadRules()
  loadAlerts()
  loadStatistics()
}

const loadRules = async () => {
  if (!projectId.value) {
    rules.value = []
    return
  }

  try {
    const res = await complianceApi.getRules(projectId.value)
    rules.value = res || []
    // 默认选中所有规则
    if (selectedRules.value.length === 0) {
      selectedRules.value = rules.value.map(r => r.code)
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('加载规则失败')
  }
}

const loadAlerts = async () => {
  if (!projectId.value) {
    alerts.value = []
    return
  }

  loading.value = true
  try {
    const params = {}
    if (filterSeverity.value) {
      params.severity = filterSeverity.value
    }
    if (filterResolved.value !== null && filterResolved.value !== '') {
      params.resolved = filterResolved.value
    }

    const res = await complianceApi.getAlerts(projectId.value, params)
    alerts.value = res || []
  } catch (error) {
    console.error(error)
    if (error.response?.status !== 404) {
      ElMessage.error('加载预警失败')
    }
  } finally {
    loading.value = false
  }
}

const loadStatistics = async () => {
  if (!projectId.value) {
    statistics.value = {}
    return
  }

  statsLoading.value = true
  try {
    const res = await complianceApi.getStatistics(projectId.value)
    statistics.value = res || {}
  } catch (error) {
    console.error(error)
  } finally {
    statsLoading.value = false
  }
}

const runCheck = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  if (selectedRules.value.length === 0) {
    ElMessage.warning('请至少选择一个检查规则')
    return
  }

  checkLoading.value = true
  try {
    const res = await complianceApi.runCheck(projectId.value, selectedRules.value)
    ElMessage.success(`检查完成，共发现 ${res.alert_count} 条预警`)
    loadAlerts()
    loadStatistics()
  } catch (error) {
    console.error(error)
    ElMessage.error('执行检查失败')
  } finally {
    checkLoading.value = false
  }
}

const resolveAlert = async (alert) => {
  try {
    await ElMessageBox.confirm(
      `确定将预警"${alert.alert_message}"标记为已处理？`,
      '处理确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    await complianceApi.resolveAlert(projectId.value, alert.id)
    ElMessage.success('已标记为已处理')
    loadAlerts()
    loadStatistics()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('处理失败')
    }
  }
}

onMounted(async () => {
  await loadProjects()
  if (projectId.value) {
    loadRules()
    loadAlerts()
    loadStatistics()
  }
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

// 统计卡片
.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-lg;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  background: $background-white;
  border-radius: $border-radius-lg;
  padding: $spacing-lg;
  box-shadow: $shadow-card;
  transition: all 0.2s ease;

  &:hover {
    box-shadow: $shadow-card-hover;
    transform: translateY(-2px);
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;

    &.total {
      background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
      color: #6366f1;
    }

    &.pending {
      background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
      color: #ef4444;
    }

    &.resolved {
      background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
      color: #10b981;
    }

    &.high {
      background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
      color: #f59e0b;
    }
  }

  .stat-content {
    .stat-value {
      font-size: 28px;
      font-weight: 700;
      font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
      color: $text-primary;

      &.pending { color: #ef4444; }
      &.resolved { color: #10b981; }
      &.high { color: #f59e0b; }
    }

    .stat-label {
      font-size: 13px;
      color: $text-secondary;
      margin-top: 2px;
    }
  }
}

// 卡片样式
.card-container {
  margin-bottom: $spacing-lg;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-card;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
}

.header-filters {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.filter-select {
  width: 120px;
}

// 规则网格
.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: $spacing-md;
}

.rule-checkbox {
  margin: 0;
  padding: $spacing-sm $spacing-md;
  border: 1px solid $border-light;
  border-radius: $border-radius-md;
  transition: all 0.2s;

  &:hover {
    border-color: $primary-color;
    background: rgba($primary-color, 0.02);
  }

  &.is-checked {
    border-color: $primary-color;
    background: rgba($primary-color, 0.05);
  }
}

.rule-info {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.rule-name {
  font-weight: 500;
  color: $text-primary;
}

.rule-severity {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;

  &.critical {
    background: #fef2f2;
    color: #dc2626;
  }

  &.high {
    background: #fff7ed;
    color: #ea580c;
  }

  &.medium {
    background: #fefce8;
    color: #ca8a04;
  }

  &.low {
    background: #f0fdf4;
    color: #16a34a;
  }

  &.info {
    background: #eff6ff;
    color: #2563eb;
  }
}

// 预警表格
.alerts-table {
  width: 100%;

  :deep(.el-table__header th) {
    background: #f9fafb !important;
    font-weight: 600;
    color: #374151;
    font-size: 13px;
    padding: 16px;
  }

  :deep(.el-table__body td) {
    padding: 18px 16px;
    border-bottom: 1px solid #f3f4f6;
  }

  :deep(.el-table__row) {
    transition: background 0.15s;

    &:hover > td {
      background: #fafbfc !important;
    }
  }
}

.voucher-no {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-weight: 600;
  color: $primary-color;
}

.severity-tag {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;

  &.critical {
    background: #fef2f2;
    color: #dc2626;
  }

  &.high {
    background: #fff7ed;
    color: #ea580c;
  }

  &.medium {
    background: #fefce8;
    color: #ca8a04;
  }

  &.low {
    background: #f0fdf4;
    color: #16a34a;
  }

  &.info {
    background: #eff6ff;
    color: #2563eb;
  }
}

.resolved-text {
  color: $text-placeholder;
}

.empty-state {
  padding: 48px;
  text-align: center;
}
</style>
