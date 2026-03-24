<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">风险画像</h2>
      <el-button type="primary" @click="generateProfiles">
        <el-icon><Refresh /></el-icon>
        生成风险画像
      </el-button>
    </div>

    <!-- 风险分布概览 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="card-container">
          <template #header>风险等级分布</template>
          <div ref="riskChartRef" style="height: 250px"></div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card class="card-container">
          <template #header>各科目风险分布</template>
          <div ref="subjectChartRef" style="height: 250px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 科目风险列表 -->
    <el-card class="card-container" style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>科目风险画像</span>
          <el-input v-model="searchKeyword" placeholder="搜索科目" style="width: 200px" clearable />
        </div>
      </template>

      <el-table :data="filteredProfiles" style="width: 100%" v-loading="loading">
        <el-table-column prop="subject_code" label="科目代码" width="120" />
        <el-table-column prop="subject_name" label="科目名称" min-width="150" />
        <el-table-column prop="risk_level" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getRiskType(row.risk_level)">
              {{ getRiskLabel(row.risk_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="risk_score" label="风险分数" width="120">
          <template #default="{ row }">
            <el-progress
              :percentage="row.risk_score"
              :color="getRiskColor(row.risk_level)"
              :stroke-width="10"
            />
          </template>
        </el-table-column>
        <el-table-column prop="material_amount" label="重要性水平" width="120">
          <template #default="{ row }">
            {{ formatAmount(row.material_amount) }}
          </template>
        </el-table-column>
        <el-table-column label="风险因素" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="(factor, index) in (row.risk_factors || []).slice(0, 3)"
              :key="index"
              size="small"
              style="margin-right: 5px"
            >
              {{ factor.name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewDetail(row)">详情</el-button>
            <el-button type="primary" link @click="goToSampling(row)">抽样</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="风险画像详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="科目代码">{{ currentProfile?.subject_code }}</el-descriptions-item>
        <el-descriptions-item label="科目名称">{{ currentProfile?.subject_name }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <el-tag :type="getRiskType(currentProfile?.risk_level)">
            {{ getRiskLabel(currentProfile?.risk_level) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="风险分数">{{ currentProfile?.risk_score?.toFixed(1) }}</el-descriptions-item>
        <el-descriptions-item label="重要性水平">{{ formatAmount(currentProfile?.material_amount) }}</el-descriptions-item>
        <el-descriptions-item label="异常分数">{{ currentProfile?.anomaly_score?.toFixed(1) }}</el-descriptions-item>
      </el-descriptions>

      <h4 style="margin-top: 20px">风险因素分析</h4>
      <el-table :data="currentProfile?.risk_factors || []" style="width: 100%">
        <el-table-column prop="name" label="因素" width="120" />
        <el-table-column prop="score" label="分数" width="80">
          <template #default="{ row }">
            {{ row.score?.toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column prop="weight" label="权重" width="80">
          <template #default="{ row }">
            {{ (row.weight * 100).toFixed(0) }}%
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" />
      </el-table>

      <h4 style="margin-top: 20px">抽样建议</h4>
      <p>{{ currentProfile?.recommendation }}</p>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { riskApi } from '@/api'
import * as echarts from 'echarts'

const router = useRouter()
const loading = ref(false)
const detailDialogVisible = ref(false)
const currentProfile = ref(null)
const searchKeyword = ref('')
const riskChartRef = ref()
const subjectChartRef = ref()

const profiles = ref([])

const projectId = ref(localStorage.getItem('currentProjectId') || '')

const filteredProfiles = computed(() => {
  if (!searchKeyword.value) return profiles.value
  const keyword = searchKeyword.value.toLowerCase()
  return profiles.value.filter(p =>
    p.subject_code?.toLowerCase().includes(keyword) ||
    p.subject_name?.toLowerCase().includes(keyword)
  )
})

const formatAmount = (amount) => {
  if (!amount) return '0.00'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

const getRiskType = (level) => {
  const types = { high: 'danger', medium: 'warning', low: 'success' }
  return types[level] || 'info'
}

const getRiskLabel = (level) => {
  const labels = { high: '高风险', medium: '中风险', low: '低风险' }
  return labels[level] || level
}

const getRiskColor = (level) => {
  const colors = { high: '#f56c6c', medium: '#e6a23c', low: '#67c23a' }
  return colors[level] || '#909399'
}

const loadProfiles = async () => {
  if (!projectId.value) return

  loading.value = true
  try {
    const res = await riskApi.get(projectId.value)
    profiles.value = res || []

    nextTick(() => {
      renderCharts()
    })
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const generateProfiles = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  loading.value = true
  try {
    await riskApi.generate(projectId.value)
    ElMessage.success('风险画像生成成功')
    loadProfiles()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  // 风险等级分布饼图
  if (riskChartRef.value) {
    const chart = echarts.init(riskChartRef.value)
    const riskCounts = { high: 0, medium: 0, low: 0 }
    profiles.value.forEach(p => {
      riskCounts[p.risk_level] = (riskCounts[p.risk_level] || 0) + 1
    })

    chart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { value: riskCounts.high, name: '高风险', itemStyle: { color: '#f56c6c' } },
          { value: riskCounts.medium, name: '中风险', itemStyle: { color: '#e6a23c' } },
          { value: riskCounts.low, name: '低风险', itemStyle: { color: '#67c23a' } }
        ]
      }]
    })
  }

  // 科目风险分布柱状图
  if (subjectChartRef.value) {
    const chart = echarts.init(subjectChartRef.value)
    const topProfiles = profiles.value.slice(0, 10)

    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: topProfiles.map(p => p.subject_name?.slice(0, 6) || ''),
        axisLabel: { interval: 0, rotate: 30 }
      },
      yAxis: { type: 'value', max: 100 },
      series: [{
        type: 'bar',
        data: topProfiles.map(p => ({
          value: p.risk_score,
          itemStyle: { color: getRiskColor(p.risk_level) }
        }))
      }]
    })
  }
}

const viewDetail = (profile) => {
  currentProfile.value = profile
  detailDialogVisible.value = true
}

const goToSampling = (profile) => {
  router.push({
    path: '/sampling/strategy',
    query: { subject_code: profile.subject_code }
  })
}

onMounted(() => {
  loadProfiles()
})
</script>