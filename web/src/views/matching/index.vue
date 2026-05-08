<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">三单匹配</h2>
      <p class="page-subtitle">发票、订单、入库单自动匹配核对</p>
    </div>

    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">匹配设置</span>
          <el-button type="primary" @click="executeMatching" :loading="loading">
            <el-icon><Connection /></el-icon>
            执行匹配
          </el-button>
        </div>
      </template>

      <el-form :model="form" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="项目">
              <el-select v-model="form.projectId" placeholder="选择项目" style="width: 100%">
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="金额容差">
              <el-input-number v-model="form.amountTolerance" :min="0" :max="1" :step="0.01" :precision="2" />
              <span style="margin-left: 8px; color: #909399;">%</span>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="日期容差(天)">
              <el-input-number v-model="form.dateTolerance" :min="1" :max="90" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">匹配结果</span>
          <div>
            <el-tag>{{ results.length }} 条记录</el-tag>
            <el-button type="danger" link @click="clearResults" v-if="results.length > 0" style="margin-left: 12px;">
              清空结果
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="results" style="width: 100%" v-loading="loading">
        <el-table-column prop="invoice_no" label="发票号" width="150" />
        <el-table-column prop="order_no" label="订单号" width="150">
          <template #default="{ row }">
            {{ row.order_no || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="receipt_no" label="入库单号" width="150">
          <template #default="{ row }">
            {{ row.receipt_no || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">
            {{ formatAmount(row.amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="match_status" label="匹配状态" width="120">
          <template #default="{ row }">
            <span :class="['status-tag', row.match_status]">
              {{ getMatchStatusLabel(row.match_status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="amount_difference" label="金额差异" width="120">
          <template #default="{ row }">
            <span v-if="row.amount_difference" :class="row.amount_difference > 0 ? 'text-danger' : 'text-success'">
              {{ row.amount_difference > 0 ? '+' : '' }}{{ formatAmount(row.amount_difference) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="date_difference" label="日期差异" width="100">
          <template #default="{ row }">
            <span v-if="row.date_difference">{{ row.date_difference }}天</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="处理建议" min-width="200">
          <template #default="{ row }">
            <div v-if="row.suggestions && row.suggestions.length > 0">
              <div v-for="(s, i) in row.suggestions" :key="i" style="font-size: 12px; color: #606266;">
                • {{ s }}
              </div>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatAmount } from '@/utils/formatters'
import { projectApi, matchingApi } from '@/api'

const loading = ref(false)
const projects = ref([])
const results = ref([])

const form = reactive({
  projectId: '',
  amountTolerance: 0.01,
  dateTolerance: 30
})

const getMatchStatusLabel = (status) => {
  const map = {
    fully_matched: '完全匹配',
    partially_matched: '部分匹配',
    not_matched: '未匹配',
    exception: '异常'
  }
  return map[status] || status
}

const loadProjects = async () => {
  try {
    const res = await projectApi.getList({ page: 1, page_size: 100 })
    projects.value = res.items || []
    if (projects.value.length > 0 && !form.projectId) {
      form.projectId = projects.value[0].id
    }
  } catch (e) {
    console.error('加载项目列表失败:', e)
  }
}

const executeMatching = async () => {
  if (!form.projectId) {
    ElMessage.warning('请选择项目')
    return
  }

  loading.value = true
  try {
    const res = await matchingApi.execute(form.projectId, {
      amount_tolerance: form.amountTolerance,
      date_tolerance: form.dateTolerance
    })
    results.value = res.results || []
    ElMessage.success(`匹配完成，共 ${res.total} 条结果`)
  } catch (e) {
    ElMessage.error('执行匹配失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const clearResults = async () => {
  try {
    await ElMessageBox.confirm('确定要清空匹配结果吗？', '提示', {
      type: 'warning'
    })
    await matchingApi.clearResults(form.projectId)
    results.value = []
    ElMessage.success('已清空')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('清空失败')
    }
  }
}

onMounted(() => {
  loadProjects()
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

.text-danger {
  color: #f56c6c;
}

.text-success {
  color: #67c23a;
}

.status-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;

  &.fully_matched {
    background: #f0f9eb;
    color: #67c23a;
  }

  &.partially_matched {
    background: #fdf6ec;
    color: #e6a23c;
  }

  &.not_matched {
    background: #fef0f0;
    color: #f56c6c;
  }
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