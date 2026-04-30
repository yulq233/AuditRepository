<template>
  <div class="logs-panel">
    <!-- 筛选条件 -->
    <el-form inline class="filter-form">
      <el-form-item label="时间">
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" style="width: 240px" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filterStatus" clearable placeholder="全部" style="width: 100px">
          <el-option label="全部" value="" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="error" />
        </el-select>
      </el-form-item>
      <el-form-item label="用途">
        <el-select v-model="filterPurpose" clearable placeholder="全部" style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="通用服务" value="general" />
          <el-option label="图片识别" value="recognition" />
          <el-option label="风险分析" value="risk_analysis" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchLogs">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 日志列表 -->
    <el-table :data="logsData.logs" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="created_at" label="时间" min-width="170">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="provider" label="供应商" min-width="90">
        <template #default="{ row }">
          <el-tag effect="plain" size="small">{{ row.provider }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="model" label="模型" min-width="180">
        <template #default="{ row }">
          <span class="model-name">{{ row.model }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="purpose" label="用途" min-width="100">
        <template #default="{ row }">
          <el-tag :type="getPurposeType(row.purpose)" size="small">
            {{ getPurposeName(row.purpose) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Token用量" min-width="120">
        <template #default="{ row }">
          <span class="token-info">入{{ row.input_tokens }} / 出{{ row.output_tokens }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="latency_ms" label="耗时" min-width="100">
        <template #default="{ row }">
          <span :class="{'slow': row.latency_ms > 5000}">{{ row.latency_ms }}ms</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" min-width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
            {{ row.status === 'success' ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="80" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="logsData.total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      @current-change="fetchLogs"
      @size-change="fetchLogs"
      class="pagination"
    />

    <!-- 详情弹窗 -->
    <el-dialog v-model="showDetailDialog" title="调用详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="调用ID">{{ currentLog.id }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatTime(currentLog.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="供应商">{{ currentLog.provider }}</el-descriptions-item>
        <el-descriptions-item label="模型">{{ currentLog.model }}</el-descriptions-item>
        <el-descriptions-item label="用途">{{ getPurposeName(currentLog.purpose) }}</el-descriptions-item>
        <el-descriptions-item label="操作">{{ currentLog.operation }}</el-descriptions-item>
        <el-descriptions-item label="输入Token">{{ currentLog.input_tokens }}</el-descriptions-item>
        <el-descriptions-item label="输出Token">{{ currentLog.output_tokens }}</el-descriptions-item>
        <el-descriptions-item label="总Token">{{ currentLog.total_tokens }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ currentLog.latency_ms }}ms</el-descriptions-item>
        <el-descriptions-item label="状态" :span="2">
          <el-tag :type="currentLog.status === 'success' ? 'success' : 'danger'">
            {{ currentLog.status }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <el-divider>请求内容</el-divider>
      <el-input type="textarea" :rows="3" :model-value="currentLog.request_content" readonly />

      <el-divider>响应内容</el-divider>
      <el-input type="textarea" :rows="3" :model-value="currentLog.response_content" readonly />

      <el-divider v-if="currentLog.error_message">错误信息</el-divider>
      <el-alert v-if="currentLog.error_message" type="error" :title="currentLog.error_message" :closable="false" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const loading = ref(false)
const dateRange = ref([])
const filterStatus = ref('')
const filterPurpose = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const showDetailDialog = ref(false)
const currentLog = ref({})

const logsData = reactive({
  total: 0,
  page: 1,
  page_size: 20,
  logs: []
})

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterPurpose.value) params.purpose = filterPurpose.value

    const res = await request.get('/ai/logs', { params })
    Object.assign(logsData, res.data || res)
  } catch (error) {
    console.error('获取调用日志失败:', error)
    ElMessage.error('获取调用日志失败')
  } finally {
    loading.value = false
  }
}

const showDetail = async (row) => {
  try {
    const res = await request.get(`/ai/logs/${row.id}`)
    currentLog.value = res.data || res
    showDetailDialog.value = true
  } catch (error) {
    console.error('获取日志详情失败:', error)
    ElMessage.error('获取日志详情失败')
  }
}

const formatTime = (time) => {
  if (!time) return ''
  const d = new Date(time)
  return d.toLocaleString('zh-CN', { hour12: false })
}

const getPurposeType = (purpose) => {
  const types = { general: '', recognition: 'success', risk_analysis: 'warning' }
  return types[purpose] || ''
}

const getPurposeName = (purpose) => {
  const names = { general: '通用服务', recognition: '图片识别', risk_analysis: '风险分析' }
  return names[purpose] || purpose
}

onMounted(() => {
  fetchLogs()
})
</script>

<style lang="scss" scoped>
.logs-panel {
  .filter-form {
    margin-bottom: 16px;
  }

  :deep(.el-table) {
    width: 100%;
    table-layout: auto;

    .cell {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  .model-name {
    font-size: 13px;
    color: #606266;
  }

  .token-info {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
  }

  .slow {
    color: #e6a23c;
  }

  .pagination {
    margin-top: 16px;
    justify-content: flex-end;
  }
}
</style>