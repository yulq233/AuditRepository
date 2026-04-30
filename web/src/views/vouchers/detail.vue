<template>
  <div class="page-container page-enter">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
        <el-divider direction="vertical" />
        <h2 class="page-title">凭证详情</h2>
      </div>
    </div>

    <!-- 凭证基本信息 -->
    <el-card class="card-container info-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">基本信息</span>
          <el-button type="primary" @click="editVoucher">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
        </div>
      </template>

      <el-descriptions :column="3" border v-loading="loading">
        <el-descriptions-item label="凭证号">
          <span class="voucher-no">{{ voucher?.voucher_no }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="凭证日期">{{ voucher?.voucher_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="金额">
          <span :class="['amount-cell', getAmountClass(voucher?.amount)]">
            {{ formatAmount(voucher?.amount) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="科目代码">{{ voucher?.subject_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="科目名称">{{ voucher?.subject_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="交易对手">{{ voucher?.counterparty || '-' }}</el-descriptions-item>
        <el-descriptions-item label="摘要" :span="3">{{ voucher?.description || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 附件管理 -->
    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">附件管理</span>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :show-file-list="false"
            accept=".pdf,.jpg,.jpeg,.png,.bmp"
            multiple
            :on-change="handleFileSelect"
          >
            <el-button type="primary">
              <el-icon><Plus /></el-icon>
              上传附件
            </el-button>
          </el-upload>
        </div>
      </template>

      <el-table :data="attachments" v-loading="attachmentsLoading" class="attachment-table">
        <el-table-column label="文件名" min-width="220">
          <template #default="{ row }">
            <div class="file-name-cell">
              <el-icon :size="20" :color="getFileIconColor(row.file_type)">
                <component :is="getFileIcon(row.file_type)" />
              </el-icon>
              <span class="file-name-text">{{ row.file_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="file_type" label="文件类型" min-width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.file_type?.toUpperCase() || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文件大小" min-width="100" align="right">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="uploaded_at" label="上传时间" min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.uploaded_at) }}
          </template>
        </el-table-column>
        <el-table-column label="识别状态" min-width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.recognition_result" type="success" size="small">已识别</el-tag>
            <el-tag v-else type="info" size="small">未识别</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="320" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button type="primary" link size="small" @click="previewAttachment(row)">
                预览
              </el-button>
              <el-button type="primary" link size="small" @click="downloadAttachment(row)">
                下载
              </el-button>
              <!-- 未识别时显示AI识别按钮 -->
              <template v-if="!row.recognition_result">
                <el-button
                  type="success"
                  link
                  size="small"
                  @click="aiRecognize(row)"
                  :loading="row.recognizing"
                >
                  AI识别
                </el-button>
              </template>
              <!-- 已识别时显示识别结果和重新识别 -->
              <template v-else>
                <el-button type="primary" link size="small" @click="showRecognitionResult(row)">
                  识别结果
                </el-button>
                <el-button
                  type="warning"
                  link
                  size="small"
                  @click="aiRecognize(row)"
                  :loading="row.recognizing"
                >
                  重新识别
                </el-button>
              </template>
              <el-popconfirm title="确定删除此附件？" @confirm="deleteAttachment(row.id)">
                <template #reference>
                  <el-button type="danger" link size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="attachments.length === 0 && !attachmentsLoading" class="empty-state">
        <el-empty description="暂无附件，点击上方按钮上传" :image-size="80" />
      </div>
    </el-card>

    <!-- 识别结果弹窗 -->
    <el-dialog
      v-model="resultDialogVisible"
      title="AI识别结果"
      width="800px"
      destroy-on-close
    >
      <template #header>
        <div class="dialog-header-custom">
          <span class="dialog-title">AI识别结果</span>
          <span class="dialog-time">{{ formatRecognitionTime(currentResult?.recognized_at) }}</span>
        </div>
      </template>
      <div v-if="currentResult" class="recognition-result">
        <!-- 识别内容 - 使用描述列表样式 -->
        <div class="result-section">
          <div class="result-item">
            <span class="result-label">凭证编号</span>
            <span class="result-value">{{ currentResult.voucher_no || '-' }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">凭证日期</span>
            <span class="result-value">{{ currentResult.voucher_date || '-' }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">金额</span>
            <span class="result-value amount-value">{{ currentResult.amount || '-' }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">交易对手</span>
            <span class="result-value">{{ currentResult.counterparty || '-' }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">业务摘要</span>
            <span class="result-value">{{ currentResult.description || '-' }}</span>
          </div>
        </div>

        <!-- 关键信息 JSON格式 -->
        <div class="key-info-section" v-if="currentResult.key_info">
          <div class="section-title">关键信息</div>
          <div class="json-content">
            <pre>{{ formatKeyInfo(currentResult.key_info) }}</pre>
          </div>
        </div>

        <!-- 建议科目和置信度 - 分两行展示 -->
        <div class="extra-info">
          <div class="info-row-full">
            <span class="info-label">建议科目：</span>
            <span class="info-value">{{ currentResult.subject_suggestion || '-' }}</span>
          </div>
          <div class="info-row-full">
            <span class="info-label">置信度：</span>
            <span class="info-value confidence-value">{{ Math.round((currentResult.confidence || 0) * 100) }}%</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="resultDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 图片预览 -->
    <el-dialog v-model="imagePreviewVisible" title="图片预览" width="800px">
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
import { ref, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Edit, Plus, Picture, Reading, Document
} from '@element-plus/icons-vue'
import { voucherApi } from '@/api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const attachmentsLoading = ref(false)
const voucher = ref(null)
const attachments = ref([])
const resultDialogVisible = ref(false)
const currentResult = ref(null)
const imagePreviewVisible = ref(false)
const previewImageUrl = ref('')
const uploadRef = ref(null)
const pendingFiles = ref([])

// 编辑相关
const editDialogVisible = ref(false)
const editLoading = ref(false)
const editFormRef = ref(null)
const editForm = reactive({
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

// 从路由获取ID
const projectId = route.params.projectId
const voucherId = route.params.id

// 验证路由参数
if (!projectId || !voucherId) {
  ElMessage.error('页面参数错误，请从凭证列表进入')
  router.push('/vouchers')
}

// 格式化金额
const formatAmount = (amount) => {
  if (!amount) return '0.00'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

// 获取金额样式类
const getAmountClass = (amount) => {
  if (!amount) return ''
  if (amount >= 100000) return 'amount-large'
  if (amount >= 10000) return 'amount-medium'
  return ''
}

// 格式化文件大小
const formatFileSize = (size) => {
  if (!size) return '0 B'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / (1024 * 1024)).toFixed(1) + ' MB'
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

// 获取文件图标
const getFileIcon = (type) => {
  if (['.jpg', '.jpeg', '.png', '.bmp'].includes(type)) return Picture
  if (type === '.pdf') return Reading
  return Document
}

// 获取文件图标颜色
const getFileIconColor = (type) => {
  if (['.jpg', '.jpeg', '.png', '.bmp'].includes(type)) return '#67c23a'
  if (type === '.pdf') return '#f56c6c'
  return '#409eff'
}

// 格式化关键信息为JSON格式
const formatKeyInfo = (keyInfo) => {
  if (!keyInfo) return '-'
  // 如果是纯文本，直接返回
  if (typeof keyInfo !== 'object') {
    // 尝试按句子分割并格式化
    return String(keyInfo)
  }
  // 如果是对象，格式化为JSON
  try {
    return JSON.stringify(keyInfo, null, 2)
  } catch {
    return String(keyInfo)
  }
}

// 格式化识别时间
const formatRecognitionTime = (time) => {
  if (!time) {
    // 如果没有时间，使用当前时间
    const now = new Date()
    return `识别时间：${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  }
  const date = new Date(time)
  return `识别时间：${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

// 加载凭证信息
const loadVoucher = async () => {
  loading.value = true
  try {
    const res = await voucherApi.getDetail(projectId, voucherId)
    voucher.value = res
  } catch (error) {
    ElMessage.error('加载凭证信息失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 加载附件列表
const loadAttachments = async () => {
  attachmentsLoading.value = true
  try {
    const res = await voucherApi.getAttachments(projectId, voucherId)
    // 保留后端返回的识别结果，仅添加识别中状态
    attachments.value = (res || []).map(att => ({
      ...att,
      recognizing: false
    }))
  } catch (error) {
    console.error(error)
    attachments.value = []
  } finally {
    attachmentsLoading.value = false
  }
}

// 文件选择处理
const handleFileSelect = async (file) => {
  pendingFiles.value.push(file.raw)
  await submitAttachments()
}

// 提交附件上传
const submitAttachments = async () => {
  if (pendingFiles.value.length === 0) return

  try {
    await voucherApi.uploadAttachments(projectId, voucherId, pendingFiles.value)
    ElMessage.success(`成功上传 ${pendingFiles.value.length} 个附件`)
    pendingFiles.value = []
    await loadAttachments()
  } catch (error) {
    ElMessage.error('上传失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 预览附件
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

// 下载附件
const downloadAttachment = (att) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000'
  const url = `${baseUrl}/api/files/${att.file_path}`
  window.open(url, '_blank')
}

// 删除附件
const deleteAttachment = async (attachmentId) => {
  try {
    await voucherApi.deleteAttachment(projectId, voucherId, attachmentId)
    ElMessage.success('附件已删除')
    await loadAttachments()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// AI识别
const aiRecognize = async (attachment) => {
  attachment.recognizing = true

  try {
    const res = await voucherApi.recognizeAttachment(projectId, voucherId, attachment.id)

    // 更新识别结果
    attachment.recognition_result = res.result

    ElMessage.success('AI识别完成')
  } catch (error) {
    ElMessage.error('AI识别失败: ' + (error.detail || error.message))
  } finally {
    attachment.recognizing = false
  }
}

// 显示识别结果
const showRecognitionResult = (attachment) => {
  currentResult.value = attachment.recognition_result
  resultDialogVisible.value = true
}

// 编辑凭证
const editVoucher = () => {
  if (!voucher.value) return
  // 填充表单
  editForm.voucher_no = voucher.value.voucher_no
  editForm.voucher_date = voucher.value.voucher_date
  editForm.amount = voucher.value.amount
  editForm.subject_code = voucher.value.subject_code || ''
  editForm.subject_name = voucher.value.subject_name || ''
  editForm.description = voucher.value.description || ''
  editForm.counterparty = voucher.value.counterparty || ''
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

    await voucherApi.update(projectId, voucherId, updateData)
    ElMessage.success('凭证更新成功')
    editDialogVisible.value = false
    // 重新加载凭证信息
    await loadVoucher()
  } catch (error) {
    ElMessage.error('更新失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    editLoading.value = false
  }
}

onMounted(() => {
  loadVoucher()
  loadAttachments()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.info-card {
  margin-bottom: $spacing-lg;
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
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
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
    color: $danger-color;
    font-weight: 700;
  }

  &.amount-medium {
    color: $warning-color;
    font-weight: 600;
  }
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .file-name-text {
    white-space: nowrap;
  }
}

// 附件表格样式
.attachment-table {
  width: 100%;

  :deep(.el-table__header th) {
    background: #f8fafc;
    font-weight: 600;
    color: #1e293b;

    .cell {
      white-space: nowrap;
      overflow: visible;
    }
  }

  :deep(.el-table__body td) {
    .cell {
      white-space: nowrap;
    }
  }
}

.action-buttons {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px;
}

.empty-state {
  padding: $spacing-xxl;
}

// 弹框自定义标题
.dialog-header-custom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;

  .dialog-title {
    font-size: 18px;
    font-weight: 600;
    color: #1e293b;
  }

  .dialog-time {
    font-size: 13px;
    color: #94a3b8;
    font-weight: 400;
  }
}

.recognition-result {
  // 识别内容区域
  .result-section {
    background: #f8fafc;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 20px;

    .result-item {
      display: flex;
      align-items: flex-start;
      padding: 12px 0;
      border-bottom: 1px solid #eef2f7;

      &:last-child {
        border-bottom: none;
      }

      .result-label {
        flex-shrink: 0;
        width: 100px;
        font-size: 14px;
        font-weight: 600;
        color: #1e293b;
      }

      .result-value {
        flex: 1;
        font-size: 14px;
        color: #475569;
        word-break: break-word;
      }
    }
  }

  .amount-value {
    font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
    font-weight: 600;
    color: #3b82f6;
  }

  .key-info-section {
    margin-bottom: 20px;
    padding: 16px;
    background: #f8fafc;
    border-radius: 8px;
    border: 1px solid #e2e8f0;

    .section-title {
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #e2e8f0;
    }

    .json-content {
      pre {
        margin: 0;
        padding: 12px;
        background: white;
        border-radius: 6px;
        font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        font-size: 13px;
        line-height: 1.7;
        color: #334155;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 250px;
        overflow-y: auto;
        border: 1px solid #e2e8f0;
      }
    }
  }

  .extra-info {
    background: #f8fafc;
    border-radius: 8px;
    padding: 16px;
    border: 1px solid #e2e8f0;

    .info-row-full {
      display: flex;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid #e2e8f0;

      &:last-child {
        border-bottom: none;
        padding-bottom: 0;
      }

      &:first-child {
        padding-top: 0;
      }

      .info-label {
        font-size: 14px;
        font-weight: 600;
        color: #1e293b;
      }

      .info-value {
        font-size: 14px;
        color: #475569;

        &.confidence-value {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-weight: 600;
          color: #3b82f6;
        }
      }
    }
  }
}

// 编辑对话框样式
.edit-dialog {
  .edit-form {
    padding: 10px 20px 0;
  }
}
</style>