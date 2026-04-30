<template>
  <div class="usage-panel">
    <!-- 筛选条件 -->
    <el-form inline class="filter-form">
      <el-form-item label="时间范围">
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="供应商">
        <el-select v-model="filterProvider" clearable placeholder="全部" style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="通义千问" value="qwen" />
          <el-option label="智谱GLM" value="zhipu" />
          <el-option label="百度文心" value="ernie" />
          <el-option label="本地模型" value="ollama" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchUsage">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6" :md="4">
        <el-card shadow="never" class="stat-card">
          <el-statistic title="总调用次数" :value="summary.total_calls" />
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <el-card shadow="never" class="stat-card">
          <el-statistic title="总Token数" :value="summary.total_tokens" />
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <el-card shadow="never" class="stat-card">
          <el-statistic title="成功次数" :value="summary.success_count" />
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <el-card shadow="never" class="stat-card">
          <el-statistic title="失败次数" :value="summary.error_count" />
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <el-card shadow="never" class="stat-card">
          <el-statistic title="平均耗时" :value="summary.avg_latency_ms" suffix="ms" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span>每日调用量趋势</span>
          </template>
          <div ref="dailyChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span>供应商分布</span>
          </template>
          <div ref="providerChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 模型用量排名 -->
    <el-card shadow="never" class="model-ranking-card">
      <template #header>
        <span>模型用量排名（Top 10）</span>
      </template>
      <el-table :data="summary.by_model" stripe v-loading="loading">
        <el-table-column prop="model" label="模型名称" />
        <el-table-column prop="calls" label="调用次数" width="120" />
        <el-table-column prop="tokens" label="Token数" width="120" />
        <el-table-column label="占比" width="100">
          <template #default="{ row }">
            {{ summary.total_calls > 0 ? (row.calls / summary.total_calls * 100).toFixed(1) + '%' : '0%' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const loading = ref(false)
const dateRange = ref([])
const filterProvider = ref('')
const dailyChartRef = ref(null)
const providerChartRef = ref(null)

const summary = reactive({
  total_calls: 0,
  total_tokens: 0,
  success_count: 0,
  error_count: 0,
  avg_latency_ms: 0,
  by_provider: {},
  by_purpose: {},
  by_model: []
})

const dailyData = ref([])

const fetchUsage = async () => {
  loading.value = true
  try {
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    if (filterProvider.value) {
      params.provider = filterProvider.value
    }

    // 获取汇总
    const summaryRes = await request.get('/ai/usage/summary', { params })
    Object.assign(summary, summaryRes.data || summaryRes)

    // 获取每日数据
    const dailyRes = await request.get('/ai/usage/daily', { params })
    dailyData.value = dailyRes.data || dailyRes

    // 渲染图表
    nextTick(() => {
      renderCharts()
    })
  } catch (error) {
    console.error('获取用量统计失败:', error)
    ElMessage.error('获取用量统计失败')
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  // 简化版图表（不依赖echarts）
  renderDailyChart()
  renderProviderChart()
}

const renderDailyChart = () => {
  const container = dailyChartRef.value
  if (!container) return

  if (dailyData.value.length === 0) {
    container.innerHTML = '<div class="no-data">暂无数据</div>'
    return
  }

  const maxCalls = Math.max(...dailyData.value.map(d => d.calls)) || 100
  let html = '<div class="simple-chart">'
  dailyData.value.slice(-14).forEach(day => {
    const height = (day.calls / maxCalls * 100) || 5
    html += `
      <div class="bar-item">
        <div class="bar" style="height: ${height}%"></div>
        <div class="label">${day.date.slice(5)}</div>
      </div>
    `
  })
  html += '</div>'
  container.innerHTML = html
}

const renderProviderChart = () => {
  const container = providerChartRef.value
  if (!container) return

  const providers = Object.entries(summary.by_provider)
  if (providers.length === 0) {
    container.innerHTML = '<div class="no-data">暂无数据</div>'
    return
  }

  let html = '<div class="pie-list">'
  providers.forEach(([name, data]) => {
    const calls = data.calls || data || 0
    const percent = summary.total_calls > 0 ? (calls / summary.total_calls * 100).toFixed(1) : 0
    const colors = { qwen: '#409eff', zhipu: '#67c23a', ernie: '#e6a23c', ollama: '#909399' }
    html += `
      <div class="pie-item">
        <div class="pie-dot" style="background: ${colors[name] || '#909399'}"></div>
        <div class="pie-label">${name}</div>
        <div class="pie-value">${calls} (${percent}%)</div>
      </div>
    `
  })
  html += '</div>'
  container.innerHTML = html
}

onMounted(() => {
  fetchUsage()
})
</script>

<style lang="scss" scoped>
.usage-panel {
  .filter-form {
    margin-bottom: 16px;
  }

  .stats-row {
    margin-bottom: 16px;

    .stat-card {
      text-align: center;
    }
  }

  .chart-card {
    margin-bottom: 16px;

    .chart-container {
      height: 200px;

      .no-data {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: #909399;
      }

      .simple-chart {
        display: flex;
        align-items: flex-end;
        height: 160px;
        padding: 10px;
        gap: 4px;

        .bar-item {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          height: 100%;

          .bar {
            width: 100%;
            background: linear-gradient(to top, #409eff, #79bbff);
            border-radius: 2px 2px 0 0;
            min-height: 4px;
          }

          .label {
            font-size: 10px;
            color: #909399;
            margin-top: 4px;
          }
        }
      }

      .pie-list {
        padding: 10px;

        .pie-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 0;

          .pie-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
          }

          .pie-label {
            flex: 1;
            font-size: 14px;
          }

          .pie-value {
            font-size: 14px;
            color: #606266;
          }
        }
      }
    }
  }
}
</style>