<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">抽样结果</h2>
      <div>
        <el-button @click="exportResults">
          <el-icon><Download /></el-icon>
          导出结果
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">样本总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.highRisk }}</div>
          <div class="stat-label">高风险</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.mediumRisk }}</div>
          <div class="stat-label">中风险</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.lowRisk }}</div>
          <div class="stat-label">低风险</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 结果列表 -->
    <el-card class="card-container" style="margin-top: 20px">
      <el-table :data="samples" style="width: 100%" v-loading="loading">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="voucher_no" label="凭证号" width="120" fixed="left" />
        <el-table-column prop="subject_name" label="科目" width="150" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">
            <span :class="{ 'amount-large': row.amount > 100000 }">
              {{ formatAmount(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="摘要" min-width="200" show-overflow-tooltip />
        <el-table-column prop="risk_score" label="风险分数" width="100">
          <template #default="{ row }">
            <el-progress
              v-if="row.risk_score"
              :percentage="row.risk_score"
              :color="getRiskColor(row.risk_score)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="抽取原因" width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewVoucher(row)">查看凭证</el-button>
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
          @size-change="loadResults"
          @current-change="loadResults"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { samplingApi } from '@/api'

const loading = ref(false)

const projectId = ref(localStorage.getItem('currentProjectId') || '')

const pagination = reactive({
  page: 1,
  pageSize: 50,
  total: 0
})

const samples = ref([])

const stats = reactive({
  total: 0,
  highRisk: 0,
  mediumRisk: 0,
  lowRisk: 0
})

const formatAmount = (amount) => {
  if (!amount) return '0.00'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

const getRiskColor = (score) => {
  if (score >= 70) return '#f56c6c'
  if (score >= 50) return '#e6a23c'
  return '#67c23a'
}

const loadResults = async () => {
  if (!projectId.value) return

  loading.value = true
  try {
    const res = await samplingApi.getResults(projectId.value, {
      page: pagination.page,
      page_size: pagination.pageSize
    })
    samples.value = res.items || []
    pagination.total = res.total || 0
    stats.total = res.total || 0
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const viewVoucher = (sample) => {
  // TODO: 跳转到凭证详情
  ElMessage.info('凭证详情功能开发中')
}

const exportResults = async () => {
  try {
    const blob = await samplingApi.export(projectId.value, { format: 'excel' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `抽样结果_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  loadResults()
})
</script>

<style lang="scss" scoped>
.stat-card {
  text-align: center;
  padding: 15px;

  .stat-value {
    font-size: 28px;
    font-weight: bold;
    color: #303133;
  }

  .stat-label {
    font-size: 14px;
    color: #909399;
    margin-top: 5px;
  }
}

.amount-large {
  color: #f56c6c;
  font-weight: bold;
}
</style>