<template>
  <div class="voucher-page">
    <!-- 页面标题区 -->
    <div class="page-title-section">
      <div class="title-content">
        <h1 class="main-title">凭证管理</h1>
        <p class="sub-title">管理审计项目的凭证数据</p>
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
        <el-button type="primary" class="import-btn" @click="showImportDialog" :disabled="!projectId">
          <el-icon><Upload /></el-icon>
          导入凭证
        </el-button>
      </div>
    </div>

    <!-- 筛选区域 -->
    <div class="filter-section" v-if="projectId">
      <div class="filter-row">
        <div class="filter-item">
          <label class="filter-label">科目代码</label>
          <el-input
            v-model="filterForm.subject_code"
            placeholder="请输入"
            clearable
            class="filter-input"
          />
        </div>
        <div class="filter-item">
          <label class="filter-label">金额范围</label>
          <div class="range-inputs">
            <el-input-number
              v-model="filterForm.min_amount"
              placeholder="最小"
              :controls="false"
              class="range-input"
            />
            <span class="range-separator">至</span>
            <el-input-number
              v-model="filterForm.max_amount"
              placeholder="最大"
              :controls="false"
              class="range-input"
            />
          </div>
        </div>
        <div class="filter-item">
          <label class="filter-label">关键词</label>
          <el-input
            v-model="filterForm.keyword"
            placeholder="凭证号/摘要"
            clearable
            class="filter-input"
          />
        </div>
        <div class="filter-actions">
          <el-button type="primary" @click="loadVouchers">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </div>
      </div>
    </div>

    <!-- 数据表格区域 -->
    <div class="table-section">
      <!-- 表格工具栏 -->
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="data-count">共 {{ pagination.total }} 条数据</span>
          <el-button
            type="danger"
            plain
            size="small"
            @click="batchDelete"
            :disabled="!selectedVouchers.length"
          >
            <el-icon><Delete /></el-icon>
            批量删除 ({{ selectedVouchers.length }})
          </el-button>
        </div>
      </div>

      <!-- 表格 -->
      <div class="table-container">
        <el-table
          :data="vouchers"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          :row-class-name="getRowClass"
          class="voucher-table"
        >
          <el-table-column type="selection" width="50" fixed="left" align="center" />
          <el-table-column prop="voucher_no" label="凭证号" width="130" fixed="left" show-overflow-tooltip />
          <el-table-column prop="voucher_date" label="日期" width="100" show-overflow-tooltip />
          <el-table-column prop="subject_code" label="科目代码" width="100" show-overflow-tooltip />
          <el-table-column prop="subject_name" label="科目名称" width="140" show-overflow-tooltip />
          <el-table-column prop="amount" label="金额" width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="['amount', getAmountClass(row.amount)]">
                {{ formatAmount(row.amount) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="counterparty" label="交易对手" min-width="180" show-overflow-tooltip />
          <el-table-column prop="description" label="摘要" min-width="200" show-overflow-tooltip />
          <el-table-column label="附件" width="120" align="center">
            <template #default="{ row }">
              <el-badge :value="row.attachment_count || 0" :hidden="!row.attachment_count" :max="99">
                <el-button
                  :type="row.attachment_count ? 'primary' : 'default'"
                  size="small"
                  @click="showAttachmentDialog(row)"
                  :icon="Paperclip"
                  circle
                />
              </el-badge>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="editVoucher(row)">编辑</el-button>
              <el-button type="primary" link size="small" @click="viewDetail(row)">详情</el-button>
              <el-button type="danger" link size="small" @click="confirmDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 分页 -->
      <div class="pagination-section">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadVouchers"
          @current-change="loadVouchers"
        />
      </div>
    </div>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入凭证"
      width="560px"
      class="import-dialog"
      destroy-on-close
    >
      <div class="import-tips">
        <div class="tips-header">
          <el-icon class="tips-icon"><InfoFilled /></el-icon>
          <span>导入说明</span>
        </div>
        <div class="tips-content">
          <p>支持列名：<b>凭证编号*</b>、凭证日期、金额、科目代码、科目名称、摘要、交易对手</p>
          <p>日期格式：YYYY-MM-DD、YYYY/MM/DD、YYYY.MM.DD</p>
        </div>
      </div>

      <div class="template-download">
        <el-button type="primary" link @click="downloadTemplate">
          <el-icon><Download /></el-icon>
          下载导入模板
        </el-button>
        <span class="template-hint">CSV格式，可用Excel编辑</span>
      </div>

      <el-upload
        ref="importUploadRef"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls,.csv"
        :on-change="handleFileChange"
        :file-list="importFileList"
        class="upload-area"
      >
        <div class="upload-content">
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <p class="upload-text">将文件拖到此处，或<em>点击上传</em></p>
          <p class="upload-hint">支持 Excel 和 CSV 格式，单次最多1000条</p>
        </div>
      </el-upload>

      <div v-if="importResult" class="import-result">
        <div class="result-title">导入结果</div>
        <div class="result-stats">
          <div class="stat-item success">
            <span class="stat-num">{{ importResult.success }}</span>
            <span class="stat-label">成功</span>
          </div>
          <div class="stat-item" :class="{ error: importResult.failed > 0 }">
            <span class="stat-num">{{ importResult.failed }}</span>
            <span class="stat-label">失败</span>
          </div>
          <div class="stat-item">
            <span class="stat-num">{{ importResult.success + importResult.failed }}</span>
            <span class="stat-label">总计</span>
          </div>
        </div>
        <el-collapse v-if="importResult.errors?.length">
          <el-collapse-item title="查看错误详情" name="errors">
            <div v-for="(error, idx) in importResult.errors" :key="idx" class="error-text">{{ error }}</div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <template #footer>
        <el-button @click="closeImportDialog">取消</el-button>
        <el-button type="primary" :loading="importing" @click="importVouchers" :disabled="!uploadFile">
          开始导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 附件管理对话框 -->
    <el-dialog
      v-model="attachmentDialogVisible"
      width="640px"
      class="attachment-dialog"
      destroy-on-close
    >
      <template #header>
        <div class="dialog-title-row">
          <span class="dialog-title">附件管理</span>
          <span class="voucher-tag">凭证：{{ attachmentTarget?.voucher_no }}</span>
        </div>
      </template>

      <div class="upload-row">
        <el-upload
          ref="attachmentUploadRef"
          :auto-upload="false"
          :show-file-list="false"
          accept=".pdf,.jpg,.jpeg,.png,.bmp"
          multiple
          :on-change="handleAttachmentSelect"
        >
          <el-button type="primary">
            <el-icon><Plus /></el-icon>
            添加附件
          </el-button>
        </el-upload>
        <span class="upload-hint">支持 PDF、JPG、PNG、BMP</span>
      </div>

      <div v-if="pendingFiles.length > 0" class="pending-section">
        <div class="pending-header">
          <span>待上传 ({{ pendingFiles.length }})</span>
          <el-button type="primary" size="small" :loading="uploading" @click="submitAttachments">
            全部上传
          </el-button>
        </div>
        <div class="pending-list">
          <div v-for="(file, index) in pendingFiles" :key="index" class="pending-item">
            <el-icon><Document /></el-icon>
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatFileSize(file.size) }}</span>
            <el-button type="danger" link size="small" @click="removePendingFile(index)">移除</el-button>
          </div>
        </div>
      </div>

      <div class="attachment-list-section">
        <div class="section-title">已上传 ({{ attachments.length }})</div>
        <div v-if="attachmentsLoading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
        <div v-else-if="attachments.length === 0" class="empty-state">
          <el-empty description="暂无附件" :image-size="48" />
        </div>
        <div v-else class="attachment-list">
          <div v-for="att in attachments" :key="att.id" class="attachment-item">
            <div class="att-icon">
              <el-icon :size="24" :color="getFileIconColor(att.file_type)">
                <component :is="getFileIcon(att.file_type)" />
              </el-icon>
            </div>
            <div class="att-info">
              <div class="att-name">{{ att.file_name }}</div>
              <div class="att-meta">{{ formatFileSize(att.file_size) }} · {{ formatTime(att.uploaded_at) }}</div>
            </div>
            <div class="att-actions">
              <el-button type="primary" link size="small" @click="previewAttachment(att)">预览</el-button>
              <el-button type="primary" link size="small" @click="downloadAttachment(att)">下载</el-button>
              <el-popconfirm title="确定删除？" @confirm="deleteAttachment(att.id)">
                <template #reference>
                  <el-button type="danger" link size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- AI识别结果对话框 -->
    <el-dialog v-model="aiResultDialogVisible" title="AI识别结果" width="520px">
      <el-descriptions :column="2" border v-if="aiResult">
        <el-descriptions-item label="凭证编号">{{ aiResult.voucher_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="凭证日期">{{ aiResult.voucher_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ aiResult.amount || '-' }}</el-descriptions-item>
        <el-descriptions-item label="交易对手">{{ aiResult.counterparty || '-' }}</el-descriptions-item>
        <el-descriptions-item label="业务摘要" :span="2">{{ aiResult.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="建议科目">{{ aiResult.subject_suggestion || '-' }}</el-descriptions-item>
        <el-descriptions-item label="置信度">
          <el-progress :percentage="(aiResult.confidence || 0) * 100" :stroke-width="8" />
        </el-descriptions-item>
        <el-descriptions-item label="风险点" :span="2">
          <el-tag
            v-for="(point, index) in (aiResult.risk_points || [])"
            :key="index"
            type="warning"
            size="small"
          >
            {{ point }}
          </el-tag>
          <span v-if="!aiResult.risk_points?.length">无</span>
        </el-descriptions-item>
        <el-descriptions-item label="关键信息" :span="2">{{ aiResult.key_info || '-' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="aiResultDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 图片预览 -->
    <el-dialog v-model="imagePreviewVisible" title="图片预览" width="720px">
      <el-image :src="previewImageUrl" fit="contain" style="width: 100%;" />
    </el-dialog>

    <!-- 编辑凭证对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑凭证"
      width="560px"
      class="edit-dialog"
      destroy-on-close
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="90px"
        class="edit-form"
      >
        <el-form-item label="凭证编号" prop="voucher_no">
          <el-input v-model="editForm.voucher_no" placeholder="请输入凭证编号" />
        </el-form-item>
        <el-form-item label="凭证日期" prop="voucher_date">
          <el-date-picker
            v-model="editForm.voucher_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input-number
            v-model="editForm.amount"
            :precision="2"
            :min="0"
            :controls="false"
            placeholder="请输入金额"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="科目代码" prop="subject_code">
          <el-input v-model="editForm.subject_code" placeholder="请输入科目代码" />
        </el-form-item>
        <el-form-item label="科目名称" prop="subject_name">
          <el-input v-model="editForm.subject_name" placeholder="请输入科目名称" />
        </el-form-item>
        <el-form-item label="交易对手" prop="counterparty">
          <el-input v-model="editForm.counterparty" placeholder="请输入交易对手" />
        </el-form-item>
        <el-form-item label="摘要" prop="description">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入摘要"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="saveVoucher">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Delete, Upload, UploadFilled, Document, Download, Paperclip,
  Plus, View, Picture, Reading, Loading, InfoFilled, Edit
} from '@element-plus/icons-vue'
import { voucherApi, projectApi } from '@/api'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const importing = ref(false)
const uploading = ref(false)
const attachmentsLoading = ref(false)
const importDialogVisible = ref(false)
const attachmentDialogVisible = ref(false)
const aiResultDialogVisible = ref(false)
const imagePreviewVisible = ref(false)
const uploadFile = ref(null)
const attachmentTarget = ref(null)
const selectedVouchers = ref([])
const aiResult = ref(null)
const importUploadRef = ref(null)
const attachmentUploadRef = ref(null)
const importResult = ref(null)
const importFileList = ref([])
const attachments = ref([])
const pendingFiles = ref([])
const previewImageUrl = ref('')

// 编辑相关
const editDialogVisible = ref(false)
const editLoading = ref(false)
const editFormRef = ref(null)
const editForm = reactive({
  id: '',
  project_id: '',
  voucher_no: '',
  voucher_date: null,
  amount: null,
  subject_code: '',
  subject_name: '',
  description: '',
  counterparty: ''
})
const editRules = {
  voucher_no: [{ required: true, message: '请输入凭证编号', trigger: 'blur' }]
}

const projects = ref([])
const projectId = ref(localStorage.getItem('currentProjectId') || '')

const filterForm = reactive({
  subject_code: '',
  min_amount: null,
  max_amount: null,
  keyword: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const vouchers = ref([])

const formatAmount = (amount) => {
  if (!amount) return '0.00'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

const formatFileSize = (size) => {
  if (!size) return '0 B'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const getAmountClass = (amount) => {
  if (!amount) return ''
  if (amount >= 100000) return 'amount-danger'
  if (amount >= 10000) return 'amount-warning'
  return ''
}

const getRowClass = ({ row }) => {
  if (row.amount >= 100000) return 'row-highlight'
  return ''
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

const loadVouchers = async () => {
  if (!projectId.value) {
    vouchers.value = []
    pagination.total = 0
    return
  }

  loading.value = true
  try {
    const res = await voucherApi.getList(projectId.value, {
      page: pagination.page,
      page_size: pagination.pageSize,
      ...filterForm
    })
    vouchers.value = res.items || []
    pagination.total = res.total || 0

    for (const v of vouchers.value) {
      try {
        const atts = await voucherApi.getAttachments(projectId.value, v.id)
        v.attachment_count = atts.length || 0
      } catch {
        v.attachment_count = 0
      }
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const resetFilter = () => {
  Object.assign(filterForm, {
    subject_code: '',
    min_amount: null,
    max_amount: null,
    keyword: ''
  })
  pagination.page = 1
  loadVouchers()
}

const handleSelectionChange = (selection) => {
  selectedVouchers.value = selection
}

const showImportDialog = () => {
  uploadFile.value = null
  importResult.value = null
  importFileList.value = []
  importDialogVisible.value = true
}

const handleFileChange = (file) => {
  uploadFile.value = file.raw
  importResult.value = null
}

const downloadTemplate = () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000'
  const url = `${baseUrl}/api/projects/${projectId.value}/vouchers/import-template`
  window.open(url, '_blank')
}

const closeImportDialog = () => {
  importDialogVisible.value = false
  if (importResult.value && importResult.value.success > 0) {
    loadVouchers()
  }
}

const importVouchers = async () => {
  if (!uploadFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  importing.value = true
  importResult.value = null
  try {
    const res = await voucherApi.import(projectId.value, uploadFile.value)
    importResult.value = res

    if (res.success > 0 && res.failed === 0) {
      ElMessage.success(`成功导入 ${res.success} 条凭证`)
    } else if (res.success > 0 && res.failed > 0) {
      ElMessage.warning(`导入完成：成功 ${res.success} 条，失败 ${res.failed} 条`)
    } else if (res.failed > 0) {
      ElMessage.error(`导入失败：${res.failed} 条记录无法导入`)
    }
  } catch (error) {
    ElMessage.error('导入失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    importing.value = false
  }
}

// 编辑凭证
const editVoucher = (voucher) => {
  // 填充表单
  editForm.id = voucher.id
  editForm.project_id = voucher.project_id
  editForm.voucher_no = voucher.voucher_no
  editForm.voucher_date = voucher.voucher_date
  editForm.amount = voucher.amount
  editForm.subject_code = voucher.subject_code || ''
  editForm.subject_name = voucher.subject_name || ''
  editForm.description = voucher.description || ''
  editForm.counterparty = voucher.counterparty || ''
  editDialogVisible.value = true
}

// 保存凭证
const saveVoucher = async () => {
  if (!editFormRef.value) return

  try {
    await editFormRef.value.validate()
  } catch {
    return
  }

  editLoading.value = true
  try {
    const updateData = {
      voucher_no: editForm.voucher_no,
      voucher_date: editForm.voucher_date,
      amount: editForm.amount,
      subject_code: editForm.subject_code || null,
      subject_name: editForm.subject_name || null,
      description: editForm.description || null,
      counterparty: editForm.counterparty || null
    }

    await voucherApi.update(editForm.project_id, editForm.id, updateData)
    ElMessage.success('凭证更新成功')
    editDialogVisible.value = false
    loadVouchers()
  } catch (error) {
    ElMessage.error('更新失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    editLoading.value = false
  }
}

const viewDetail = (voucher) => {
  // 使用凭证自身的project_id，确保跳转正确
  router.push(`/vouchers/${voucher.project_id}/${voucher.id}`)
}

const showAttachmentDialog = async (voucher) => {
  attachmentTarget.value = voucher
  pendingFiles.value = []
  attachmentDialogVisible.value = true
  await loadAttachments()
}

const loadAttachments = async () => {
  if (!attachmentTarget.value) return

  attachmentsLoading.value = true
  try {
    attachments.value = await voucherApi.getAttachments(projectId.value, attachmentTarget.value.id)
  } catch (error) {
    console.error(error)
    attachments.value = []
  } finally {
    attachmentsLoading.value = false
  }
}

const handleAttachmentSelect = (file) => {
  pendingFiles.value.push(file.raw)
}

const removePendingFile = (index) => {
  pendingFiles.value.splice(index, 1)
}

const submitAttachments = async () => {
  if (pendingFiles.value.length === 0) return

  uploading.value = true
  try {
    await voucherApi.uploadAttachments(projectId.value, attachmentTarget.value.id, pendingFiles.value)
    ElMessage.success(`成功上传 ${pendingFiles.value.length} 个附件`)
    pendingFiles.value = []
    await loadAttachments()
    const voucher = vouchers.value.find(v => v.id === attachmentTarget.value.id)
    if (voucher) {
      voucher.attachment_count = attachments.value.length
    }
  } catch (error) {
    ElMessage.error('上传失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    uploading.value = false
  }
}

const previewAttachment = (att) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000'
  const url = `${baseUrl}/api/files/${att.file_path}`

  if (['.jpg', '.jpeg', '.png', '.bmp'].includes(att.file_type)) {
    previewImageUrl.value = url
    imagePreviewVisible.value = true
  } else {
    window.open(url, '_blank')
  }
}

const downloadAttachment = (att) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000'
  const url = `${baseUrl}/api/files/${att.file_path}`
  window.open(url, '_blank')
}

const deleteAttachment = async (attachmentId) => {
  try {
    await voucherApi.deleteAttachment(projectId.value, attachmentTarget.value.id, attachmentId)
    ElMessage.success('附件已删除')
    await loadAttachments()
    const voucher = vouchers.value.find(v => v.id === attachmentTarget.value.id)
    if (voucher) {
      voucher.attachment_count = attachments.value.length
    }
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const aiRecognize = async (voucher) => {
  try {
    ElMessage.info('正在进行AI识别...')
    const res = await voucherApi.aiRecognize(projectId.value, voucher.id)

    if (typeof res.result === 'string') {
      try {
        aiResult.value = JSON.parse(res.result)
      } catch {
        aiResult.value = { key_info: res.result }
      }
    } else {
      aiResult.value = res.result
    }

    aiResultDialogVisible.value = true
    ElMessage.success('AI识别完成')
  } catch (error) {
    ElMessage.error('AI识别失败: ' + (error.response?.data?.detail || error.message))
  }
}

const confirmDelete = async (voucher) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除凭证 "${voucher.voucher_no}" 吗？`,
      '删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )

    await voucherApi.delete(projectId.value, voucher.id)
    ElMessage.success('删除成功')
    loadVouchers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const batchDelete = async () => {
  if (!selectedVouchers.value.length) {
    ElMessage.warning('请先选择要删除的凭证')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedVouchers.value.length} 条凭证吗？`,
      '批量删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )

    const voucherIds = selectedVouchers.value.map(v => v.id)
    const res = await voucherApi.batchDelete(projectId.value, voucherIds)

    if (res.errors && res.errors.length > 0) {
      ElMessage.warning(res.message + '，部分凭证删除失败')
      console.error('删除失败的凭证:', res.errors)
    } else {
      ElMessage.success(res.message)
    }

    selectedVouchers.value = []
    loadVouchers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const loadProjects = async () => {
  try {
    const res = await projectApi.getList({ page: 1, page_size: 100 })
    projects.value = res.items || []

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
  pagination.page = 1
  selectedVouchers.value = []
  loadVouchers()
}

onMounted(async () => {
  await loadProjects()
  if (projectId.value) {
    loadVouchers()
  }
})
</script>

<style lang="scss" scoped>
// =============================================
// Pixso 现代简约风格 - 凭证管理页面
// =============================================

.voucher-page {
  min-height: 100%;
  background: #f5f7fa;
  padding: 24px;
}

// 页面标题区
.page-title-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.title-content {
  .main-title {
    font-size: 24px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 4px 0;
  }

  .sub-title {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }
}

.title-actions {
  display: flex;
  gap: 12px;

  .project-select {
    width: 200px;
  }

  .import-btn {
    :deep(.el-icon) {
      margin-right: 6px;
    }
  }
}

// 筛选区域
.filter-section {
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.filter-row {
  display: flex;
  align-items: flex-end;
  gap: 24px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 6px;

  .filter-label {
    font-size: 13px;
    color: #6b7280;
    font-weight: 500;
  }

  .filter-input {
    width: 160px;
  }

  .range-inputs {
    display: flex;
    align-items: center;
    gap: 8px;

    .range-input {
      width: 100px;
    }

    .range-separator {
      color: #9ca3af;
      font-size: 13px;
    }
  }
}

.filter-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
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
  }
}

.table-container {
  padding: 0;
  overflow-x: auto;

  :deep(.voucher-table) {
    --el-table-border-color: #f3f4f6;
    --el-table-header-bg-color: #f9fafb;

    th.el-table__cell {
      font-size: 13px;
      font-weight: 600;
      color: #374151;
      background: #f9fafb !important;

      .cell {
        padding: 0 12px;
      }
    }

    td.el-table__cell {
      font-size: 14px;
      color: #4b5563;

      .cell {
        padding: 0 12px;
      }
    }

    // 附件列 - 允许badge完全显示
    td.el-table__cell:last-child,
    td.el-table__cell:nth-last-child(2) {
      .cell {
        overflow: visible;
      }
    }

    tr:hover td.el-table__cell {
      background: #f9fafb !important;
    }

    .row-highlight {
      td.el-table__cell {
        background: #fef2f2 !important;
      }
    }

    .amount {
      font-family: 'SF Mono', 'Monaco', Consolas, monospace;
      font-weight: 500;

      &.amount-danger {
        color: #ef4444;
        font-weight: 600;
      }

      &.amount-warning {
        color: #f59e0b;
      }
    }

    .el-table__fixed,
    .el-table__fixed-right {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
  }
}

.pagination-section {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid #f3f4f6;
}

// 导入对话框
.import-dialog {
  .import-tips {
    background: #f0f9ff;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 16px;

    .tips-header {
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 600;
      color: #0369a1;
      margin-bottom: 8px;

      .tips-icon {
        font-size: 16px;
      }
    }

    .tips-content {
      font-size: 13px;
      color: #0c4a6e;
      line-height: 1.6;

      p {
        margin: 4px 0;
      }

      b {
        color: #0369a1;
      }
    }
  }

  .template-download {
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;

    .template-hint {
      font-size: 12px;
      color: #9ca3af;
    }
  }

  .upload-area {
    :deep(.el-upload-dragger) {
      border: 2px dashed #e5e7eb;
      border-radius: 12px;
      background: #fafafa;
      transition: all 0.2s;

      &:hover {
        border-color: #6366f1;
        background: #f5f3ff;
      }
    }

    .upload-content {
      padding: 24px;

      .upload-icon {
        font-size: 40px;
        color: #9ca3af;
        margin-bottom: 8px;
      }

      .upload-text {
        font-size: 14px;
        color: #4b5563;
        margin: 0;

        em {
          color: #6366f1;
          font-style: normal;
        }
      }

      .upload-hint {
        font-size: 12px;
        color: #9ca3af;
        margin: 8px 0 0 0;
      }
    }
  }

  .import-result {
    margin-top: 20px;

    .result-title {
      font-size: 14px;
      font-weight: 600;
      color: #374151;
      margin-bottom: 12px;
    }

    .result-stats {
      display: flex;
      gap: 12px;
      margin-bottom: 16px;

      .stat-item {
        flex: 1;
        text-align: center;
        padding: 16px;
        background: #f9fafb;
        border-radius: 8px;
        border: 1px solid #e5e7eb;

        &.success {
          background: #f0fdf4;
          border-color: #bbf7d0;

          .stat-num {
            color: #16a34a;
          }
        }

        &.error {
          background: #fef2f2;
          border-color: #fecaca;

          .stat-num {
            color: #ef4444;
          }
        }

        .stat-num {
          font-size: 28px;
          font-weight: 700;
          color: #374151;
          line-height: 1;
        }

        .stat-label {
          font-size: 12px;
          color: #6b7280;
          margin-top: 4px;
        }
      }
    }

    .error-text {
      padding: 8px 0;
      font-size: 13px;
      color: #ef4444;
      border-bottom: 1px dashed #f3f4f6;

      &:last-child {
        border-bottom: none;
      }
    }
  }
}

// 附件对话框
.attachment-dialog {
  .dialog-title-row {
    display: flex;
    align-items: center;
    gap: 12px;

    .dialog-title {
      font-size: 16px;
      font-weight: 600;
    }

    .voucher-tag {
      font-size: 12px;
      color: #6b7280;
      background: #f3f4f6;
      padding: 2px 10px;
      border-radius: 12px;
    }
  }

  .upload-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: #f9fafb;
    border-radius: 8px;
    margin-bottom: 16px;

    .upload-hint {
      font-size: 12px;
      color: #9ca3af;
    }
  }

  .pending-section {
    margin-bottom: 16px;

    .pending-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: #fef3c7;
      border-radius: 6px;
      margin-bottom: 8px;
      font-size: 13px;
      color: #b45309;
      font-weight: 500;
    }

    .pending-list {
      max-height: 150px;
      overflow-y: auto;
    }

    .pending-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 6px;
      margin-bottom: 6px;
      font-size: 13px;

      .file-name {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .file-size {
        color: #9ca3af;
        font-size: 12px;
      }
    }
  }

  .attachment-list-section {
    .section-title {
      font-size: 14px;
      font-weight: 600;
      color: #374151;
      margin-bottom: 12px;
    }

    .loading-state,
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px;
      color: #9ca3af;
      gap: 8px;
      background: #f9fafb;
      border-radius: 8px;
    }

    .attachment-list {
      max-height: 320px;
      overflow-y: auto;
    }

    .attachment-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      border: 1px solid #f3f4f6;
      border-radius: 8px;
      margin-bottom: 8px;
      transition: all 0.15s;

      &:hover {
        border-color: #e5e7eb;
        background: #fafafa;
      }

      .att-icon {
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f3f4f6;
        border-radius: 8px;
      }

      .att-info {
        flex: 1;
        min-width: 0;

        .att-name {
          font-size: 14px;
          color: #374151;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .att-meta {
          font-size: 12px;
          color: #9ca3af;
          margin-top: 2px;
        }
      }

      .att-actions {
        display: flex;
        gap: 4px;
      }
    }
  }
}

// 编辑凭证对话框样式
.edit-dialog {
  .edit-form {
    padding: 10px 20px 0;
  }
}
</style>
