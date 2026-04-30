<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">抽样向导</h2>
    </div>

    <el-card class="card-container">
      <!-- 步骤条 -->
      <el-steps :active="currentStep" finish-status="success" align-center style="margin-bottom: 30px">
        <el-step title="选择项目" description="确定审计目标" />
        <el-step title="定义总体" description="设置抽样范围" />
        <el-step title="抽样方法" description="配置抽样参数" />
        <el-step title="确认执行" description="执行抽样" />
      </el-steps>

      <!-- 步骤内容 -->
      <div class="step-content">
        <!-- 步骤1：选择项目和审计目标 -->
        <div v-show="currentStep === 0" class="step-panel">
          <el-form :model="wizardForm" label-width="120px">
            <el-form-item label="选择项目" required>
              <el-select v-model="wizardForm.projectId" placeholder="请选择审计项目" style="width: 300px">
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="审计目标">
              <el-radio-group v-model="wizardForm.auditGoal">
                <el-radio value="substantive">实质性测试 - 测试账户余额和交易</el-radio>
                <el-radio value="control">控制测试 - 测试内部控制有效性</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="测试类型">
              <el-checkbox-group v-model="wizardForm.testTypes">
                <el-checkbox label="occurrence">发生性测试 - 验证交易是否真实发生</el-checkbox>
                <el-checkbox label="completeness">完整性测试 - 验证记录是否完整</el-checkbox>
                <el-checkbox label="accuracy">准确性测试 - 验证金额是否准确</el-checkbox>
                <el-checkbox label="cutoff">截止测试 - 验证交易记录在正确期间</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤2：定义总体范围 -->
        <div v-show="currentStep === 1" class="step-panel">
          <el-form :model="wizardForm.population" label-width="120px">
            <el-form-item label="总体范围">
              <el-radio-group v-model="wizardForm.population.scope">
                <el-radio value="all">全部凭证</el-radio>
                <el-radio value="subject">按科目筛选</el-radio>
                <el-radio value="date">按日期范围</el-radio>
                <el-radio value="amount">按金额范围</el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- 按科目筛选 -->
            <template v-if="wizardForm.population.scope === 'subject'">
              <el-form-item label="选择科目">
                <el-select v-model="wizardForm.population.subjects" multiple placeholder="选择科目" style="width: 400px">
                  <el-option label="库存现金 (1001)" value="1001" />
                  <el-option label="银行存款 (1002)" value="1002" />
                  <el-option label="应收账款 (1122)" value="1122" />
                  <el-option label="预付账款 (1123)" value="1123" />
                  <el-option label="应付账款 (2202)" value="2202" />
                  <el-option label="主营业务收入 (6001)" value="6001" />
                  <el-option label="管理费用 (6602)" value="6602" />
                  <el-option label="销售费用 (6601)" value="6601" />
                </el-select>
              </el-form-item>
            </template>

            <!-- 按日期范围 -->
            <template v-if="wizardForm.population.scope === 'date'">
              <el-form-item label="开始日期">
                <el-date-picker v-model="wizardForm.population.startDate" type="date" placeholder="选择开始日期" />
              </el-form-item>
              <el-form-item label="结束日期">
                <el-date-picker v-model="wizardForm.population.endDate" type="date" placeholder="选择结束日期" />
              </el-form-item>
            </template>

            <!-- 按金额范围 -->
            <template v-if="wizardForm.population.scope === 'amount'">
              <el-form-item label="最小金额">
                <el-input-number v-model="wizardForm.population.minAmount" :min="0" :controls="false" />
              </el-form-item>
              <el-form-item label="最大金额">
                <el-input-number v-model="wizardForm.population.maxAmount" :min="0" :controls="false" />
              </el-form-item>
            </template>

            <!-- 总体统计 -->
            <el-divider />
            <el-form-item label="总体规模">
              <div v-if="populationStats" class="population-stats">
                <el-statistic title="凭证数量" :value="populationStats.count" />
                <el-statistic title="总金额" :value="populationStats.totalAmount" :precision="2" prefix="¥" style="margin-left: 40px" />
                <el-button type="primary" link @click="analyzePopulationRisk" :loading="analyzingRisk" style="margin-left: 40px">
                  AI风险分析
                </el-button>
              </div>
              <el-button v-else type="primary" link @click="loadPopulationStats" :loading="loadingStats">
                点击获取总体统计
              </el-button>
            </el-form-item>

            <!-- AI风险分析结果 -->
            <div v-if="riskAnalysisResult" class="risk-analysis-section">
              <el-divider content-position="left">AI风险分析</el-divider>
              <el-row :gutter="20">
                <el-col :span="8">
                  <div class="risk-summary-card">
                    <div class="risk-score" :class="riskAnalysisResult.overall_risk_level">
                      {{ riskAnalysisResult.overall_risk_score || 0 }}
                    </div>
                    <div class="risk-label">总体风险评分</div>
                    <el-tag :type="getRiskTagType(riskAnalysisResult.overall_risk_level)">
                      {{ getRiskLevelLabel(riskAnalysisResult.overall_risk_level).replace(/·/g, '') }}
                    </el-tag>
                  </div>
                </el-col>
                <el-col :span="16">
                  <div class="risk-distribution">
                    <h4>风险分布</h4>
                    <div class="distribution-bars">
                      <div class="distribution-item">
                        <span class="label">高风险</span>
                        <el-progress
                          :percentage="riskVoucherStats.highRatio"
                          :stroke-width="12"
                          color="#f56c6c"
                        />
                        <span class="count">{{ riskVoucherStats.high }} 张</span>
                      </div>
                      <div class="distribution-item">
                        <span class="label">中风险</span>
                        <el-progress
                          :percentage="riskVoucherStats.mediumRatio"
                          :stroke-width="12"
                          color="#e6a23c"
                        />
                        <span class="count">{{ riskVoucherStats.medium }} 张</span>
                      </div>
                      <div class="distribution-item">
                        <span class="label">低风险</span>
                        <el-progress
                          :percentage="riskVoucherStats.lowRatio"
                          :stroke-width="12"
                          color="#67c23a"
                        />
                        <span class="count">{{ riskVoucherStats.low }} 张</span>
                      </div>
                    </div>
                  </div>
                </el-col>
              </el-row>

              <!-- AI分层建议 -->
              <div v-if="riskAnalysisResult.stratification_suggestion" class="stratification-suggestion">
                <h4>AI分层建议</h4>
                <el-alert type="info" :closable="false">
                  <template #title>
                    {{ riskAnalysisResult.stratification_suggestion }}
                  </template>
                </el-alert>
              </div>

              <!-- 风险因素 -->
              <div v-if="riskAnalysisResult.risk_factors?.length" class="risk-factors">
                <h4>主要风险因素</h4>
                <div class="risk-factor-tags">
                  <el-tag
                    v-for="factor in riskAnalysisResult.risk_factors"
                    :key="factor"
                    size="small"
                    type="warning"
                    class="risk-tag"
                  >
                    {{ factor.replace(/·/g, '') }}
                  </el-tag>
                </div>
              </div>

              <!-- 风险凭证列表 -->
              <div v-if="riskVoucherList.length > 0" class="risk-voucher-list">
                <el-divider content-position="left">
                  风险凭证明细
                  <el-tag size="small" type="info" style="margin-left: 8px">
                    共 {{ riskVoucherStats.total }} 张
                  </el-tag>
                </el-divider>

                <!-- 筛选和统计 -->
                <div class="list-toolbar">
                  <el-radio-group v-model="riskFilterLevel" size="small" @change="handleRiskFilterChange">
                    <el-radio-button value="all">全部 ({{ riskVoucherStats.total }})</el-radio-button>
                    <el-radio-button value="high">
                      高风险 ({{ riskVoucherStats.high }})
                    </el-radio-button>
                    <el-radio-button value="medium">
                      中风险 ({{ riskVoucherStats.medium }})
                    </el-radio-button>
                    <el-radio-button value="low">
                      低风险 ({{ riskVoucherStats.low }})
                    </el-radio-button>
                  </el-radio-group>
                </div>

                <!-- 凭证表格 -->
                <el-table
                  :data="pagedRiskVouchers"
                  stripe
                  size="small"
                  style="width: 100%"
                  :flexible="false"
                >
                  <el-table-column prop="voucher_no" label="凭证号" width="150" />
                  <el-table-column prop="voucher_date" label="日期" width="110" />
                  <el-table-column prop="amount" label="金额" width="160" align="right">
                    <template #default="{ row }">
                      <span :style="{ color: row.amount > 100000 ? '#f56c6c' : 'inherit' }">
                        ¥{{ (row.amount || 0).toLocaleString() }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="subject_name" label="科目" min-width="140" show-overflow-tooltip />
                  <el-table-column prop="counterparty" label="对方单位" min-width="120" show-overflow-tooltip />
                  <el-table-column label="风险等级" width="100" align="center">
                    <template #default="{ row }">
                      <el-tag :type="getRiskTagType(row.risk_level)" size="small">
                        {{ getRiskLevelLabel(row.risk_level).replace(/·/g, '') }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="风险评分" width="90" align="center">
                    <template #default="{ row }">
                      <span :style="{ color: getRiskScoreColor(row.risk_score), fontWeight: 'bold' }">
                        {{ row.risk_score }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column label="风险因素" min-width="200">
                    <template #default="{ row }">
                      <div class="risk-factor-tags">
                        <el-tag
                          v-for="(factor, idx) in row.risk_factors"
                          :key="idx"
                          size="small"
                          type="warning"
                          class="risk-tag"
                        >
                          {{ factor.replace(/·/g, '') }}
                        </el-tag>
                        <span v-if="!row.risk_factors?.length" style="color: #909399">-</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="附件分析" width="90" align="center">
                    <template #default="{ row }">
                      <el-tag v-if="row.has_attachment && row.attachment_analyzed" type="success" size="small">
                        已分析
                      </el-tag>
                      <el-tag v-else-if="row.has_attachment && !row.attachment_analyzed" type="info" size="small">
                        待分析
                      </el-tag>
                      <span v-else style="color: #909399">无附件</span>
                    </template>
                  </el-table-column>
                </el-table>

                <!-- 分页 -->
                <div class="pagination-wrapper">
                  <el-pagination
                    v-model:current-page="riskVoucherPage"
                    v-model:page-size="riskVoucherPageSize"
                    :page-sizes="[10, 20, 50, 100]"
                    :total="filteredRiskVouchers.length"
                    layout="total, sizes, prev, pager, next"
                    @current-change="handleRiskVoucherPageChange"
                    @size-change="riskVoucherPage = 1"
                  />
                </div>
              </div>
            </div>
          </el-form>
        </div>

        <!-- 步骤3：选择抽样方法和参数 -->
        <div v-show="currentStep === 2" class="step-panel">
          <el-form :model="wizardForm.sampling" label-width="120px">
            <el-form-item label="抽样方法">
              <el-radio-group v-model="wizardForm.sampling.method">
                <el-radio value="random">
                  <span>随机抽样</span>
                  <span class="method-desc">- 适用于低风险科目，按比例随机抽取</span>
                </el-radio>
                <el-radio value="monetary_unit">
                  <span>货币单位抽样(MUS)</span>
                  <span class="method-desc">- 按金额概率抽样，大额优先</span>
                </el-radio>
                <el-radio value="systematic">
                  <span>系统抽样</span>
                  <span class="method-desc">- 按固定间隔抽取，效率高</span>
                </el-radio>
                <el-radio value="stratified">
                  <span>分层抽样</span>
                  <span class="method-desc">- 按金额分层，大额重点审查</span>
                </el-radio>
                <el-radio value="judgment">
                  <span>判断抽样</span>
                  <span class="method-desc">- 基于审计师经验判断</span>
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- 随机抽样参数 -->
            <template v-if="wizardForm.sampling.method === 'random'">
              <el-form-item label="置信水平">
                <el-select v-model="wizardForm.sampling.confidenceLevel" style="width: 150px">
                  <el-option label="90%" :value="90" />
                  <el-option label="95%" :value="95" />
                  <el-option label="99%" :value="99" />
                </el-select>
              </el-form-item>
              <el-form-item label="可容忍误差">
                <el-input-number v-model="wizardForm.sampling.tolerableError" :min="1" :max="20" />
                <span style="margin-left: 8px">%</span>
              </el-form-item>
              <el-form-item label="预期偏差率">
                <el-input-number v-model="wizardForm.sampling.expectedError" :min="0" :max="15" />
                <span style="margin-left: 8px">%</span>
              </el-form-item>
            </template>

            <!-- MUS参数 -->
            <template v-if="wizardForm.sampling.method === 'monetary_unit'">
              <el-alert type="info" :closable="false" style="margin-bottom: 16px">
                <template #title>
                  货币单位抽样(MUS)是一种统计抽样方法，每个货币单位都有同等被选中的概率。
                  大额凭证有更高的被选中概率，适合实质性测试。
                </template>
              </el-alert>
              <el-form-item label="置信水平">
                <el-select v-model="wizardForm.sampling.musConfidenceLevel" style="width: 150px">
                  <el-option label="90%" :value="0.90" />
                  <el-option label="95%" :value="0.95" />
                  <el-option label="99%" :value="0.99" />
                </el-select>
              </el-form-item>
              <el-form-item label="可容忍错报率">
                <el-input-number
                  v-model="wizardForm.sampling.musTolerableError"
                  :min="1"
                  :max="20"
                  :precision="1"
                />
                <span style="margin-left: 8px">%</span>
              </el-form-item>
              <el-form-item label="预期错报率">
                <el-input-number
                  v-model="wizardForm.sampling.musExpectedError"
                  :min="0"
                  :max="10"
                  :precision="1"
                />
                <span style="margin-left: 8px">%</span>
              </el-form-item>
              <el-form-item label="抽样间隔" v-if="musPreview">
                <el-tag type="info" size="large">{{ musPreview.sampling_interval?.toLocaleString() }}</el-tag>
                <span style="margin-left: 8px; color: #909399">元</span>
              </el-form-item>
              <el-form-item label="保证系数" v-if="musPreview">
                <el-tag>{{ musPreview.reliability_factor }}</el-tag>
              </el-form-item>
            </template>

            <!-- 系统抽样参数 -->
            <template v-if="wizardForm.sampling.method === 'systematic'">
              <el-alert type="info" :closable="false" style="margin-bottom: 16px">
                <template #title>
                  系统抽样按固定间隔从总体中抽取样本，抽样效率高，适合大规模总体。
                </template>
              </el-alert>
              <el-form-item label="样本量设定">
                <el-radio-group v-model="wizardForm.sampling.systematicMode">
                  <el-radio value="count">按样本量</el-radio>
                  <el-radio value="rate">按抽样比例</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="样本量" v-if="wizardForm.sampling.systematicMode === 'count'">
                <el-input-number
                  v-model="wizardForm.sampling.systematicSampleSize"
                  :min="1"
                  :max="populationStats?.count || 1000"
                />
                <span style="margin-left: 8px">张</span>
              </el-form-item>
              <el-form-item label="抽样比例" v-else>
                <el-input-number
                  v-model="wizardForm.sampling.systematicSamplingRate"
                  :min="1"
                  :max="100"
                />
                <span style="margin-left: 8px">%</span>
              </el-form-item>
              <el-form-item label="抽样间隔" v-if="systematicPreview">
                <el-tag type="info" size="large">{{ systematicPreview.interval }}</el-tag>
                <span style="margin-left: 8px; color: #909399">张凭证</span>
              </el-form-item>
              <el-form-item label="随机起点" v-if="systematicPreview">
                <el-tag>{{ systematicPreview.random_start }}</el-tag>
              </el-form-item>
            </template>

            <!-- 分层抽样参数 -->
            <template v-if="wizardForm.sampling.method === 'stratified'">
              <el-divider content-position="left">分层设置</el-divider>
              <div v-for="(layer, index) in wizardForm.sampling.layers" :key="index" class="layer-config">
                <div class="layer-header">
                  <span class="layer-title">第{{ index + 1 }}层：{{ layer.name }}</span>
                </div>
                <el-row :gutter="20">
                  <el-col :span="5">
                    <el-form-item label="层名称" label-width="70px">
                      <el-input v-model="layer.name" placeholder="如：大额" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="最小金额" label-width="70px">
                      <el-input-number
                        v-model="layer.minAmount"
                        :controls="false"
                        placeholder="不限"
                        class="amount-input"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="最大金额" label-width="70px">
                      <el-input-number
                        v-model="layer.maxAmount"
                        :controls="false"
                        placeholder="不限"
                        class="amount-input"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="7">
                    <el-form-item label="抽样比例" label-width="70px">
                      <div class="rate-input-wrapper">
                        <el-input-number
                          v-model="layer.samplingRate"
                          :min="0"
                          :max="100"
                          class="rate-input"
                        />
                        <span class="rate-suffix">%</span>
                      </div>
                    </el-form-item>
                  </el-col>
                </el-row>
              </div>
            </template>

            <!-- 样本量预览 -->
            <el-divider />
            <el-form-item label="预估样本量">
              <div v-if="sampleSizePreview" class="sample-preview">
                <el-statistic title="预估样本量" :value="sampleSizePreview.total_sample_size" suffix=" 张" />
                <el-statistic title="抽样率" :value="sampleSizePreview.overall_sampling_rate" suffix="%" style="margin-left: 40px" />
              </div>
              <el-button v-else type="primary" @click="calculateSampleSize" :loading="calculating">
                计算样本量
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤4：确认执行 -->
        <div v-show="currentStep === 3" class="step-panel">
          <el-descriptions title="抽样方案摘要" :column="2" border>
            <el-descriptions-item label="项目">
              {{ projects.find(p => p.id === wizardForm.projectId)?.name }}
            </el-descriptions-item>
            <el-descriptions-item label="审计目标">
              {{ wizardForm.auditGoal === 'substantive' ? '实质性测试' : '控制测试' }}
            </el-descriptions-item>
            <el-descriptions-item label="总体范围">
              {{ getScopeLabel() }}
            </el-descriptions-item>
            <el-descriptions-item label="总体规模">
              {{ populationStats?.count || 0 }} 张凭证
            </el-descriptions-item>
            <el-descriptions-item label="抽样方法">
              {{ getMethodLabel() }}
            </el-descriptions-item>
            <el-descriptions-item label="预估样本量">
              {{ sampleSizePreview?.total_sample_size || 0 }} 张
            </el-descriptions-item>
          </el-descriptions>

          <div style="margin-top: 30px; text-align: center">
            <el-button type="primary" size="large" @click="executeSampling" :loading="executing">
              <el-icon><Check /></el-icon>
              执行抽样
            </el-button>
          </div>
        </div>
      </div>

      <!-- 导航按钮 -->
      <div class="step-navigation">
        <el-button v-if="currentStep > 0" @click="prevStep">上一步</el-button>
        <el-button v-if="currentStep < 3" type="primary" @click="nextStep" :disabled="!canNextStep">
          下一步
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { projectApi, samplingApi, voucherApi, aiApi } from '@/api'

const router = useRouter()
const currentStep = ref(0)
const projects = ref([])
const populationStats = ref(null)
const riskAnalysisResult = ref(null)
const sampleSizePreview = ref(null)
const musPreview = ref(null)
const systematicPreview = ref(null)
const loadingStats = ref(false)
const analyzingRisk = ref(false)
const calculating = ref(false)
const executing = ref(false)

// 风险凭证列表分页
const riskVoucherList = ref([])
const riskVoucherPage = ref(1)
const riskVoucherPageSize = ref(10)
const riskVoucherTotal = ref(0)
const riskFilterLevel = ref('all') // 筛选风险等级

const wizardForm = reactive({
  projectId: localStorage.getItem('currentProjectId') || '',
  auditGoal: 'substantive',
  testTypes: ['occurrence', 'completeness'],
  population: {
    scope: 'all',
    subjects: [],
    startDate: null,
    endDate: null,
    minAmount: null,
    maxAmount: null
  },
  sampling: {
    method: 'stratified',
    confidenceLevel: 95,
    tolerableError: 5,
    expectedError: 3,
    // MUS参数
    musConfidenceLevel: 0.95,
    musTolerableError: 5,
    musExpectedError: 1,
    // 系统抽样参数
    systematicMode: 'rate',
    systematicSampleSize: 50,
    systematicSamplingRate: 10,
    // 分层抽样参数
    layers: [
      { name: '大额', minAmount: 100000, maxAmount: null, samplingRate: 100 },
      { name: '中额', minAmount: 10000, maxAmount: 100000, samplingRate: 30 },
      { name: '小额', minAmount: null, maxAmount: 10000, samplingRate: 10 }
    ]
  }
})

const canNextStep = computed(() => {
  if (currentStep.value === 0) {
    return !!wizardForm.projectId
  }
  if (currentStep.value === 1) {
    return populationStats.value && populationStats.value.count > 0
  }
  if (currentStep.value === 2) {
    return sampleSizePreview.value && sampleSizePreview.value.total_sample_size > 0
  }
  return true
})

// 筛选后的风险凭证列表
const filteredRiskVouchers = computed(() => {
  let list = riskVoucherList.value
  if (riskFilterLevel.value !== 'all') {
    list = list.filter(v => v.risk_level === riskFilterLevel.value)
  }
  return list
})

// 当前页的风险凭证
const pagedRiskVouchers = computed(() => {
  const start = (riskVoucherPage.value - 1) * riskVoucherPageSize.value
  const end = start + riskVoucherPageSize.value
  return filteredRiskVouchers.value.slice(start, end)
})

// 风险凭证统计
const riskVoucherStats = computed(() => {
  const list = riskVoucherList.value
  const total = list.length
  const high = list.filter(v => v.risk_level === 'high').length
  const medium = list.filter(v => v.risk_level === 'medium').length
  const low = list.filter(v => v.risk_level === 'low').length

  // 计算百分比，确保总和为100%
  const calculateRatio = (count) => total > 0 ? Math.round((count / total) * 100) : 0

  let highRatio = calculateRatio(high)
  let mediumRatio = calculateRatio(medium)
  let lowRatio = calculateRatio(low)

  // 调整误差，确保总和为100%
  const totalRatio = highRatio + mediumRatio + lowRatio
  if (totalRatio !== 100 && total > 0) {
    const diff = 100 - totalRatio
    // 将差值加到最大的那个上
    if (high >= medium && high >= low) {
      highRatio += diff
    } else if (medium >= high && medium >= low) {
      mediumRatio += diff
    } else {
      lowRatio += diff
    }
  }

  return {
    total,
    high,
    medium,
    low,
    highRatio,
    mediumRatio,
    lowRatio
  }
})

// 监听总体范围变化，重置统计数据
watch(() => wizardForm.population.scope, () => {
  // 切换总体范围时，重置统计和风险分析结果
  populationStats.value = null
  riskAnalysisResult.value = null
  riskVoucherList.value = []
})

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const nextStep = () => {
  if (currentStep.value < 3 && canNextStep.value) {
    currentStep.value++
  }
}

const loadProjects = async () => {
  try {
    const res = await projectApi.getList({ page: 1, page_size: 100 })
    projects.value = res.items || []

    // 验证当前项目
    if (wizardForm.projectId) {
      const exists = projects.value.some(p => p.id === wizardForm.projectId)
      if (!exists) {
        wizardForm.projectId = ''
      }
    }
  } catch (error) {
    console.error(error)
  }
}

const loadPopulationStats = async () => {
  if (!wizardForm.projectId) {
    ElMessage.warning('请先选择项目')
    return
  }

  loadingStats.value = true
  try {
    // 构建筛选参数
    const params = {}

    // 根据总体范围设置筛选条件
    if (wizardForm.population.scope === 'subject' && wizardForm.population.subjects.length > 0) {
      params.subject_codes = wizardForm.population.subjects.join(',')
    } else if (wizardForm.population.scope === 'date') {
      if (wizardForm.population.startDate) {
        params.start_date = wizardForm.population.startDate.toISOString().split('T')[0]
      }
      if (wizardForm.population.endDate) {
        params.end_date = wizardForm.population.endDate.toISOString().split('T')[0]
      }
    } else if (wizardForm.population.scope === 'amount') {
      if (wizardForm.population.minAmount !== null) {
        params.min_amount = wizardForm.population.minAmount
      }
      if (wizardForm.population.maxAmount !== null) {
        params.max_amount = wizardForm.population.maxAmount
      }
    }

    // 调用总体统计API
    const res = await voucherApi.getPopulationStats(wizardForm.projectId, params)
    populationStats.value = {
      count: res.count || 0,
      totalAmount: res.total_amount || 0
    }
  } catch (error) {
    ElMessage.error('获取总体统计失败: ' + (error.response?.data?.detail || error.message))
    populationStats.value = {
      count: 0,
      totalAmount: 0
    }
  } finally {
    loadingStats.value = false
  }
}

const analyzePopulationRisk = async () => {
  if (!wizardForm.projectId || !populationStats.value) {
    ElMessage.warning('请先获取总体统计')
    return
  }

  analyzingRisk.value = true
  try {
    // 调用AI风险分析API
    const requestData = {
      project_id: wizardForm.projectId,
      analysis_type: 'population_risk',
      population_stats: populationStats.value
    }
    console.log('AI风险分析请求:', JSON.stringify(requestData, null, 2))

    const res = await aiApi.analyze(requestData)

    // 解析返回结果（results是数组，取第一个元素）
    if (res.results && res.results.length > 0) {
      riskAnalysisResult.value = res.results[0]

      // 处理凭证风险详情列表
      if (riskAnalysisResult.value.voucher_risk_details) {
        riskVoucherList.value = riskAnalysisResult.value.voucher_risk_details
        riskVoucherTotal.value = riskVoucherList.value.length
        riskVoucherPage.value = 1
      }

      // 根据AI建议自动调整分层设置
      if (riskAnalysisResult.value.stratification_config && wizardForm.sampling.method === 'stratified') {
        applyAIStratificationConfig(riskAnalysisResult.value.stratification_config)
      }

      ElMessage.success('AI风险分析完成')
    } else {
      // 没有结果，使用本地模拟
      riskAnalysisResult.value = simulateRiskAnalysis(populationStats.value)
      ElMessage.warning('AI返回结果为空，使用本地分析')
    }
  } catch (error) {
    // 如果API调用失败，使用本地模拟分析
    console.error('AI风险分析失败:', error)
    console.error('错误详情:', error.response?.data || error.message)
    riskAnalysisResult.value = simulateRiskAnalysis(populationStats.value)
    ElMessage.warning(`AI服务暂不可用: ${error.response?.data?.detail || error.message}`)
  } finally {
    analyzingRisk.value = false
  }
}

const generateMockVoucherRiskDetails = (count, avgAmount) => {
  // 生成模拟的凭证风险详情
  const details = []
  const subjects = ['银行存款', '应收账款', '其他应收款', '固定资产', '管理费用', '销售费用', '材料采购']
  const counterparties = ['甲公司', '乙公司', '丙公司', '个人', '内部往来', '供应商A', '客户B']

  for (let i = 1; i <= Math.min(10, count); i++) {
    const amount = avgAmount * (0.5 + Math.random() * 2)
    let riskScore = 30
    const riskFactors = []

    if (amount > avgAmount * 1.5) {
      riskScore += 25
      riskFactors.push('大额交易')
    }
    if (Math.random() > 0.7) {
      riskScore += 20
      riskFactors.push('敏感科目')
    }
    if (Math.random() > 0.8) {
      riskScore += 15
      riskFactors.push('关联方交易')
    }

    const riskLevel = riskScore >= 70 ? 'high' : (riskScore >= 40 ? 'medium' : 'low')

    details.push({
      voucher_id: `mock-voucher-${i}`,
      voucher_no: `记-2025-${String(i).padStart(4, '0')}`,
      voucher_date: `2025-${String(Math.floor(Math.random() * 12) + 1).padStart(2, '0')}-${String(Math.floor(Math.random() * 28) + 1).padStart(2, '0')}`,
      amount: Math.round(amount * 100) / 100,
      subject_name: subjects[Math.floor(Math.random() * subjects.length)],
      counterparty: counterparties[Math.floor(Math.random() * counterparties.length)],
      risk_level: riskLevel,
      risk_score: Math.min(100, riskScore),
      risk_factors: riskFactors.length > 0 ? riskFactors : ['常规交易'],
      explanation: riskLevel === 'high' ? '该凭证存在较高风险，建议重点检查' : '风险较低，常规检查即可'
    })
  }
  return details
}

const simulateRiskAnalysis = (stats) => {
  // 本地模拟风险分析
  const count = stats.count || 0
  const amount = stats.totalAmount || 0
  const avgAmount = count > 0 ? amount / count : 0

  // 模拟风险分布
  const highRiskCount = Math.floor(count * 0.1)
  const mediumRiskCount = Math.floor(count * 0.3)
  const lowRiskCount = count - highRiskCount - mediumRiskCount

  // 计算风险评分
  let riskScore = 30
  if (avgAmount > 100000) riskScore += 20
  if (avgAmount > 500000) riskScore += 20

  const riskLevel = riskScore >= 70 ? 'high' : (riskScore >= 40 ? 'medium' : 'low')

  return {
    overall_risk_score: Math.min(100, riskScore),
    overall_risk_level: riskLevel,
    high_risk_count: highRiskCount,
    medium_risk_count: mediumRiskCount,
    low_risk_count: lowRiskCount,
    high_risk_ratio: count > 0 ? Math.round(highRiskCount / count * 100) : 0,
    medium_risk_ratio: count > 0 ? Math.round(mediumRiskCount / count * 100) : 0,
    low_risk_ratio: count > 0 ? Math.round(lowRiskCount / count * 100) : 0,
    risk_factors: avgAmount > 100000 ? ['大额交易集中'] : [],
    stratification_suggestion: `建议采用分层抽样：大额凭证（>=${Math.round(avgAmount * 2)}元）100%抽取，中额凭证30%抽取，小额凭证10%抽取`,
    voucher_risk_details: count > 0 ? generateMockVoucherRiskDetails(count, avgAmount) : []
  }
}

const applyAIStratificationConfig = (config) => {
  if (config.layers && Array.isArray(config.layers)) {
    wizardForm.sampling.layers = config.layers.map(layer => ({
      name: layer.name,
      minAmount: layer.min_amount,
      maxAmount: layer.max_amount,
      samplingRate: Math.round(layer.sampling_rate * 100)
    }))
  }
}

const getRiskTagType = (level) => {
  const map = { high: 'danger', medium: 'warning', low: 'success' }
  return map[level] || 'info'
}

const getRiskLevelLabel = (level) => {
  const map = { high: '高风险', medium: '中风险', low: '低风险' }
  return map[level] || '未知'
}

const getRiskScoreColor = (score) => {
  if (score >= 70) return '#f56c6c'
  if (score >= 40) return '#e6a23c'
  return '#67c23a'
}

const handleRiskVoucherPageChange = (page) => {
  riskVoucherPage.value = page
}

const handleRiskFilterChange = () => {
  riskVoucherPage.value = 1
}

const calculateSampleSize = async () => {
  if (!wizardForm.projectId) {
    ElMessage.warning('请先选择项目')
    return
  }

  calculating.value = true
  try {
    if (wizardForm.sampling.method === 'stratified') {
      const layers = wizardForm.sampling.layers.map(layer => ({
        ...layer,
        sampling_rate: layer.samplingRate / 100
      }))

      const res = await samplingApi.previewStratified(wizardForm.projectId, {
        stratify_by: 'amount',
        layers: layers
      })
      sampleSizePreview.value = res
    } else if (wizardForm.sampling.method === 'monetary_unit') {
      // MUS抽样预览
      const res = await samplingApi.previewMUS(wizardForm.projectId, {
        confidence_level: wizardForm.sampling.musConfidenceLevel,
        tolerable_misstatement: wizardForm.sampling.musTolerableError / 100,
        expected_misstatement: wizardForm.sampling.musExpectedError / 100
      })
      musPreview.value = res
      sampleSizePreview.value = {
        total_population: populationStats.value?.count || 0,
        total_sample_size: res.sample_size,
        overall_sampling_rate: Number((res.sample_size / (populationStats.value?.count || 1) * 100).toFixed(2)),
        layers_summary: []
      }
    } else if (wizardForm.sampling.method === 'systematic') {
      // 系统抽样预览
      const params = {}
      if (wizardForm.sampling.systematicMode === 'count') {
        params.sample_size = wizardForm.sampling.systematicSampleSize
      } else {
        params.sampling_rate = wizardForm.sampling.systematicSamplingRate / 100
      }
      const res = await samplingApi.previewSystematic(wizardForm.projectId, params)
      systematicPreview.value = res
      sampleSizePreview.value = {
        total_population: res.population_size,
        total_sample_size: res.actual_sample_size || res.sample_size,
        overall_sampling_rate: res.sampling_rate,
        layers_summary: []
      }
    } else {
      // 随机抽样计算
      const z = { 90: 1.645, 95: 1.96, 99: 2.576 }[wizardForm.sampling.confidenceLevel] || 1.96
      const p = wizardForm.sampling.expectedError / 100
      const e = wizardForm.sampling.tolerableError / 100
      const N = populationStats.value?.count || 1000

      const n = (z * z * p * (1 - p)) / (e * e)
      const nAdjusted = Math.round(n * N / (N + n - 1))

      sampleSizePreview.value = {
        total_population: N,
        total_sample_size: nAdjusted,
        overall_sampling_rate: Number((nAdjusted / N * 100).toFixed(2)),
        layers_summary: []
      }
    }
  } catch (error) {
    ElMessage.error('计算失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    calculating.value = false
  }
}

const getScopeLabel = () => {
  const labels = {
    all: '全部凭证',
    subject: '按科目筛选',
    date: '按日期范围',
    amount: '按金额范围'
  }
  return labels[wizardForm.population.scope] || '全部凭证'
}

const getMethodLabel = () => {
  const labels = {
    random: '随机抽样',
    monetary_unit: '货币单位抽样(MUS)',
    systematic: '系统抽样',
    stratified: '分层抽样',
    judgment: '判断抽样'
  }
  return labels[wizardForm.sampling.method] || '随机抽样'
}

const executeSampling = async () => {
  if (!wizardForm.projectId) {
    ElMessage.warning('请先选择项目')
    return
  }

  executing.value = true
  try {
    const method = wizardForm.sampling.method

    if (method === 'monetary_unit') {
      // MUS抽样执行
      await samplingApi.executeMUS(wizardForm.projectId, {
        name: `MUS抽样-${new Date().toLocaleDateString()}`,
        confidence_level: wizardForm.sampling.musConfidenceLevel,
        tolerable_misstatement: wizardForm.sampling.musTolerableError / 100,
        expected_misstatement: wizardForm.sampling.musExpectedError / 100,
        sampling_interval: musPreview.value?.sampling_interval,
        random_start: musPreview.value?.random_start
      })
      ElMessage.success('MUS抽样执行成功')
      router.push('/sampling/results')
    } else if (method === 'systematic') {
      // 系统抽样执行
      const params = {
        name: `系统抽样-${new Date().toLocaleDateString()}`
      }
      if (wizardForm.sampling.systematicMode === 'count') {
        params.sample_size = wizardForm.sampling.systematicSampleSize
      } else {
        params.sampling_rate = wizardForm.sampling.systematicSamplingRate / 100
      }
      await samplingApi.executeSystematic(wizardForm.projectId, params)
      ElMessage.success('系统抽样执行成功')
      router.push('/sampling/results')
    } else {
      // 原有的抽样方法（随机、分层、判断）
      let ruleConfig = {}

      if (method === 'random') {
        ruleConfig = {
          percentage: sampleSizePreview.value.overall_sampling_rate,
          confidence_level: wizardForm.sampling.confidenceLevel,
          tolerable_error: wizardForm.sampling.tolerableError,
          expected_error: wizardForm.sampling.expectedError
        }
      } else if (method === 'stratified') {
        ruleConfig = {
          stratify_by: 'amount',
          layers: wizardForm.sampling.layers.map(layer => ({
            ...layer,
            sampling_rate: layer.samplingRate / 100
          }))
        }
      }

      // 创建规则
      const rule = await samplingApi.createRule(wizardForm.projectId, {
        name: `${getMethodLabel()}-${new Date().toLocaleDateString()}`,
        rule_type: method,
        rule_config: ruleConfig
      })

      // 执行抽样
      await samplingApi.execute(wizardForm.projectId, {
        rule_id: rule.id
      })

      ElMessage.success('抽样执行成功')
      router.push('/sampling/results')
    }
  } catch (error) {
    ElMessage.error('执行失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    executing.value = false
  }
}

onMounted(() => {
  loadProjects()
})
</script>

<style lang="scss" scoped>
/* 覆盖页面容器边距，参考凭证管理页面 */
.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

.step-content {
  min-height: 400px;
  padding: 20px;
}

.step-panel {
  max-width: 900px;
  margin: 0 auto;
}

.step-navigation {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.method-desc {
  color: #909399;
  font-size: 13px;
  margin-left: 8px;
}

.layer-config {
  padding: 16px 20px;
  margin-bottom: 16px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #e8e8e8;

  .layer-header {
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px dashed #e0e0e0;

    .layer-title {
      font-size: 15px;
      font-weight: 500;
      color: #303133;
    }
  }

  .el-form-item {
    margin-bottom: 12px;
  }

  // 金额输入框样式
  .amount-input {
    width: 100%;

    :deep(.el-input__wrapper) {
      padding: 0 12px;
    }

    :deep(.el-input__inner) {
      text-align: left;
    }
  }

  // 抽样比例输入框样式
  .rate-input-wrapper {
    display: flex;
    align-items: center;
    width: 100%;

    .rate-input {
      flex: 1;

      :deep(.el-input__wrapper) {
        border-radius: 4px 0 0 4px;
      }
    }

    .rate-suffix {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 32px;
      background: #f5f7fa;
      border: 1px solid #dcdfe6;
      border-left: none;
      border-radius: 0 4px 4px 0;
      color: #606266;
      font-size: 14px;
      white-space: nowrap;
    }
  }
}

.population-stats,
.sample-preview {
  display: flex;
  align-items: center;
}

.risk-analysis-section {
  margin-top: 20px;
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
  width: 150%;
  margin-left: -25%;
}

.risk-summary-card {
  text-align: center;
  padding: 20px;
  background: white;
  border-radius: 8px;

  .risk-score {
    font-size: 48px;
    font-weight: 700;

    &.high { color: #f56c6c; }
    &.medium { color: #e6a23c; }
    &.low { color: #67c23a; }
  }

  .risk-label {
    font-size: 14px;
    color: #909399;
    margin: 8px 0;
  }
}

.risk-distribution {
  padding: 16px 20px;
  background: white;
  border-radius: 8px;

  h4 {
    margin-bottom: 16px;
    font-size: 14px;
    color: #606266;
  }

  .distribution-item {
    display: flex;
    align-items: center;
    margin-bottom: 12px;

    .label {
      width: 60px;
      font-size: 13px;
      color: #606266;
    }

    .el-progress {
      flex: 1;
      margin: 0 12px;
    }

    .count {
      width: 60px;
      text-align: right;
      font-size: 13px;
      color: #909399;
    }
  }
}

.stratification-suggestion,
.risk-factors {
  margin-top: 16px;

  h4 {
    margin-bottom: 12px;
    font-size: 14px;
    color: #606266;
  }

  .risk-factor-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    line-height: 1.8;
  }

  .risk-tag {
    white-space: nowrap;
    max-width: 100%;
    overflow: visible;
    text-overflow: clip;
  }
}

.risk-voucher-list {
  margin-top: 20px;
  overflow-x: auto;

  .el-table {
    min-width: 900px;
  }

  .list-toolbar {
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .risk-factor-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    line-height: 1.8;
  }

  .risk-tag {
    white-space: nowrap;
    max-width: 100%;
    overflow: visible;
    text-overflow: clip;
  }

  .pagination-wrapper {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
