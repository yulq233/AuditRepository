<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">{{ project?.name || '项目详情' }}</h2>
      <div>
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" @click="showImportDialog">
          <el-icon><Upload /></el-icon>
          导入凭证
        </el-button>
      </div>
    </div>

    <!-- 项目概览 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.voucherCount }}</div>
          <div class="stat-label">凭证数量</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ formatAmount(stats.totalAmount) }}</div>
          <div class="stat-label">凭证总金额</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.sampleCount }}</div>
          <div class="stat-label">抽样数量</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.completionRate }}%</div>
          <div class="stat-label">完成进度</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作 -->
    <el-card class="card-container" style="margin-top: 20px">
      <template #header>快捷操作</template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="quick-action" @click="$router.push('/sampling/risk-profile')">
            <el-icon :size="40" color="#409eff"><DataAnalysis /></el-icon>
            <div>风险画像</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="quick-action" @click="$router.push('/sampling/execute')">
            <el-icon :size="40" color="#67c23a"><Aim /></el-icon>
            <div>执行抽样</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="quick-action" @click="$router.push('/matching')">
            <el-icon :size="40" color="#e6a23c"><Connection /></el-icon>
            <div>三单匹配</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="quick-action" @click="$router.push('/papers')">
            <el-icon :size="40" color="#f56c6c"><Notebook /></el-icon>
            <div>生成底稿</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 最近凭证 -->
    <el-card class="card-container" style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>最近凭证</span>
          <el-button type="primary" link @click="$router.push('/vouchers')">
            查看全部
          </el-button>
        </div>
      </template>

      <el-table :data="recentVouchers" style="width: 100%">
        <el-table-column prop="voucher_no" label="凭证号" width="120" />
        <el-table-column prop="voucher_date" label="日期" width="120" />
        <el-table-column prop="subject_name" label="科目" min-width="150" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">
            {{ formatAmount(row.amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="摘要" min-width="200" show-overflow-tooltip />
      </el-table>
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
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 Excel (.xlsx, .xls) 和 CSV 格式，需包含凭证编号列
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="importVouchers">
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi, voucherApi } from '@/api'

const route = useRoute()
const projectId = route.params.id

const project = ref(null)
const stats = reactive({
  voucherCount: 0,
  totalAmount: 0,
  sampleCount: 0,
  completionRate: 0
})

const recentVouchers = ref([])
const importDialogVisible = ref(false)
const importing = ref(false)
const uploadFile = ref(null)

const formatAmount = (amount) => {
  if (!amount) return '0.00'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const loadProject = async () => {
  try {
    project.value = await projectApi.getDetail(projectId)
  } catch (error) {
    console.error(error)
  }
}

const loadVouchers = async () => {
  try {
    const res = await voucherApi.getList(projectId, { page: 1, page_size: 10 })
    recentVouchers.value = res.items || []
    stats.voucherCount = res.total || 0

    // 计算总金额
    stats.totalAmount = recentVouchers.value.reduce((sum, v) => sum + (v.amount || 0), 0)
  } catch (error) {
    console.error(error)
  }
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
    const res = await voucherApi.import(projectId, uploadFile.value)
    ElMessage.success(`导入成功 ${res.success} 条，失败 ${res.failed} 条`)
    importDialogVisible.value = false
    loadVouchers()
  } catch (error) {
    console.error(error)
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  loadProject()
  loadVouchers()
})
</script>

<style lang="scss" scoped>
.stat-card {
  text-align: center;
  padding: 20px;

  .stat-value {
    font-size: 32px;
    font-weight: bold;
    color: #303133;
  }

  .stat-label {
    font-size: 14px;
    color: #909399;
    margin-top: 8px;
  }
}

.quick-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.3s;

  &:hover {
    background: #f5f7fa;
  }

  div {
    margin-top: 10px;
    font-size: 14px;
    color: #606266;
  }
}
</style>