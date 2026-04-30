<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h2 class="page-title">执行抽样</h2>
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
    </div>

    <!-- 抽样方式选择 -->
    <el-tabs v-model="activeTab" type="border-card" class="sampling-tabs">
      <!-- 规则抽样 -->
      <el-tab-pane name="rule">
        <template #label>
          <span class="tab-label">
            <el-icon><Setting /></el-icon>
            规则抽样
          </span>
        </template>

        <div class="tab-content">
          <el-alert type="info" :closable="false" style="margin-bottom: 20px">
            <template #title>
              <strong>规则抽样</strong>
            </template>
            根据预设条件（金额、科目、日期等）自动筛选凭证，适合有明确抽样标准的审计场景。
          </el-alert>

          <el-row :gutter="20">
            <!-- 规则配置 -->
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>{{ editingRule ? '编辑抽样规则' : '新建抽样规则' }}</span>
                    <el-button v-if="editingRule" type="primary" link size="small" @click="cancelEdit">
                      新建规则
                    </el-button>
                  </div>
                </template>
                <el-form :model="ruleForm" label-width="100px" size="default">
                  <el-form-item label="规则名称">
                    <el-input v-model="ruleForm.name" placeholder="请输入规则名称" style="width: 280px" />
                  </el-form-item>
                  <el-form-item label="规则类型">
                    <el-select v-model="ruleForm.rule_type" @change="onRuleTypeChange" style="width: 200px">
                      <el-option label="随机抽样" value="random" />
                      <el-option label="金额抽样" value="amount" />
                      <el-option label="科目抽样" value="subject" />
                      <el-option label="日期范围" value="date" />
                      <el-option label="分层抽样" value="stratified" />
                    </el-select>
                  </el-form-item>

                  <!-- 随机抽样配置 -->
                  <template v-if="ruleForm.rule_type === 'random'">
                    <el-form-item label="抽样比例" class="slider-form-item">
                      <div class="rate-slider">
                        <el-slider v-model="ruleForm.rule_config.percentage" :min="5" :max="100" :step="5" :marks="rateMarks" />
                      </div>
                    </el-form-item>
                    <el-form-item label="样本数量">
                      <el-input-number v-model="ruleForm.rule_config.sample_size" :min="0" :step="5" placeholder="按比例计算" style="width: 150px" />
                      <span class="input-suffix">张（留空按比例）</span>
                    </el-form-item>
                  </template>

                  <!-- 金额抽样配置 -->
                  <template v-if="ruleForm.rule_type === 'amount'">
                    <el-form-item label="最小金额">
                      <el-input-number v-model="ruleForm.rule_config.min_amount" :min="0" :controls="false" placeholder="不限" class="amount-input" />
                      <span class="input-suffix">元</span>
                    </el-form-item>
                    <el-form-item label="最大金额">
                      <el-input-number v-model="ruleForm.rule_config.max_amount" :min="0" :controls="false" placeholder="不限" class="amount-input" />
                      <span class="input-suffix">元</span>
                    </el-form-item>
                    <el-form-item label="抽样比例" class="slider-form-item">
                      <div class="rate-slider">
                        <el-slider v-model="ruleForm.rule_config.percentage" :min="5" :max="100" :step="5" :marks="rateMarks" />
                      </div>
                    </el-form-item>
                  </template>

                  <!-- 科目抽样配置 -->
                  <template v-if="ruleForm.rule_type === 'subject'">
                    <el-form-item label="科目代码">
                      <el-select v-model="ruleForm.rule_config.subject_codes" multiple filterable placeholder="选择科目" style="width: 280px">
                        <el-option v-for="subject in subjectOptions" :key="subject.code" :label="subject.name" :value="subject.code" />
                      </el-select>
                    </el-form-item>
                  </template>

                  <!-- 日期抽样配置 -->
                  <template v-if="ruleForm.rule_type === 'date'">
                    <el-form-item label="日期范围">
                      <el-date-picker v-model="ruleForm.rule_config.start_date" type="date" placeholder="开始" style="width: 130px" />
                      <span style="margin: 0 8px">至</span>
                      <el-date-picker v-model="ruleForm.rule_config.end_date" type="date" placeholder="结束" style="width: 130px" />
                    </el-form-item>
                  </template>

                  <!-- 分层抽样配置 -->
                  <template v-if="ruleForm.rule_type === 'stratified'">
                    <el-form-item label="分层依据">
                      <el-select v-model="ruleForm.rule_config.stratify_by" style="width: 200px">
                        <el-option label="按金额分层" value="amount" />
                      </el-select>
                    </el-form-item>

                    <el-divider content-position="left">分层设置</el-divider>

                    <div v-for="(layer, index) in ruleForm.rule_config.layers" :key="index" class="layer-config">
                      <div class="layer-header">
                        <span class="layer-name">第{{ index + 1 }}层：{{ layer.name }}</span>
                        <el-button v-if="ruleForm.rule_config.layers.length > 1" type="danger" link size="small" @click="removeLayer(index)">删除</el-button>
                      </div>
                      <el-row :gutter="10">
                        <el-col :span="8">
                          <el-form-item label="名称" label-width="50px">
                            <el-input v-model="layer.name" placeholder="名称" />
                          </el-form-item>
                        </el-col>
                        <el-col :span="8">
                          <el-form-item label="最小" label-width="50px">
                            <el-input-number v-model="layer.min_amount" :min="0" :controls="false" placeholder="不限" class="layer-input" />
                          </el-form-item>
                        </el-col>
                        <el-col :span="8">
                          <el-form-item label="最大" label-width="50px">
                            <el-input-number v-model="layer.max_amount" :min="0" :controls="false" placeholder="不限" class="layer-input" />
                          </el-form-item>
                        </el-col>
                      </el-row>
                      <el-form-item label="抽样比例" label-width="80px" class="slider-form-item">
                        <div class="rate-slider" style="padding: 0">
                          <el-slider v-model="layer.sampling_rate" :min="0" :max="100" :step="5" :marks="rateMarks" />
                        </div>
                      </el-form-item>
                    </div>

                    <el-button type="primary" link @click="addLayer">
                      <el-icon><Plus /></el-icon> 添加分层
                    </el-button>

                    <div v-if="previewResult" class="preview-result">
                      <el-divider />
                      <el-descriptions title="预览结果" :column="3" border size="small">
                        <el-descriptions-item label="总体">{{ previewResult.total_population }} 张</el-descriptions-item>
                        <el-descriptions-item label="预估样本">{{ previewResult.total_sample_size }} 张</el-descriptions-item>
                        <el-descriptions-item label="抽样率">{{ previewResult.overall_sampling_rate }}%</el-descriptions-item>
                      </el-descriptions>
                      <el-table :data="previewResult.layers_summary" size="small" style="margin-top: 10px">
                        <el-table-column prop="name" label="层名称" width="100" />
                        <el-table-column prop="population_count" label="总体数量" width="100" />
                        <el-table-column prop="sample_count" label="样本数量" width="100" />
                        <el-table-column label="抽样比例">
                          <template #default="{ row }">
                            {{ (row.sampling_rate * 100).toFixed(0) }}%
                          </template>
                        </el-table-column>
                      </el-table>
                    </div>
                  </template>

                  <el-form-item style="margin-top: 20px">
                    <el-button v-if="ruleForm.rule_type === 'stratified'" @click="previewStratified" :loading="previewing" style="margin-right: 10px">
                      预览样本量
                    </el-button>
                    <template v-if="editingRule">
                      <el-button type="primary" @click="updateRule" :loading="executing">
                        更新规则
                      </el-button>
                      <el-button @click="cancelEdit">取消</el-button>
                    </template>
                    <el-button v-else type="primary" @click="executeSampling" :loading="executing">
                      执行抽样
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>

            <!-- 已保存规则 -->
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span>已保存规则</span>
                </template>
                <el-table :data="rules" style="width: 100%" size="small">
                  <el-table-column prop="name" label="规则名称" min-width="120" />
                  <el-table-column prop="rule_type" label="类型" width="120">
                    <template #default="{ row }">
                      <el-tag size="small" style="min-width: 80px; justify-content: center;">{{ getRuleTypeLabel(row.rule_type) }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="created_at" label="创建时间" width="150">
                    <template #default="{ row }">
                      {{ formatDate(row.created_at) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="160">
                    <template #default="{ row }">
                      <el-button type="primary" link size="small" @click="editRule(row)">编辑</el-button>
                      <el-button type="primary" link size="small" @click="useRule(row)">使用</el-button>
                      <el-button type="danger" link size="small" @click="deleteRule(row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-empty v-if="rules.length === 0" description="暂无已保存规则" :image-size="60" />
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>

      <!-- AI智能抽样 -->
      <el-tab-pane name="ai">
        <template #label>
          <span class="tab-label">
            <el-icon><MagicStick /></el-icon>
            AI智能抽样
          </span>
        </template>

        <div class="tab-content">
          <el-alert type="success" :closable="false" style="margin-bottom: 20px">
            <template #title>
              <strong>AI智能抽样</strong>
            </template>
            AI自动分析凭证风险等级，智能推荐高风险凭证优先抽样，适合需要快速定位风险点的审计场景。
          </el-alert>

          <el-row :gutter="20">
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <div style="display: flex; align-items: center">
                    <el-icon color="#409eff" style="margin-right: 5px"><MagicStick /></el-icon>
                    <span>AI智能抽样配置</span>
                  </div>
                </template>

                <el-form :model="aiForm" label-width="100px">
                  <el-form-item label="样本数量">
                    <el-input-number v-model="aiForm.sample_size" :min="10" :max="500" :step="5" style="width: 150px" />
                    <span class="input-suffix">张（建议10-50）</span>
                  </el-form-item>
                  <el-form-item label="重点关注">
                    <el-checkbox-group v-model="aiForm.focus_areas">
                      <el-checkbox label="大额交易">大额交易</el-checkbox>
                      <el-checkbox label="异常日期">异常日期</el-checkbox>
                      <el-checkbox label="关联方">关联方</el-checkbox>
                      <el-checkbox label="跨期调整">跨期调整</el-checkbox>
                    </el-checkbox-group>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="aiSampling" :loading="aiExecuting" size="large">
                      <el-icon><MagicStick /></el-icon>
                      开始AI分析
                    </el-button>
                  </el-form-item>
                </el-form>

                <el-divider />

                <div class="ai-features">
                  <h4>AI分析内容</h4>
                  <ul>
                    <li>凭证金额异常检测</li>
                    <li>科目与摘要匹配度分析</li>
                    <li>交易对手风险识别</li>
                    <li>日期异常检测（非工作日等）</li>
                    <li>风险等级自动评估</li>
                  </ul>
                </div>
              </el-card>
            </el-col>

            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span>抽样方式对比</span>
                </template>

                <el-table :data="comparisonData" style="width: 100%" size="small">
                  <el-table-column prop="feature" label="对比项" width="120" />
                  <el-table-column prop="rule" label="规则抽样" />
                  <el-table-column prop="ai" label="AI智能抽样" />
                </el-table>

                <div style="margin-top: 20px">
                  <h4>选择建议</h4>
                  <el-descriptions :column="1" border size="small">
                    <el-descriptions-item label="规则抽样适合">
                      有明确抽样标准、需要按特定条件筛选、审计程序规范化的场景
                    </el-descriptions-item>
                    <el-descriptions-item label="AI抽样适合">
                      需要快速定位风险、凭证量大需筛选、初次审计需全面了解风险的场景
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Setting, MagicStick } from '@element-plus/icons-vue'
import { samplingApi, aiApi, projectApi } from '@/api'
import dayjs from 'dayjs'

const router = useRouter()
const activeTab = ref('rule')
const executing = ref(false)
const aiExecuting = ref(false)
const previewing = ref(false)
const previewResult = ref(null)

const projectId = ref(localStorage.getItem('currentProjectId') || '')
const projects = ref([])

const ruleForm = reactive({
  name: '',
  rule_type: 'random',
  rule_config: {
    percentage: 10,
    sample_size: null,
    min_amount: null,
    max_amount: null,
    subject_codes: [],
    start_date: null,
    end_date: null,
    stratify_by: 'amount',
    layers: [
      { name: '大额', min_amount: 100000, max_amount: null, sampling_rate: 100 },
      { name: '中额', min_amount: 10000, max_amount: 100000, sampling_rate: 30 },
      { name: '小额', min_amount: null, max_amount: 10000, sampling_rate: 10 }
    ]
  }
})

const aiForm = reactive({
  sample_size: 30,
  focus_areas: []
})

const rules = ref([])
const subjectOptions = ref([])

// 滑动条刻度
const rateMarks = {
  5: '5%',
  10: '10%',
  25: '25%',
  50: '50%',
  75: '75%',
  100: '100%'
}

// 对比数据
const comparisonData = [
  { feature: '筛选方式', rule: '预设条件筛选', ai: 'AI风险评估' },
  { feature: '操作复杂度', rule: '需配置参数', ai: '一键分析' },
  { feature: '适用场景', rule: '标准化抽样', ai: '风险导向抽样' },
  { feature: '分析速度', rule: '快速', ai: '较慢（需AI分析）' },
  { feature: '结果说明', rule: '按条件返回', ai: '包含风险原因' }
]

const formatDate = (date) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'

const getRuleTypeLabel = (type) => {
  const labels = { random: '随机', amount: '金额', subject: '科目', date: '日期', stratified: '分层', risk_stratified: '分层' }
  return labels[type] || type
}

const onRuleTypeChange = () => {
  ruleForm.rule_config = {
    percentage: 10,
    sample_size: null,
    min_amount: null,
    max_amount: null,
    subject_codes: [],
    start_date: null,
    end_date: null,
    stratify_by: 'amount',
    layers: [
      { name: '大额', min_amount: 100000, max_amount: null, sampling_rate: 100 },
      { name: '中额', min_amount: 10000, max_amount: 100000, sampling_rate: 30 },
      { name: '小额', min_amount: null, max_amount: 10000, sampling_rate: 10 }
    ]
  }
  previewResult.value = null
}

const addLayer = () => {
  ruleForm.rule_config.layers.push({
    name: `第${ruleForm.rule_config.layers.length + 1}层`,
    min_amount: null,
    max_amount: null,
    sampling_rate: 10
  })
}

const removeLayer = (index) => {
  ruleForm.rule_config.layers.splice(index, 1)
}

const previewStratified = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  previewing.value = true
  try {
    const layers = ruleForm.rule_config.layers.map(layer => ({
      ...layer,
      sampling_rate: layer.sampling_rate / 100
    }))

    const res = await samplingApi.previewStratified(projectId.value, {
      stratify_by: ruleForm.rule_config.stratify_by,
      layers: layers
    })
    previewResult.value = res
  } catch (error) {
    ElMessage.error('预览失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    previewing.value = false
  }
}

const loadRules = async () => {
  if (!projectId.value) return
  try {
    rules.value = await samplingApi.getRules(projectId.value)
  } catch (error) {
    console.error(error)
  }
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

const onProjectChange = (val) => {
  localStorage.setItem('currentProjectId', val)
  loadRules()
  previewResult.value = null
}

const executeSampling = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  if (!ruleForm.name) {
    ElMessage.warning('请输入规则名称')
    return
  }

  executing.value = true
  try {
    const rule = await samplingApi.createRule(projectId.value, {
      name: ruleForm.name,
      rule_type: ruleForm.rule_type,
      rule_config: ruleForm.rule_config
    })

    await samplingApi.execute(projectId.value, {
      rule_id: rule.id,
      sample_size: ruleForm.rule_config.sample_size
    })

    ElMessage.success('抽样执行成功')
    router.push('/sampling/results')
  } catch (error) {
    console.error(error)
  } finally {
    executing.value = false
  }
}

const useRule = async (rule) => {
  executing.value = true
  try {
    await samplingApi.execute(projectId.value, { rule_id: rule.id })
    ElMessage.success('抽样执行成功')
    router.push('/sampling/results')
  } catch (error) {
    console.error(error)
  } finally {
    executing.value = false
  }
}

const deleteRule = async (rule) => {
  try {
    await ElMessageBox.confirm('确定要删除该规则吗？', '提示', { type: 'warning' })
    await samplingApi.deleteRule(projectId.value, rule.id)
    ElMessage.success('规则已删除')
    loadRules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

// 编辑规则
const editingRule = ref(null)
const editRule = (rule) => {
  editingRule.value = rule
  // 填充表单
  ruleForm.name = rule.name
  ruleForm.rule_type = rule.rule_type
  ruleForm.rule_config = { ...rule.rule_config }
  // 如果是分层抽样，处理layers
  if (rule.rule_type === 'stratified' && rule.rule_config.layers) {
    ruleForm.rule_config.layers = rule.rule_config.layers.map(layer => ({
      ...layer,
      sampling_rate: layer.sampling_rate * 100 // 转换为百分比
    }))
  }
}

// 更新规则
const updateRule = async () => {
  if (!ruleForm.name) {
    ElMessage.warning('请输入规则名称')
    return
  }

  executing.value = true
  try {
    const config = { ...ruleForm.rule_config }
    // 如果是分层抽样，转换抽样比例为小数
    if (ruleForm.rule_type === 'stratified' && config.layers) {
      config.layers = config.layers.map(layer => ({
        ...layer,
        sampling_rate: layer.sampling_rate / 100
      }))
    }

    await samplingApi.updateRule(projectId.value, editingRule.value.id, {
      name: ruleForm.name,
      rule_type: ruleForm.rule_type,
      rule_config: config
    })

    ElMessage.success('规则更新成功')
    editingRule.value = null
    // 重置表单
    ruleForm.name = ''
    onRuleTypeChange()
    loadRules()
  } catch (error) {
    ElMessage.error('更新失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    executing.value = false
  }
}

// 取消编辑
const cancelEdit = () => {
  editingRule.value = null
  ruleForm.name = ''
  onRuleTypeChange()
}

const aiSampling = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  aiExecuting.value = true
  try {
    ElMessage.info('AI正在分析凭证，请耐心等待...')
    await aiApi.intelligentSample({
      project_id: projectId.value,
      sample_size: aiForm.sample_size,
      focus_areas: aiForm.focus_areas.length > 0 ? aiForm.focus_areas : null
    })
    ElMessage.success('AI智能抽样完成')
    router.push('/sampling/results')
  } catch (error) {
    console.error(error)
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      ElMessage.error('AI分析超时，请减少样本数量或稍后重试')
    } else if (error.response?.status === 500) {
      ElMessage.error('AI服务异常，请检查模型配置')
    } else if (!error.response) {
      ElMessage.error('网络连接失败，请检查服务是否正常运行')
    }
  } finally {
    aiExecuting.value = false
  }
}

onMounted(async () => {
  await loadProjects()
  loadRules()
})
</script>

<style lang="scss" scoped>
/* 覆盖页面容器边距，参考凭证管理页面 */
.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.sampling-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 15px;
}

.tab-content {
  padding: 20px;
}

.layer-config {
  padding: 12px;
  margin-bottom: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e9ecef;

  .layer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;

    .layer-name {
      font-weight: 500;
      color: #303133;
    }
  }
}

.preview-result {
  margin-top: 16px;
}

.ai-features {
  h4 {
    margin: 0 0 10px 0;
    color: #303133;
  }

  ul {
    margin: 0;
    padding-left: 20px;

    li {
      margin-bottom: 6px;
      color: #606266;
      font-size: 13px;
    }
  }
}

.rate-slider {
  width: 100%;
  padding: 0 10px;
}

.slider-form-item {
  margin-bottom: 28px;
}

.amount-input {
  width: 150px;
}

.input-suffix {
  margin-left: 8px;
  font-size: 13px;
  color: #909399;
}

.layer-input {
  width: 100%;
}
</style>