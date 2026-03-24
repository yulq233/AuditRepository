<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">合规检查</h2>
      <p class="page-subtitle">凭证合规性自动检查与预警</p>
    </div>

    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">检查规则</span>
          <el-button type="primary" @click="runCheck" :loading="loading">
            <el-icon><Warning /></el-icon>
            执行检查
          </el-button>
        </div>
      </template>

      <el-checkbox-group v-model="selectedRules">
        <el-row :gutter="20">
          <el-col :span="6" v-for="rule in rules" :key="rule.key">
            <el-checkbox :label="rule.key">{{ rule.name }}</el-checkbox>
          </el-col>
        </el-row>
      </el-checkbox-group>
    </el-card>

    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">预警列表</span>
          <el-tag type="danger">{{ alerts.length }} 条预警</el-tag>
        </div>
      </template>

      <el-table :data="alerts" style="width: 100%">
        <el-table-column prop="voucher_no" label="凭证号" width="150" />
        <el-table-column prop="rule_name" label="规则" width="150" />
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.severity === 'critical' ? 'blocked' : row.severity]">
              {{ getSeverityLabel(row.severity) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="alert_message" label="预警信息" min-width="250" />
        <el-table-column prop="is_resolved" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_resolved ? 'success' : 'warning'">
              {{ row.is_resolved ? '已处理' : '待处理' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const loading = ref(false)
const selectedRules = ref(['budget_exceed', 'approval_missing', 'cash_exceed'])
const alerts = ref([])

const rules = [
  { key: 'budget_exceed', name: '预算超标' },
  { key: 'approval_missing', name: '审批流程不全' },
  { key: 'sequential_invoices', name: '连号发票' },
  { key: 'weekend_transactions', name: '周末大额交易' },
  { key: 'cash_exceed', name: '现金超限' }
]

const getSeverityLabel = (severity) => {
  const map = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低'
  }
  return map[severity] || severity
}

const runCheck = async () => {
  loading.value = true
  // TODO: 调用API执行检查
  setTimeout(() => {
    loading.value = false
  }, 1000)
}

onMounted(() => {
  // TODO: 加载预警数据
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
</style>