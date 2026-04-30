<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">总体推断</h2>
    </div>

    <!-- 选择抽样记录 -->
    <el-card class="selection-card">
      <el-form :inline="true">
        <el-form-item label="抽样记录">
          <el-select v-model="selectedRecordId" placeholder="选择抽样记录" style="width: 400px" @change="loadSummary">
            <el-option
              v-for="item in summaries"
              :key="item.record_id"
              :label="`${item.rule_name} (${item.sample_size}张样本)`"
              :value="item.record_id"
            >
              <div style="display: flex; justify-content: space-between; width: 100%">
                <span>{{ item.rule_name }}</span>
                <el-tag v-if="item.inference_completed" type="success" size="small">已推断</el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="置信水平">
          <el-select v-model="confidenceLevel" style="width: 120px">
            <el-option label="90%" :value="0.90" />
            <el-option label="95%" :value="0.95" />
            <el-option label="99%" :value="0.99" />
          </el-select>
        </el-form-item>
        <el-form-item label="可容忍误差">
          <el-input-number v-model="tolerableError" :min="1" :max="20" :precision="1" />
          <span style="margin-left: 8px">%</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="executeInference" :loading="calculating" :disabled="!selectedRecordId">
            执行推断
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 推断结果 -->
    <el-card v-if="inferenceResult" class="result-card">
      <div class="result-header">
        <el-icon :size="48" :color="inferenceResult.is_acceptable ? '#10b981' : '#ef4444'">
          <CircleCheck v-if="inferenceResult.is_acceptable" />
          <Warning v-else />
        </el-icon>
        <div class="result-title">
          <h3 :class="inferenceResult.is_acceptable ? 'success' : 'danger'">
            {{ inferenceResult.is_acceptable ? '可接受' : '需关注' }}
          </h3>
          <p>{{ getMethodLabel(inferenceResult.method) }} | 置信水平 {{ (inferenceResult.confidence_level * 100).toFixed(0) }}%</p>
        </div>
      </div>

      <el-divider />

      <!-- 统计数据 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :span="4">
          <div class="stat-box">
            <div class="stat-value">{{ inferenceResult.sample_size }}</div>
            <div class="stat-label">样本量</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-box">
            <div class="stat-value">{{ inferenceResult.population_size }}</div>
            <div class="stat-label">总体规模</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-box">
            <div class="stat-value">{{ inferenceResult.misstatement_count }}</div>
            <div class="stat-label">错报笔数</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-box highlight">
            <div class="stat-value">{{ formatAmount(inferenceResult.projected_misstatement) }}</div>
            <div class="stat-label">推断错报</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-box">
            <div class="stat-value">{{ formatAmount(inferenceResult.upper_limit) }}</div>
            <div class="stat-label">错报上限</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-box">
            <div class="stat-value">{{ formatAmount(inferenceResult.precision) }}</div>
            <div class="stat-label">精度</div>
          </div>
        </el-col>
      </el-row>

      <!-- 置信区间可视化 -->
      <div class="chart-section">
        <h4>置信区间</h4>
        <div class="interval-chart">
          <div class="interval-bar">
            <div class="interval-range" :style="intervalStyle"></div>
            <div class="interval-point" :style="pointStyle"></div>
          </div>
          <div class="interval-labels">
            <span>{{ formatAmount(inferenceResult.lower_limit) }}</span>
            <span class="point-label">{{ formatAmount(inferenceResult.projected_misstatement) }}</span>
            <span>{{ formatAmount(inferenceResult.upper_limit) }}</span>
          </div>
        </div>
      </div>

      <!-- 结论 -->
      <el-alert
        :title="inferenceResult.is_acceptable ? '结论：可接受' : '结论：需关注'"
        :type="inferenceResult.is_acceptable ? 'success' : 'warning'"
        :description="inferenceResult.conclusion"
        show-icon
        :closable="false"
        style="margin-top: 20px"
      />

      <!-- 建议列表 -->
      <div v-if="inferenceResult.recommendations?.length" class="recommendations">
        <h4>扩展测试建议</h4>
        <el-alert
          v-for="(rec, index) in inferenceResult.recommendations"
          :key="index"
          :title="rec"
          type="warning"
          :closable="false"
          style="margin-bottom: 10px"
        />
      </div>
    </el-card>

    <!-- 错报汇总 -->
    <el-card v-if="selectedRecordId" class="summary-card">
      <template #header>
        <div class="card-header">
          <span>样本错报汇总</span>
          <el-button type="primary" link @click="goToTest">进入样本测试</el-button>
        </div>
      </template>
      <el-descriptions :column="4" border>
        <el-descriptions-item label="样本总数">
          {{ currentSummary?.sample_size || 0 }} 张
        </el-descriptions-item>
        <el-descriptions-item label="已测试">
          {{ currentSummary?.tested_count || 0 }} 张
        </el-descriptions-item>
        <el-descriptions-item label="错报笔数">
          <span :class="{ 'error-text': currentSummary?.misstatement_count > 0 }">
            {{ currentSummary?.misstatement_count || 0 }} 笔
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="错报金额">
          <span :class="{ 'error-text': currentSummary?.total_misstatement_amount > 0 }">
            {{ formatAmount(currentSummary?.total_misstatement_amount || 0) }}
          </span>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 错报类型分布 -->
      <div v-if="misstatements.length > 0" style="margin-top: 20px">
        <h4>错报明细</h4>
        <el-table :data="misstatements" size="small" max-height="300">
          <el-table-column prop="sample_id" label="样本ID" width="280" />
          <el-table-column prop="misstatement_type" label="错报类型" width="120">
            <template #default="{ row }">
              {{ getTypeLabel(row.misstatement_type) }}
            </template>
          </el-table-column>
          <el-table-column prop="misstatement_amount" label="错报金额" width="150" align="right">
            <template #default="{ row }">
              {{ formatAmount(row.misstatement_amount) }}
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        </el-table>
      </div>
    </el-card>

    <!-- 空状态 -->
    <el-empty v-if="!selectedRecordId" description="请先选择抽样记录" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Warning } from '@element-plus/icons-vue'
import { samplingApi } from '@/api'

const router = useRouter()
const summaries = ref([])
const selectedRecordId = ref('')
const confidenceLevel = ref(0.95)
const tolerableError = ref(5)
const calculating = ref(false)
const inferenceResult = ref(null)
const misstatements = ref([])

const currentSummary = computed(() => {
  return summaries.value.find(s => s.record_id === selectedRecordId.value)
})

const intervalStyle = computed(() => {
  if (!inferenceResult.value) return {}
  const { lower_limit, upper_limit, population_amount } = inferenceResult.value
  const total = population_amount || upper_limit * 2
  const left = (lower_limit / total) * 100
  const width = ((upper_limit - lower_limit) / total) * 100
  return {
    left: `${Math.max(0, left)}%`,
    width: `${Math.min(100, width)}%`
  }
})

const pointStyle = computed(() => {
  if (!inferenceResult.value) return {}
  const { projected_misstatement, population_amount, upper_limit } = inferenceResult.value
  const total = population_amount || upper_limit * 2
  const left = (projected_misstatement / total) * 100
  return {
    left: `${Math.min(100, left)}%`
  }
})

const loadSummaries = async () => {
  const projectId = localStorage.getItem('currentProjectId')
  if (!projectId) return

  try {
    const data = await samplingApi.getInferenceSummaries(projectId)
    summaries.value = data || []
  } catch (error) {
    console.error('加载摘要失败:', error)
  }
}

const loadSummary = async () => {
  if (!selectedRecordId.value) return

  const projectId = localStorage.getItem('currentProjectId')

  try {
    // 加载错报列表
    const data = await samplingApi.getMisstatements(projectId)
    misstatements.value = (data || []).filter(m => {
      // 这里应该根据record_id过滤，但API目前不支持
      return true
    })
  } catch (error) {
    console.error('加载错报失败:', error)
  }
}

const executeInference = async () => {
  if (!selectedRecordId.value) return

  const projectId = localStorage.getItem('currentProjectId')
  calculating.value = true

  try {
    const result = await samplingApi.executeInference(projectId, {
      record_id: selectedRecordId.value,
      confidence_level: confidenceLevel.value,
      tolerable_error: tolerableError.value / 100
    })
    inferenceResult.value = result
    ElMessage.success('推断计算完成')
  } catch (error) {
    ElMessage.error('推断失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    calculating.value = false
  }
}

const goToTest = () => {
  router.push('/sampling/test')
}

const formatAmount = (amount) => {
  if (amount === null || amount === undefined) return '-'
  return '¥' + amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const getMethodLabel = (method) => {
  const map = {
    monetary_unit: '货币单位抽样(MUS)',
    systematic: '系统抽样',
    random: '随机抽样',
    stratified: '分层抽样'
  }
  return map[method] || method
}

const getTypeLabel = (type) => {
  const map = {
    amount_error: '金额错误',
    missing_doc: '缺少单据',
    fictitious: '虚构交易',
    classification: '分类错误',
    other: '其他'
  }
  return map[type] || type
}

onMounted(() => {
  loadSummaries()
})
</script>

<style lang="scss" scoped>
/* 覆盖页面容器边距，参考凭证管理页面 */
.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

.selection-card {
  margin-bottom: 20px;
}

.result-card {
  margin-bottom: 20px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 20px;

  .result-title {
    h3 {
      margin: 0;
      font-size: 24px;

      &.success { color: #10b981; }
      &.danger { color: #ef4444; }
    }

    p {
      margin: 4px 0 0;
      color: #909399;
      font-size: 14px;
    }
  }
}

.stats-row {
  margin: 20px 0;
}

.stat-box {
  text-align: center;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;

  &.highlight {
    background: #fef0f0;
  }

  .stat-value {
    font-size: 22px;
    font-weight: 600;
    color: #303133;
  }

  .stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 4px;
  }
}

.chart-section {
  margin-top: 24px;

  h4 {
    margin-bottom: 16px;
    font-size: 15px;
    color: #606266;
  }
}

.interval-chart {
  .interval-bar {
    position: relative;
    height: 20px;
    background: #e4e7ed;
    border-radius: 10px;
    margin: 0 60px;

    .interval-range {
      position: absolute;
      height: 100%;
      background: linear-gradient(90deg, #409eff, #67c23a);
      border-radius: 10px;
      opacity: 0.6;
    }

    .interval-point {
      position: absolute;
      top: 50%;
      transform: translate(-50%, -50%);
      width: 16px;
      height: 16px;
      background: #f56c6c;
      border-radius: 50%;
      border: 3px solid #fff;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
    }
  }

  .interval-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 8px;
    padding: 0 60px;
    font-size: 13px;
    color: #606266;

    .point-label {
      font-weight: 600;
      color: #f56c6c;
    }
  }
}

.recommendations {
  margin-top: 24px;

  h4 {
    margin-bottom: 12px;
    font-size: 15px;
    color: #606266;
  }
}

.summary-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.error-text {
  color: #f56c6c;
  font-weight: 600;
}
</style>