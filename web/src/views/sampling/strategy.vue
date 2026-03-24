<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">抽样策略</h2>
    </div>

    <!-- 参数调整面板 -->
    <el-card class="card-container">
      <template #header>抽样参数配置</template>
      <el-form :model="params" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="置信水平">
              <el-slider v-model="params.confidenceLevel" :marks="confidenceMarks" :step="5" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="可容忍误差">
              <el-slider v-model="params.tolerableError" :marks="errorMarks" :step="1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="预期偏差率">
              <el-slider v-model="params.expectedError" :marks="errorMarks" :step="1" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button type="primary" @click="calculateSampleSize">计算样本量</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 计算结果 -->
    <el-card class="card-container" style="margin-top: 20px">
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
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'

const route = useRoute()
const chartRef = ref()

const params = reactive({
  confidenceLevel: 95,
  tolerableError: 5,
  expectedError: 3
})

const result = reactive({
  sampleSize: 0,
  samplingRate: 0,
  populationSize: 1000,
  confidenceLevel: 95
})

const confidenceMarks = { 90: '90%', 95: '95%', 99: '99%' }
const errorMarks = { 1: '1%', 5: '5%', 10: '10%' }

const methodDescriptions = [
  { method: '随机抽样', scenario: '低风险科目', description: '使用统计公式计算样本量，随机抽取样本' },
  { method: '分层抽样', scenario: '中风险科目', description: '按金额分层，不同层采用不同抽样比例' },
  { method: '判断抽样', scenario: '高风险科目', description: '基于专业判断，重点审查异常和大额交易' }
]

const zValues = { 90: 1.645, 95: 1.96, 99: 2.576 }

const calculateSampleSize = () => {
  const z = zValues[params.confidenceLevel] || 1.96
  const p = params.expectedError / 100
  const e = params.tolerableError / 100
  const N = result.populationSize

  // 计算样本量: n = (Z² × p × (1-p)) / e²
  const n = (z * z * p * (1 - p)) / (e * e)

  // 有限总体校正
  const nAdjusted = Math.round(n * N / (N + n - 1))

  result.sampleSize = nAdjusted
  result.samplingRate = ((nAdjusted / N) * 100).toFixed(1)
  result.confidenceLevel = params.confidenceLevel

  nextTick(() => {
    renderChart()
  })
}

const renderChart = () => {
  if (!chartRef.value) return

  const chart = echarts.init(chartRef.value)

  // 生成不同置信水平下的样本量
  const data = []
  for (let cl = 85; cl <= 99; cl += 1) {
    const z = zValues[Math.round(cl / 5) * 5] || 1.96
    const p = params.expectedError / 100
    const e = params.tolerableError / 100
    const N = result.populationSize
    const n = Math.round((z * z * p * (1 - p)) / (e * e) * N / (N + (z * z * p * (1 - p)) / (e * e) - 1))
    data.push([cl, n])
  }

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'value',
      name: '置信水平(%)',
      min: 85,
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

onMounted(() => {
  // 从路由参数获取科目代码
  const subjectCode = route.query.subject_code
  if (subjectCode) {
    // TODO: 根据科目获取总体规模
  }

  calculateSampleSize()
})
</script>

<style lang="scss" scoped>
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