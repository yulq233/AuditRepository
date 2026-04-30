<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
        <el-divider direction="vertical" />
        <h2 class="page-title">{{ record?.rule_name || '抽样详情' }}</h2>
      </div>
      <div class="header-actions">
        <el-dropdown @command="handleExport">
          <el-button type="primary">
            <el-icon><Download /></el-icon>
            导出结果
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="excel">导出Excel</el-dropdown-item>
              <el-dropdown-item command="pdf">导出PDF</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-section" v-loading="loading">
      <div class="stat-card">
        <div class="stat-icon total">
          <el-icon :size="24"><Document /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ record?.sample_size || 0 }}</div>
          <div class="stat-label">样本总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon high">
          <el-icon :size="24"><Warning /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value high">{{ record?.high_risk_count || 0 }}</div>
          <div class="stat-label">高风险</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon medium">
          <el-icon :size="24"><InfoFilled /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value medium">{{ record?.medium_risk_count || 0 }}</div>
          <div class="stat-label">中风险</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon low">
          <el-icon :size="24"><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value low">{{ record?.low_risk_count || 0 }}</div>
          <div class="stat-label">低风险</div>
        </div>
      </div>
    </div>

    <!-- 基本信息 -->
    <el-card class="card-container info-card">
      <template #header>
        <span class="card-title">基本信息</span>
      </template>
      <el-descriptions :column="4" border>
        <el-descriptions-item label="抽样类型">
          <el-tag :type="getRuleTypeTag(record?.rule_type)" size="small">
            {{ getRuleTypeName(record?.rule_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="抽样时间">{{ formatTime(record?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="record?.status === 'completed' ? 'success' : 'warning'" size="small">
            {{ record?.status === 'completed' ? '已完成' : '处理中' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="抽样比例">{{ samplingRate }}%</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 样本明细 -->
    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">样本明细</span>
          <el-input
            v-model="searchText"
            placeholder="搜索凭证号/摘要"
            class="search-input"
            clearable
            @clear="filterSamples"
            @keyup.enter="filterSamples"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
      </template>

      <el-table :data="filteredSamples" class="samples-table" v-loading="loading" fit>
        <el-table-column type="index" width="60" label="序号" align="center" />
        <el-table-column prop="voucher_no" label="凭证号" width="180" fixed="left" class-name="no-ellipsis">
          <template #default="{ row }">
            <span class="voucher-no">{{ row.voucher_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="subject_name" label="科目" width="150" show-overflow-tooltip />
        <el-table-column prop="amount" label="金额" width="160" align="right" class-name="no-ellipsis">
          <template #default="{ row }">
            <span :class="['amount-cell', { 'amount-large': row.amount > 100000 }]">
              {{ formatAmount(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="摘要" min-width="200" show-overflow-tooltip />
        <el-table-column prop="risk_score" label="风险分数" width="120" align="center">
          <template #default="{ row }">
            <div v-if="row.risk_score" class="risk-score-cell">
              <el-progress
                :percentage="row.risk_score"
                :color="getRiskColor(row.risk_score)"
                :stroke-width="6"
                :show-text="false"
                style="width: 60px"
              />
              <span class="risk-score-text" :style="{ color: getRiskColor(row.risk_score) }">
                {{ row.risk_score }}
              </span>
            </div>
            <span v-else class="no-risk">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险等级" width="100" align="center" class-name="risk-level-cell">
          <template #default="{ row }">
            <el-tag
              v-if="row.risk_level"
              :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'success'"
              size="small"
            >
              {{ row.risk_level === 'high' ? '高风险' : row.risk_level === 'medium' ? '中风险' : '低风险' }}
            </el-tag>
            <span v-else class="no-risk">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="risk_factors" label="风险因素" min-width="200" class-name="risk-factors-column">
          <template #default="{ row }">
            <div v-if="row.risk_factors && row.risk_factors.length > 0" class="risk-tags-wrap">
              <el-tag
                v-for="(factor, idx) in row.risk_factors"
                :key="idx"
                size="small"
                type="warning"
              >
                {{ factor }}
              </el-tag>
            </div>
            <span v-else class="no-risk">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="explanation" label="解释说明" min-width="390" class-name="explanation-column">
          <template #default="{ row }">
            <div v-if="row.explanation" class="ai-analysis-section">
              <div class="ai-explanation">
                <span class="ai-content">{{ row.explanation }}</span>
              </div>
            </div>
            <span v-else class="no-risk">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="抽取原因" width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewVoucher(row)">
              查看凭证
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-section">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[50, 100, 200]"
          layout="total, sizes, prev, pager, next"
          @size-change="handlePageSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 凭证详情对话框 -->
    <el-dialog
      v-model="voucherDialogVisible"
      title="凭证详情"
      width="700px"
      destroy-on-close
      class="voucher-dialog"
    >
      <el-descriptions :column="2" border v-if="currentVoucher">
        <el-descriptions-item label="凭证号">
          <span class="voucher-no">{{ currentVoucher.voucher_no }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="金额">
          <span class="amount-cell">{{ formatAmount(currentVoucher.amount) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="科目">{{ currentVoucher.subject_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="对方科目">{{ currentVoucher.counterparty || '-' }}</el-descriptions-item>
        <el-descriptions-item label="摘要" :span="2">{{ currentVoucher.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="风险分数">
          <div v-if="currentVoucher.risk_score" class="risk-score-cell">
            <el-progress
              :percentage="currentVoucher.risk_score"
              :color="getRiskColor(currentVoucher.risk_score)"
              :stroke-width="8"
              style="width: 120px"
            />
            <span class="risk-score-text" :style="{ color: getRiskColor(currentVoucher.risk_score) }">
              {{ currentVoucher.risk_score }}
            </span>
          </div>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="抽取原因">{{ currentVoucher.reason || '-' }}</el-descriptions-item>
      </el-descriptions>

      <!-- 附件列表 -->
      <div class="attachment-section">
        <div class="section-title">附件列表</div>
        <div v-if="loadingAttachments" class="loading-state">
          <el-icon class="is-loading"><Document /></el-icon>
          <span>加载中...</span>
        </div>
        <div v-else-if="currentVoucherAttachments.length === 0" class="empty-state">
          <span>暂无附件</span>
        </div>
        <div v-else class="attachment-list">
          <div v-for="att in currentVoucherAttachments" :key="att.id" class="attachment-item">
            <div class="att-icon">
              <el-icon :size="24" :color="getFileIconColor(att.file_type)">
                <component :is="getFileIcon(att.file_type)" />
              </el-icon>
            </div>
            <div class="att-info">
              <div class="att-name">{{ att.file_name }}</div>
              <div class="att-meta">{{ formatFileSize(att.file_size) }}</div>
            </div>
            <div class="att-actions">
              <el-button type="primary" link size="small" @click="previewAttachment(att)">预览</el-button>
              <el-button type="primary" link size="small" @click="downloadAttachment(att)">下载</el-button>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="voucherDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download, ArrowDown, Search, Document, Warning, InfoFilled, CircleCheck, Picture, Reading } from '@element-plus/icons-vue'
import { samplingApi, voucherApi } from '@/api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const record = ref(null)
const samples = ref([])
const searchText = ref('')
const voucherDialogVisible = ref(false)
const currentVoucher = ref(null)
const currentVoucherAttachments = ref([])
const loadingAttachments = ref(false)

const pagination = reactive({
  page: 1,
  pageSize: 50,
  total: 0
})

const projectId = computed(() => route.query.projectId)
const recordId = computed(() => route.query.recordId)

// 过滤后的样本
const filteredSamples = computed(() => {
  let result = samples.value
  if (searchText.value) {
    const keyword = searchText.value.toLowerCase()
    result = result.filter(s =>
      (s.voucher_no && s.voucher_no.toLowerCase().includes(keyword)) ||
      (s.description && s.description.toLowerCase().includes(keyword)) ||
      (s.subject_name && s.subject_name.toLowerCase().includes(keyword))
    )
  }
  pagination.total = result.length
  const start = (pagination.page - 1) * pagination.pageSize
  return result.slice(start, start + pagination.pageSize)
})

// 抽样比例
const samplingRate = computed(() => {
  if (!record.value) return 0
  // 假设项目有1000张凭证
  return Math.round((record.value.sample_size / 1000) * 100 * 100) / 100
})

const getRuleTypeName = (type) => {
  const types = {
    'random': '随机抽样',
    'amount': '金额抽样',
    'subject': '科目抽样',
    'date': '日期抽样',
    'stratified': '分层抽样',
    'ai': 'AI智能抽样'
  }
  return types[type] || type
}

const getRuleTypeTag = (type) => {
  const tags = {
    'random': '',
    'amount': 'success',
    'subject': 'warning',
    'date': 'info',
    'stratified': 'warning',
    'ai': 'danger'
  }
  return tags[type] || ''
}

const formatTime = (time) => {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

const formatAmount = (amount) => {
  if (!amount) return '0.00'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

const getRiskColor = (score) => {
  if (score >= 70) return '#ef4444'
  if (score >= 50) return '#f59e0b'
  return '#10b981'
}

const getAttachmentUrl = (path) => {
  if (!path) return ''
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000'
  return `${baseUrl}/uploads/${path}`
}

const formatFileSize = (size) => {
  if (!size) return '0 B'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / (1024 * 1024)).toFixed(1) + ' MB'
}

const getFileIcon = (type) => {
  if (['.jpg', '.jpeg', '.png', '.bmp'].includes(type)) return Picture
  if (type === '.pdf') return Reading
  return Document
}

const getFileIconColor = (type) => {
  if (['.jpg', '.jpeg', '.png', '.bmp'].includes(type)) return '#10b981'
  if (type === '.pdf') return '#ef4444'
  return '#6366f1'
}

const previewAttachment = (att) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000'
  const url = `${baseUrl}/api/files/${att.file_path}`

  if (['.jpg', '.jpeg', '.png', '.bmp'].includes(att.file_type)) {
    // 图片类型，使用el-image预览（简化处理，直接打开新窗口）
    window.open(url, '_blank')
  } else {
    window.open(url, '_blank')
  }
}

const downloadAttachment = (att) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000'
  const url = `${baseUrl}/api/files/${att.file_path}`
  window.open(url, '_blank')
}

const loadDetail = async () => {
  if (!projectId.value || !recordId.value) {
    ElMessage.error('缺少必要参数')
    return
  }

  loading.value = true
  try {
    const res = await samplingApi.getRecordDetail(projectId.value, recordId.value)
    record.value = res.record
    samples.value = res.samples || []
    pagination.total = samples.value.length
  } catch (error) {
    console.error(error)
    ElMessage.error('加载详情失败')
  } finally {
    loading.value = false
  }
}

const filterSamples = () => {
  pagination.page = 1
}

const handlePageChange = (page) => {
  pagination.page = page
}

const handlePageSizeChange = (size) => {
  pagination.pageSize = size
  pagination.page = 1
}

const viewVoucher = async (sample) => {
  currentVoucher.value = sample
  currentVoucherAttachments.value = []
  voucherDialogVisible.value = true

  // 加载附件列表
  if (sample.voucher_id) {
    loadingAttachments.value = true
    try {
      const attachments = await voucherApi.getAttachments(projectId.value, sample.voucher_id)
      currentVoucherAttachments.value = attachments || []
    } catch (error) {
      console.error('获取附件列表失败:', error)
      currentVoucherAttachments.value = []
    } finally {
      loadingAttachments.value = false
    }
  }
}

const handleExport = async (format) => {
  try {
    ElMessage.info('正在导出...')
    const blob = await samplingApi.exportRecord(projectId.value, recordId.value, format)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const ext = format === 'pdf' ? 'pdf' : 'xlsx'
    link.download = `抽样结果_${record.value?.rule_name || ''}_${new Date().toISOString().slice(0, 10)}.${ext}`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('导出失败')
  }
}

const goBack = () => {
  router.push('/sampling/results')
}

onMounted(() => {
  loadDetail()
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

// 页面头部
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;
  padding-bottom: $spacing-lg;
  border-bottom: 1px solid $border-light;
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: $text-primary;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

// 统计卡片区域
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

    &.high {
      background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
      color: #ef4444;
    }

    &.medium {
      background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
      color: #f59e0b;
    }

    &.low {
      background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
      color: #10b981;
    }
  }

  .stat-content {
    .stat-value {
      font-size: 28px;
      font-weight: 700;
      font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
      color: $text-primary;

      &.high { color: #ef4444; }
      &.medium { color: #f59e0b; }
      &.low { color: #10b981; }
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

.info-card {
  margin-bottom: $spacing-lg;
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

.search-input {
  width: 240px;
}

// 样本表格样式
.samples-table {
  width: 100%;

  :deep(.el-table__header th) {
    background: #f9fafb !important;
    font-weight: 600;
    color: #374151;
    font-size: 13px;
    padding: 16px;

    .cell {
      white-space: nowrap;
      overflow: visible;
    }
  }

  :deep(.el-table__body td) {
    padding: 18px 16px;
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

  // 凭证号和金额列不显示省略号
  :deep(.no-ellipsis) .cell {
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
  }

  // 风险因素列 - 标签横向排列
  :deep(.risk-factors-column) {
    .cell {
      overflow: visible !important;
      text-overflow: clip !important;
    }
  }
}

.voucher-no {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-weight: 600;
  color: $primary-color;
}

.amount-cell {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-weight: 500;

  &.amount-large {
    color: #ef4444;
    font-weight: 700;
  }
}

// 风险分数
.risk-score-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}

.risk-score-text {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-weight: 600;
  font-size: 13px;
}

.no-risk {
  color: $text-placeholder;
}

// 风险等级列 - 显示完整内容
:deep(.risk-level-cell) .cell {
  white-space: nowrap !important;
  overflow: visible !important;
  text-overflow: clip !important;
}

/* 风险标签换行显示 - 与风险画像样式一致 */
.risk-tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  line-height: 1.8;
}

.risk-tags-wrap .el-tag {
  flex-shrink: 0;
}

/* 解释说明列 - AI分析区域样式 */
.ai-analysis-section {
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 4px;
  padding: 8px 10px;
  line-height: 1.6;
  font-size: 13px;
}

.ai-explanation {
  color: #b88230;
  line-height: 1.5;
  word-break: break-word;
}

.ai-explanation .ai-content {
  display: block;
  word-break: break-word;
  white-space: pre-wrap;
}

// 解释说明列 - 显示完整内容
:deep(.explanation-column) .cell {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  word-break: break-word;
}

// 分页
.pagination-section {
  margin-top: $spacing-lg;
  display: flex;
  justify-content: flex-end;
}

// 附件列表
.attachment-section {
  margin-top: $spacing-lg;
  border-top: 1px solid $border-light;
  padding-top: $spacing-md;

  .section-title {
    font-size: 14px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: $spacing-md;
  }

  .loading-state,
  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 24px;
    color: $text-secondary;
    background: #f9fafb;
    border-radius: $border-radius-md;
  }

  .attachment-list {
    max-height: 300px;
    overflow-y: auto;
  }

  .attachment-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border: 1px solid $border-light;
    border-radius: $border-radius-md;
    margin-bottom: 8px;
    transition: all 0.15s;

    &:hover {
      border-color: $border-color;
      background: #fafafa;
    }

    .att-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f3f4f6;
      border-radius: $border-radius-md;
    }

    .att-info {
      flex: 1;
      min-width: 0;

      .att-name {
        font-size: 14px;
        color: $text-primary;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .att-meta {
        font-size: 12px;
        color: $text-secondary;
        margin-top: 2px;
      }
    }

    .att-actions {
      display: flex;
      gap: 4px;
    }
  }
}

// 凭证对话框
.voucher-dialog {
  :deep(.el-descriptions__label) {
    font-weight: 600;
    color: #374151;
  }
}
</style>
