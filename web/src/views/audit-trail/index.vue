<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">审计轨迹</h2>
      <p class="page-subtitle">完整记录所有操作历史</p>
    </div>

    <el-card class="card-container">
      <template #header>
        <div class="card-header">
          <span class="card-title">操作日志</span>
        </div>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="操作类型">
          <el-select v-model="filters.action" placeholder="全部" clearable style="width: 150px">
            <el-option label="创建抽样" value="sample.created" />
            <el-option label="复核样本" value="sample.reviewed" />
            <el-option label="凭证上传" value="voucher.uploaded" />
            <el-option label="规则执行" value="rule.executed" />
            <el-option label="结果导出" value="result.exported" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTrail">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="trails" style="width: 100%" v-loading="loading">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at, 'YYYY-MM-DD HH:mm:ss') }}
          </template>
        </el-table-column>
        <el-table-column prop="user_id" label="操作人" width="120" />
        <el-table-column prop="action" label="操作类型" width="150">
          <template #default="{ row }">
            {{ getActionLabel(row.action) }}
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="对象类型" width="120" />
        <el-table-column prop="details" label="操作详情" min-width="200">
          <template #default="{ row }">
            <el-text truncated>{{ JSON.stringify(row.details) }}</el-text>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" width="150">
          <template #default="{ row }">
            {{ row.reason || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { formatDate } from '@/utils/formatters'

const loading = ref(false)
const trails = ref([])

const filters = reactive({
  action: '',
  dateRange: null
})

const getActionLabel = (action) => {
  const map = {
    'sample.created': '创建抽样',
    'sample.reviewed': '复核样本',
    'voucher.uploaded': '凭证上传',
    'rule.executed': '规则执行',
    'result.exported': '结果导出',
    'ai.analyzed': 'AI分析'
  }
  return map[action] || action
}

const loadTrail = async () => {
  loading.value = true
  // TODO: 调用API加载审计轨迹
  setTimeout(() => {
    loading.value = false
  }, 500)
}

onMounted(() => {
  loadTrail()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.filter-form {
  margin-bottom: $spacing-md;
}
</style>