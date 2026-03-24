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
              <el-input-number v-model="form.amountTolerance" :min="0" :max="1000" :step="10" />
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
          <el-tag>{{ results.length }} 条记录</el-tag>
        </div>
      </template>

      <el-table :data="results" style="width: 100%" v-loading="loading">
        <el-table-column prop="invoice_no" label="发票号" width="150" />
        <el-table-column prop="order_no" label="订单号" width="150" />
        <el-table-column prop="receipt_no" label="入库单号" width="150" />
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
        <el-table-column prop="differences" label="差异说明" min-width="200">
          <template #default="{ row }">
            {{ row.differences || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { formatAmount } from '@/utils/formatters'

const loading = ref(false)
const projects = ref([])
const results = ref([])

const form = reactive({
  projectId: '',
  amountTolerance: 100,
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

const executeMatching = async () => {
  loading.value = true
  // TODO: 调用API执行匹配
  setTimeout(() => {
    loading.value = false
  }, 1000)
}

onMounted(() => {
  // TODO: 加载项目列表
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';
</style>