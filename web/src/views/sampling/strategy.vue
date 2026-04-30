<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">抽样策略</h2>
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-select
          v-model="projectId"
          placeholder="选择项目"
          style="width: 200px"
          @change="onProjectChange"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
        <el-select
          v-model="selectedSubject"
          placeholder="选择科目"
          style="width: 200px"
          @change="onSubjectChange"
          :disabled="!projectId"
        >
          <el-option
            v-for="subject in subjects"
            :key="subject.code"
            :label="`${subject.code} - ${subject.name}`"
            :value="subject.code"
          />
        </el-select>
      </div>
    </div>

    <!-- 总体信息 -->
    <el-card class="card-container" v-if="populationStats.population_size > 0">
      <template #header>总体信息</template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ populationStats.population_size }}</div>
            <div class="stat-label">总体规模</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ formatAmount(populationStats.total_amount) }}</div>
            <div class="stat-label">总金额</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ formatAmount(populationStats.avg_amount) }}</div>
            <div class="stat-label">平均金额</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ populationStats.subjects?.length || 0 }}</div>
            <div class="stat-label">科目数量</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 参数调整面板 -->
    <el-card class="card-container" style="margin-top: 20px">
      <template #header>抽样参数配置</template>
      <el-form :model="params" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="置信水平">
              <el-slider
                v-model="params.confidenceLevel"
                :min="85"
                :max="99"
                :marks="confidenceMarks"
                :step="5"
                :format-tooltip="formatPercent"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="可容忍误差">
              <el-slider
                v-model="params.tolerableError"
                :min="1"
                :max="20"
                :marks="errorMarks"
                :step="1"
                :format-tooltip="formatPercent"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="预期偏差率">
              <el-slider
                v-model="params.expectedError"
                :min="1"
                :max="15"
                :marks="expectedErrorMarks"
                :step="1"
                :format-tooltip="formatPercent"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button type="primary" @click="calculateSampleSize" :loading="calculating" :disabled="!projectId">
            计算样本量
          </el-button>
          <el-button @click="getStrategyRecommend" :loading="loadingStrategy" :disabled="!projectId">
            获取策略推荐
          </el-button>
          <span v-if="!selectedSubject" style="color: #909399; font-size: 12px; margin-left: 8px;">
            未选择科目将对整个项目生成综合策略
          </span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 计算结果 -->
    <el-card class="card-container" style="margin-top: 20px" v-if="result.sampleSize > 0">
      <template #header>计算结果</template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="result-item">
            <div class="result-value">{{ result.sampleSize }}</div>
            <div class="result-label">推荐样本量</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item">
            <div class="result-value">{{ result.samplingRate }}%</div>
            <div class="result-label">抽样比例</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item">
            <div class="result-value">{{ result.populationSize }}</div>
            <div class="result-label">总体规模</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="result-item">
            <div class="result-value">{{ result.confidenceLevel }}%</div>
            <div class="result-label">置信水平</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 策略推荐结果 -->
    <el-card class="card-container" style="margin-top: 20px" v-if="strategy.method">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>策略推荐</span>
          <el-tag :type="getRiskType(strategy.riskLevel)">
            {{ getRiskLabel(strategy.riskLevel) }}风险
          </el-tag>
        </div>
      </template>

      <el-descriptions :column="4" border>
        <el-descriptions-item label="科目">
          <el-tag v-if="strategy.subjectCode === 'ALL'" type="info">项目整体</el-tag>
          <span v-else>{{ strategy.subjectCode }} - {{ strategy.subjectName }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="推荐方法">
          <el-tag>{{ getMethodLabel(strategy.method) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="样本量">{{ strategy.sampleSize }} 笔</el-descriptions-item>
        <el-descriptions-item label="抽样比例">{{ (strategy.samplingRate * 100).toFixed(1) }}%</el-descriptions-item>
      </el-descriptions>

      <div style="margin-top: 16px;">
        <strong>策略依据：</strong>
        <p style="margin-top: 8px; color: #606266;">{{ strategy.rationale }}</p>
      </div>

      <!-- 科目分析（项目级别时显示） -->
      <div v-if="strategy.subjectsAnalysis && strategy.subjectsAnalysis.length > 0" style="margin-top: 16px;">
        <strong>科目分析（按金额排序）：</strong>
        <el-table :data="strategy.subjectsAnalysis" style="margin-top: 8px;" max-height="300">
          <el-table-column prop="code" label="科目代码" width="120" />
          <el-table-column prop="name" label="科目名称" min-width="150" />
          <el-table-column prop="count" label="凭证数" width="100" />
          <el-table-column label="金额" width="150">
            <template #default="{ row }">
              {{ formatAmount(row.total_amount) }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 分层抽样详情 -->
      <div v-if="strategy.stratification && strategy.stratification.length > 0" style="margin-top: 16px;">
        <strong>分层详情：</strong>
        <el-table :data="strategy.stratification" style="margin-top: 8px;">
          <el-table-column prop="name" label="层级" width="100" />
          <el-table-column label="金额范围" width="280">
            <template #default="{ row }">
              {{ formatAmount(row.min_amount) }} - {{ formatAmount(row.max_amount) }}
            </template>
          </el-table-column>
          <el-table-column prop="count" label="凭证数" width="100" />
          <el-table-column prop="sample_size" label="样本量" width="100" />
          <el-table-column label="抽样方法" width="120">
            <template #default="{ row }">
              {{ getMethodLabel(row.method) }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 重点关注领域 -->
      <div v-if="strategy.keyFocusAreas && strategy.keyFocusAreas.length > 0" style="margin-top: 16px;">
        <strong>重点关注领域：</strong>
        <div style="margin-top: 8px;">
          <el-tag v-for="area in strategy.keyFocusAreas" :key="area" style="margin-right: 8px;">{{ area }}</el-tag>
        </div>
      </div>

      <div style="margin-top: 16px;">
        <el-button type="primary" @click="goToExecute">应用策略并执行抽样</el-button>
      </div>
    </el-card>

    <!-- 样本量曲线图 -->
    <el-card class="card-container" style="margin-top: 20px">
      <template #header>样本量-置信度曲线</template>
      <div ref="chartRef" style="height: 300px"></div>
    </el-card>

    <!-- 抽样方法说明 -->
    <el-card class="card-container" style="margin-top: 20px">
      <template #header>抽样方法说明</template>
      <el-table :data="methodDescriptions" style="width: 100%">
        <el-table-column prop="method" label="抽样方法" width="150" />
        <el-table-column prop="scenario" label="适用场景" width="200" />
        <el-table-column prop="description" label="说明" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { samplingApi, projectApi } from '@/api'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()
const chartRef = ref()

const projectId = ref(localStorage.getItem('currentProjectId') || '')
const projects = ref([])
const subjects = ref([])
const selectedSubject = ref('')
const calculating = ref(false)
const loadingStrategy = ref(false)

const populationStats = reactive({
  population_size: 0,
  total_amount: 0,
  avg_amount: 0,
  min_amount: 0,
  max_amount: 0,
  subjects: []
})

const params = reactive({
  confidenceLevel: 95,
  tolerableError: 5,
  expectedError: 3
})

const result = reactive({
  sampleSize: 0,
  samplingRate: 0,
  populationSize: 0,
  confidenceLevel: 95
})

const strategy = reactive({
  method: '',
  subjectCode: '',
  subjectName: '',
  riskLevel: '',
  sampleSize: 0,
  samplingRate: 0,
  rationale: '',
  stratification: [],
  keyFocusAreas: [],
  subjectsAnalysis: []
})

const confidenceMarks = { 85: '85%', 90: '90%', 95: '95%', 99: '99%' }
const errorMarks = { 1: '1%', 10: '10%', 20: '20%' }
const expectedErrorMarks = { 1: '1%', 5: '5%', 10: '10%', 15: '15%' }

const methodDescriptions = [
  { method: '随机抽样', scenario: '低风险科目', description: '使用统计公式计算样本量，随机抽取样本' },
  { method: '分层抽样', scenario: '中风险科目', description: '按金额分层，不同层采用不同抽样比例' },
  { method: '判断抽样', scenario: '高风险科目', description: '基于专业判断，重点审查异常和大额交易' },
  { method: '系统抽样', scenario: '常规审计', description: '按固定间隔抽取样本，适合有序数据' },
  { method: '货币单位抽样', scenario: '金额重要性', description: '以金额为抽样单位，大额凭证抽中概率更高' }
]

const formatPercent = (val) => `${val}%`

const formatAmount = (amount) => {
  if (!amount) return '0.00'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const getRiskType = (level) => {
  const types = { high: 'danger', medium: 'warning', low: 'success' }
  return types[level] || 'info'
}

const getRiskLabel = (level) => {
  const labels = { high: '高', medium: '中', low: '低' }
  return labels[level] || level
}

const getMethodLabel = (method) => {
  const labels = {
    random: '随机抽样',
    stratified: '分层抽样',
    judgment: '判断抽样',
    systematic: '系统抽样',
    monetary_unit: '货币单位抽样'
  }
  return labels[method] || method
}

const loadProjects = async () => {
  try {
    const res = await projectApi.getList({ page: 1, page_size: 100 })
    projects.value = res.items || []

    if (projectId.value) {
      const exists = projects.value.some(p => p.id === projectId.value)
      if (!exists) {
        projectId.value = ''
        localStorage.removeItem('currentProjectId')
      }
    }
  } catch (error) {
    console.error(error)
  }
}

const loadPopulationStats = async () => {
  if (!projectId.value) return

  try {
    const res = await samplingApi.getPopulationStats(projectId.value, selectedSubject.value || null)
    Object.assign(populationStats, res)
    result.populationSize = res.population_size
    subjects.value = res.subjects || []
  } catch (error) {
    console.error(error)
  }
}

const onProjectChange = (val) => {
  localStorage.setItem('currentProjectId', val)
  selectedSubject.value = ''
  resetResult()
  loadPopulationStats()
}

const onSubjectChange = () => {
  resetResult()
  loadPopulationStats()
}

const resetResult = () => {
  result.sampleSize = 0
  result.samplingRate = 0
  strategy.method = ''
  strategy.stratification = []
  strategy.subjectsAnalysis = []
}

const calculateSampleSize = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  calculating.value = true
  try {
    const res = await samplingApi.calculateSampleSize(projectId.value, {
      population_size: populationStats.population_size,
      confidence_level: params.confidenceLevel / 100,
      tolerable_error: params.tolerableError / 100,
      expected_error: params.expectedError / 100
    })

    result.sampleSize = res.sample_size
    result.samplingRate = (res.sampling_rate * 100).toFixed(1)
    result.confidenceLevel = params.confidenceLevel

    nextTick(() => {
      renderChart(res.curve_data)
    })
  } catch (error) {
    console.error(error)
    ElMessage.error('计算失败')
  } finally {
    calculating.value = false
  }
}

const getStrategyRecommend = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  loadingStrategy.value = true
  try {
    const res = await samplingApi.getStrategyRecommend(projectId.value, selectedSubject.value || null, {
      confidence_level: params.confidenceLevel / 100,
      tolerable_error: params.tolerableError / 100 > 0 ? params.tolerableError / 100 : undefined,
      expected_error: params.expectedError / 100 > 0 ? params.expectedError / 100 : undefined
    })

    strategy.method = res.method
    strategy.subjectCode = res.subject_code
    strategy.subjectName = res.subject_name
    strategy.riskLevel = res.risk_level
    strategy.sampleSize = res.sample_size
    strategy.samplingRate = res.sampling_rate
    strategy.rationale = res.rationale
    strategy.stratification = res.stratification || []
    strategy.keyFocusAreas = res.key_focus_areas || []
    strategy.subjectsAnalysis = res.subjects_analysis || []

    result.sampleSize = res.sample_size
    result.samplingRate = (res.sampling_rate * 100).toFixed(1)
    result.populationSize = res.total_population
  } catch (error) {
    console.error(error)
    ElMessage.error('获取策略推荐失败')
  } finally {
    loadingStrategy.value = false
  }
}

const goToExecute = () => {
  router.push({
    path: '/sampling/execute',
    query: {
      subject_code: strategy.subjectCode,
      sample_size: strategy.sampleSize,
      method: strategy.method
    }
  })
}

const renderChart = (curveData) => {
  if (!chartRef.value) return

  const chart = echarts.init(chartRef.value)

  // 使用后端返回的曲线数据
  const data = curveData ? curveData.map(c => [c.confidence_level * 100, c.sample_size]) : []

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'value',
      name: '置信水平(%)',
      min: 80,
      max: 99
    },
    yAxis: {
      type: 'value',
      name: '样本量'
    },
    series: [{
      type: 'line',
      data: data,
      smooth: true,
      markPoint: {
        data: [
          { type: 'max', name: '最大值' },
          { type: 'min', name: '最小值' }
        ]
      }
    }]
  })
}

onMounted(async () => {
  await loadProjects()
  if (projectId.value) {
    await loadPopulationStats()
  }

  // 从路由参数获取科目代码（从风险画像跳转）
  const subjectCode = route.query.subject_code
  if (subjectCode) {
    selectedSubject.value = subjectCode
    await loadPopulationStats()
  }

  // 如果有总体规模，自动计算
  if (populationStats.population_size > 0) {
    calculateSampleSize()
  }
})
</script>

<style lang="scss" scoped>
/* 覆盖页面容器边距，参考凭证管理页面 */
.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

.el-form-item {
  margin-bottom: 40px;

  :deep(.el-slider__marks) {
    margin-top: 12px;
  }
}

.stat-item {
  text-align: center;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;

  .stat-value {
    font-size: 24px;
    font-weight: bold;
    color: #409eff;
  }

  .stat-label {
    font-size: 14px;
    color: #909399;
    margin-top: 8px;
  }
}

.result-item {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;

  .result-value {
    font-size: 36px;
    font-weight: bold;
    color: #409eff;
  }

  .result-label {
    font-size: 14px;
    color: #909399;
    margin-top: 10px;
  }
}
</style>
