<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">凭证管理</h2>
      <el-button type="primary" @click="showImportDialog">
        <el-icon><Upload /></el-icon>
        导入凭证
      </el-button>
    </div>

    <!-- 筛选 -->
    <el-card class="card-container filter-container">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="科目">
          <el-input v-model="filterForm.subject_code" placeholder="科目代码" clearable />
        </el-form-item>
        <el-form-item label="金额范围">
          <el-input-number v-model="filterForm.min_amount" placeholder="最小" :controls="false" style="width: 100px" />
          <span style="margin: 0 5px">-</span>
          <el-input-number v-model="filterForm.max_amount" placeholder="最大" :controls="false" style="width: 100px" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filterForm.keyword" placeholder="凭证号/摘要" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadVouchers">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 凭证列表 -->
    <el-card class="card-container">
      <el-table :data="vouchers" style="width: 100%" v-loading="loading">
        <el-table-column prop="voucher_no" label="凭证号" width="120" fixed="left" />
        <el-table-column prop="voucher_date" label="日期" width="120" />
        <el-table-column prop="subject_code" label="科目代码" width="100" />
        <el-table-column prop="subject_name" label="科目名称" width="150" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">
            <span :class="{ 'amount-large': row.amount > 100000 }">
              {{ formatAmount(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="摘要" min-width="200" show-overflow-tooltip />
        <el-table-column prop="counterparty" label="交易对手" width="150" />
        <el-table-column label="附件" width="80">
          <template #default="{ row }">
            <el-icon v-if="row.attachment_path" color="#67c23a"><Document /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewDetail(row)">查看</el-button>
            <el-button type="primary" link @click="uploadAttachment(row)">上传</el-button>
            <el-button type="primary" link @click="runOcr(row)">OCR</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[50, 100, 200]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadVouchers"
          @current-change="loadVouchers"
        />
      </div>
    </el-card>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入凭证" width="500px">
      <el-upload
        drag
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls,.csv"
        :on-change="handleFileChange"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 Excel 和 CSV 格式</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="importVouchers">导入</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="凭证详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="凭证号">{{ currentVoucher?.voucher_no }}</el-descriptions-item>
        <el-descriptions-item label="日期">{{ currentVoucher?.voucher_date }}</el-descriptions-item>
        <el-descriptions-item label="科目代码">{{ currentVoucher?.subject_code }}</el-descriptions-item>
        <el-descriptions-item label="科目名称">{{ currentVoucher?.subject_name }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ formatAmount(currentVoucher?.amount) }}</el-descriptions-item>
        <el-descriptions-item label="交易对手">{{ currentVoucher?.counterparty }}</el-descriptions-item>
        <el-descriptions-item label="摘要" :span="2">{{ currentVoucher?.description }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { voucherApi } from '@/api'

const loading = ref(false)
const importing = ref(false)
const importDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const uploadFile = ref(null)
const currentVoucher = ref(null)

const filterForm = reactive({
  subject_code: '',
  min_amount: null,
  max_amount: null,
  keyword: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 50,
  total: 0
})

const vouchers = ref([])

// 当前项目ID（从localStorage或路由获取）
const projectId = ref(localStorage.getItem('currentProjectId') || '')

const formatAmount = (amount) => {
  if (!amount) return '0.00'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

const loadVouchers = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
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

const showImportDialog = () => {
  uploadFile.value = null
  importDialogVisible.value = true
}

const handleFileChange = (file) => {
  uploadFile.value = file.raw
}

const importVouchers = async () => {
  if (!uploadFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  importing.value = true
  try {
    const res = await voucherApi.import(projectId.value, uploadFile.value)
    ElMessage.success(`导入成功 ${res.success} 条，失败 ${res.failed} 条`)
    importDialogVisible.value = false
    loadVouchers()
  } catch (error) {
    console.error(error)
  } finally {
    importing.value = false
  }
}

const viewDetail = (voucher) => {
  currentVoucher.value = voucher
  detailDialogVisible.value = true
}

const uploadAttachment = (voucher) => {
  // TODO: 实现附件上传
  ElMessage.info('附件上传功能开发中')
}

const runOcr = async (voucher) => {
  try {
    ElMessage.info('正在进行OCR识别...')
    const res = await voucherApi.ocr(projectId.value, voucher.id)
    ElMessage.success(`OCR识别完成，置信度: ${(res.confidence * 100).toFixed(1)}%`)
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  loadVouchers()
})
</script>

<style lang="scss" scoped>
.amount-large {
  color: #f56c6c;
  font-weight: bold;
}
</style>