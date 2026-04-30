<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">样本测试</h2>
      <div class="header-actions">
        <el-select v-model="selectedRecordId" placeholder="选择抽样记录" style="width: 300px; margin-right: 16px" @change="loadSamples">
          <el-option
            v-for="record in samplingRecords"
            :key="record.id"
            :label="`${record.rule_name} (${record.sample_size}张)`"
            :value="record.id"
          />
        </el-select>
        <el-button type="primary" @click="executeAiTest" :loading="testing" :disabled="!selectedRecordId">
          <el-icon><Cpu /></el-icon>
          执行AI测试
        </el-button>
        <el-button @click="batchTest" :disabled="selectedSamples.length === 0">
          批量测试选中项
        </el-button>
      </div>
    </div>

    <!-- 测试进度 -->
    <el-card class="progress-card" v-if="selectedRecordId">
      <div class="progress-stats">
        <div class="stat-item">
          <span class="stat-value">{{ testStats.total }}</span>
          <span class="stat-label">样本总数</span>
        </div>
        <div class="stat-item">
          <span class="stat-value pending">{{ testStats.pending }}</span>
          <span class="stat-label">待测试</span>
        </div>
        <div class="stat-item">
          <span class="stat-value success">{{ testStats.completed }}</span>
          <span class="stat-label">正常</span>
        </div>
        <div class="stat-item">
          <span class="stat-value danger">{{ testStats.suspectedError }}</span>
          <span class="stat-label">疑似错报</span>
        </div>
        <div class="stat-item">
          <span class="stat-value warning">{{ testStats.needsReview }}</span>
          <span class="stat-label">需复核</span>
        </div>
      </div>
      <el-progress
        :percentage="testProgress"
        :status="testProgress === 100 ? 'success' : ''"
      />
    </el-card>

    <!-- 样本列表 -->
    <el-card v-if="selectedRecordId">
      <el-table
        :data="samples"
        @selection-change="handleSelectionChange"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="voucher_no" label="凭证号" width="140" fixed />
        <el-table-column prop="amount" label="金额" width="130" align="right">
          <template #default="{ row }">
            <span :class="{ 'large-amount': row.amount > 100000 }">
              {{ formatAmount(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="subject_name" label="科目" width="120" />
        <el-table-column prop="description" label="摘要" min-width="150" show-overflow-tooltip />
        <el-table-column prop="test_status" label="测试状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.test_status)" size="small">
              {{ getStatusLabel(row.test_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ai_test_result" label="AI判定" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.ai_test_result" :type="getAiResultTag(row.ai_test_result)" size="small">
              {{ getAiResultLabel(row.ai_test_result) }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="risk_score" label="风险分数" width="120">
          <template #default="{ row }">
            <el-progress
              v-if="row.risk_score"
              :percentage="row.risk_score"
              :color="getRiskColor(row.risk_score)"
              :stroke-width="6"
            />
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="错报金额" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.misstatement_amount" class="error-amount">
              {{ formatAmount(row.misstatement_amount) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link size="small" @click="viewDetail(row)">详情</el-button>
            <el-button link size="small" @click="openMisstatementDialog(row)">记录错报</el-button>
            <el-button
              v-if="row.ai_test_result && row.ai_test_result !== 'valid'"
              link
              size="small"
              type="warning"
              @click="openOverrideDialog(row)"
            >
              修正
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[50, 100, 200]"
          :total="totalSamples"
          layout="total, sizes, prev, pager, next"
          @size-change="loadSamples"
          @current-change="loadSamples"
        />
      </div>
    </el-card>

    <!-- 空状态 -->
    <el-empty v-if="!selectedRecordId" description="请先选择抽样记录" />

    <!-- 错报记录对话框 -->
    <el-dialog v-model="misstatementDialogVisible" title="记录错报" width="650px">
      <el-form :model="misstatementForm" label-width="100px">
        <el-form-item label="凭证号">
          <el-input :value="currentSample?.voucher_no" disabled />
        </el-form-item>
        <el-form-item label="错报类型" required>
          <el-select v-model="misstatementForm.misstatement_type" style="width: 100%">
            <el-option label="金额错误" value="amount_error" />
            <el-option label="缺少支持性单据" value="missing_doc" />
            <el-option label="虚构交易" value="fictitious" />
            <el-option label="分类错误" value="classification" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="原始金额">
          <el-input-number v-model="misstatementForm.original_amount" :controls="false" style="width: 200px" />
        </el-form-item>
        <el-form-item label="正确金额">
          <el-input-number v-model="misstatementForm.correct_amount" :controls="false" style="width: 200px" />
        </el-form-item>
        <el-form-item label="错报金额">
          <el-input-number v-model="misstatementForm.misstatement_amount" :controls="false" style="width: 200px" />
        </el-form-item>
        <el-form-item label="错报描述" required>
          <el-input v-model="misstatementForm.description" type="textarea" :rows="3" placeholder="请描述错报情况" />
        </el-form-item>
        <el-form-item label="证据文件">
          <el-upload
            ref="evidenceUploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleEvidenceChange"
            :on-remove="handleEvidenceRemove"
            accept="image/*,.pdf"
          >
            <template #trigger>
              <el-button type="primary" plain>选择文件</el-button>
            </template>
            <template #tip>
              <div class="el-upload__tip">支持上传截图、PDF等证据文件</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="misstatementDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitMisstatement" :loading="submitting">确认记录</el-button>
      </template>
    </el-dialog>

    <!-- 人工修正对话框 -->
    <el-dialog v-model="overrideDialogVisible" title="修正AI判定" width="500px">
      <el-form :model="overrideForm" label-width="100px">
        <el-form-item label="凭证号">
          <el-input :value="currentSample?.voucher_no" disabled />
        </el-form-item>
        <el-form-item label="当前判定">
          <el-tag :type="getAiResultTag(currentSample?.ai_test_result)">
            {{ getAiResultLabel(currentSample?.ai_test_result) }}
          </el-tag>
        </el-form-item>
        <el-form-item label="修正为" required>
          <el-radio-group v-model="overrideForm.override_conclusion">
            <el-radio value="valid">真实合理</el-radio>
            <el-radio value="abnormal">存在异常</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="修正原因" required>
          <el-input v-model="overrideForm.override_reason" type="textarea" :rows="3" placeholder="请说明修正原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="overrideDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitOverride" :loading="submitting">确认修正</el-button>
      </template>
    </el-dialog>

    <!-- AI分析详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="AI分析详情" width="900px" top="5vh">
      <div v-if="aiTestDetail" class="ai-detail-content">
        <!-- 判定结论 -->
        <div class="detail-section">
          <h4>判定结论</h4>
          <div class="conclusion-box" :class="aiTestDetail.ai_conclusion">
            <el-icon :size="32">
              <CircleCheck v-if="aiTestDetail.ai_conclusion === 'valid'" />
              <Warning v-else-if="aiTestDetail.ai_conclusion === 'abnormal'" />
              <QuestionFilled v-else />
            </el-icon>
            <div class="conclusion-text">
              <span class="conclusion-label">{{ getAiResultLabel(aiTestDetail.ai_conclusion) }}</span>
              <span class="confidence">置信度: {{ (aiTestDetail.confidence * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>

        <!-- 风险分析 -->
        <div class="detail-section">
          <h4>风险分析</h4>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="risk-gauge">
                <el-progress
                  type="dashboard"
                  :percentage="aiTestDetail.risk_score || 0"
                  :color="getRiskColor(aiTestDetail.risk_score || 0)"
                >
                  <template #default="{ percentage }">
                    <span class="percentage-value">{{ percentage }}</span>
                    <span class="percentage-label">风险分数</span>
                  </template>
                </el-progress>
              </div>
            </el-col>
            <el-col :span="16">
              <div class="risk-factors">
                <div class="factor-title">风险因素</div>
                <el-tag
                  v-for="factor in (aiTestDetail.risk_factors || [])"
                  :key="factor"
                  type="warning"
                  style="margin-right: 8px; margin-bottom: 8px"
                >
                  {{ factor }}
                </el-tag>
                <el-empty v-if="!aiTestDetail.risk_factors?.length" description="无风险因素" :image-size="60" />
              </div>
              <div class="risk-level">
                <span>风险等级：</span>
                <el-tag :type="aiTestDetail.risk_level === 'high' ? 'danger' : (aiTestDetail.risk_level === 'medium' ? 'warning' : 'success')">
                  {{ aiTestDetail.risk_level === 'high' ? '高' : (aiTestDetail.risk_level === 'medium' ? '中' : '低') }}
                </el-tag>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 证据链分析 -->
        <div class="detail-section" v-if="aiTestDetail.evidence_analysis">
          <h4>证据链分析</h4>
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="evidence-item" :class="{ active: aiTestDetail.evidence_analysis.has_invoice }">
                <el-icon><Document /></el-icon>
                <span>发票</span>
                <el-tag v-if="aiTestDetail.evidence_analysis.has_invoice" type="success" size="small">有</el-tag>
                <el-tag v-else type="info" size="small">无</el-tag>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="evidence-item" :class="{ active: aiTestDetail.evidence_analysis.has_contract }">
                <el-icon><Tickets /></el-icon>
                <span>合同</span>
                <el-tag v-if="aiTestDetail.evidence_analysis.has_contract" type="success" size="small">有</el-tag>
                <el-tag v-else type="info" size="small">无</el-tag>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="evidence-item" :class="{ active: aiTestDetail.evidence_analysis.has_receipt }">
                <el-icon><Money /></el-icon>
                <span>银行回单</span>
                <el-tag v-if="aiTestDetail.evidence_analysis.has_receipt" type="success" size="small">有</el-tag>
                <el-tag v-else type="info" size="small">无</el-tag>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="evidence-item" :class="{ active: aiTestDetail.evidence_analysis.has_logistics }">
                <el-icon><Van /></el-icon>
                <span>物流单</span>
                <el-tag v-if="aiTestDetail.evidence_analysis.has_logistics" type="success" size="small">有</el-tag>
                <el-tag v-else type="info" size="small">无</el-tag>
              </div>
            </el-col>
          </el-row>

          <div class="evidence-status">
            <span>完整性评分：</span>
            <el-progress
              :percentage="aiTestDetail.evidence_analysis.completeness_score || 0"
              :color="aiTestDetail.evidence_analysis.completeness_score >= 70 ? '#67c23a' : (aiTestDetail.evidence_analysis.completeness_score >= 40 ? '#e6a23c' : '#f56c6c')"
              style="width: 200px; display: inline-block"
            />
            <el-tag
              :type="aiTestDetail.evidence_analysis.match_status === 'matched' ? 'success' : (aiTestDetail.evidence_analysis.match_status === 'partial' ? 'warning' : 'danger')"
              style="margin-left: 16px"
            >
              {{ aiTestDetail.evidence_analysis.match_status === 'matched' ? '完整' : (aiTestDetail.evidence_analysis.match_status === 'partial' ? '部分完整' : '不完整') }}
            </el-tag>
          </div>

          <!-- 异常描述 -->
          <div v-if="aiTestDetail.evidence_analysis.anomalies?.length" class="anomaly-section">
            <div class="anomaly-title">发现异常</div>
            <el-alert
              v-for="anomaly in aiTestDetail.evidence_analysis.anomalies"
              :key="anomaly"
              :title="anomaly"
              type="warning"
              :closable="false"
              style="margin-bottom: 8px"
            />
          </div>
        </div>

        <!-- 附件分析详情 -->
        <div class="detail-section" v-if="aiTestDetail.evidence_analysis?.attachment_analysis?.length">
          <h4>附件分析详情</h4>
          <el-table :data="aiTestDetail.evidence_analysis.attachment_analysis" size="small">
            <el-table-column prop="file_name" label="文件名" min-width="150" show-overflow-tooltip />
            <el-table-column prop="doc_type" label="文档类型" width="100">
              <template #default="{ row }">
                {{ getDocTypeLabel(row.doc_type) }}
              </template>
            </el-table-column>
            <el-table-column label="提取信息" min-width="200">
              <template #default="{ row }">
                <div v-if="row.extracted_info">
                  <div v-if="row.extracted_info.amount">金额: {{ row.extracted_info.amount }}</div>
                  <div v-if="row.extracted_info.date">日期: {{ row.extracted_info.date }}</div>
                  <div v-if="row.extracted_info.party">交易方: {{ row.extracted_info.party }}</div>
                </div>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="置信度" width="100">
              <template #default="{ row }">
                {{ (row.confidence * 100).toFixed(0) }}%
              </template>
            </el-table-column>
            <el-table-column label="异常" width="150">
              <template #default="{ row }">
                <el-tag v-for="a in row.anomalies" :key="a" type="warning" size="small" style="margin-right: 4px">
                  {{ a }}
                </el-tag>
                <span v-if="!row.anomalies?.length" class="text-muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 交叉验证 -->
        <div class="detail-section" v-if="aiTestDetail.evidence_analysis?.cross_validation">
          <h4>交叉验证</h4>
          <el-alert
            :type="aiTestDetail.evidence_analysis.cross_validation.is_consistent ? 'success' : 'warning'"
            :title="aiTestDetail.evidence_analysis.cross_validation.is_consistent ? '信息一致' : '存在不一致'"
            :description="aiTestDetail.evidence_analysis.cross_validation.validation_details"
            :closable="false"
          />
          <div v-if="aiTestDetail.evidence_analysis.cross_validation.discrepancies?.length" style="margin-top: 12px">
            <div class="anomaly-title">不一致项</div>
            <el-tag
              v-for="d in aiTestDetail.evidence_analysis.cross_validation.discrepancies"
              :key="d"
              type="warning"
              style="margin-right: 8px"
            >
              {{ d }}
            </el-tag>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button v-if="aiTestDetail?.ai_conclusion !== 'valid'" type="warning" @click="openOverrideFromDetail">
          修正判定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu, CircleCheck, Warning, QuestionFilled, Document, Tickets, Money, Van } from '@element-plus/icons-vue'
import { samplingApi } from '@/api'

const loading = ref(false)
const testing = ref(false)
const submitting = ref(false)
const samplingRecords = ref([])
const selectedRecordId = ref('')
const samples = ref([])
const selectedSamples = ref([])
const totalSamples = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const testStats = ref({
  total: 0,
  pending: 0,
  completed: 0,
  suspectedError: 0,
  needsReview: 0,
  exception: 0
})

// 错报记录对话框
const misstatementDialogVisible = ref(false)
const currentSample = ref(null)
const evidenceUploadRef = ref()
const evidenceFile = ref(null)
const misstatementForm = reactive({
  misstatement_type: 'amount_error',
  original_amount: 0,
  correct_amount: 0,
  misstatement_amount: 0,
  description: ''
})

// 人工修正对话框
const overrideDialogVisible = ref(false)
const overrideForm = reactive({
  ai_result_id: '',
  override_conclusion: 'valid',
  override_reason: ''
})

// AI分析详情对话框
const detailDialogVisible = ref(false)
const aiTestDetail = ref(null)

const testProgress = computed(() => {
  if (testStats.value.total === 0) return 0
  const completed = testStats.value.completed + testStats.value.suspectedError + testStats.value.needsReview
  return Math.round(completed / testStats.value.total * 100)
})

const loadSamplingRecords = async () => {
  const projectId = localStorage.getItem('currentProjectId')
  if (!projectId) return

  try {
    const records = await samplingApi.getRecords(projectId)
    samplingRecords.value = records || []
  } catch (error) {
    console.error('加载抽样记录失败:', error)
  }
}

const loadSamples = async () => {
  if (!selectedRecordId.value) return

  const projectId = localStorage.getItem('currentProjectId')
  loading.value = true

  try {
    const res = await samplingApi.getRecordDetail(projectId, selectedRecordId.value)
    samples.value = res.samples || []
    totalSamples.value = res.samples?.length || 0

    // 计算统计数据
    const stats = { total: 0, pending: 0, completed: 0, suspectedError: 0, needsReview: 0, exception: 0 }
    res.samples?.forEach(s => {
      stats.total++
      if (s.test_status === 'pending') stats.pending++
      else if (s.test_status === 'completed') stats.completed++
      else if (s.test_status === 'suspected_error') stats.suspectedError++
      else if (s.test_status === 'needs_review') stats.needsReview++
      else if (s.test_status === 'exception') stats.exception++
    })
    testStats.value = stats
  } catch (error) {
    ElMessage.error('加载样本失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedSamples.value = selection
}

const executeAiTest = async () => {
  if (!selectedRecordId.value) return

  const projectId = localStorage.getItem('currentProjectId')
  const sampleIds = samples.value
    .filter(s => s.test_status === 'pending')
    .map(s => s.id)

  if (sampleIds.length === 0) {
    ElMessage.warning('没有待测试的样本')
    return
  }

  testing.value = true
  try {
    const result = await samplingApi.executeTest(projectId, { sample_ids: sampleIds })
    ElMessage.success(`测试完成: ${result.total_tested}个样本, ${result.need_review_count}个需复核`)
    loadSamples()
  } catch (error) {
    ElMessage.error('测试失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    testing.value = false
  }
}

const batchTest = async () => {
  if (selectedSamples.value.length === 0) return

  const projectId = localStorage.getItem('currentProjectId')
  const sampleIds = selectedSamples.value.map(s => s.id)

  testing.value = true
  try {
    const result = await samplingApi.executeTest(projectId, { sample_ids: sampleIds })
    ElMessage.success(`测试完成: ${result.total_tested}个样本, ${result.need_review_count}个需复核`)
    loadSamples()
  } catch (error) {
    ElMessage.error('测试失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    testing.value = false
  }
}

const openMisstatementDialog = (row) => {
  currentSample.value = row
  misstatementForm.misstatement_type = 'amount_error'
  misstatementForm.original_amount = row.amount || 0
  misstatementForm.correct_amount = row.amount || 0
  misstatementForm.misstatement_amount = 0
  misstatementForm.description = ''
  evidenceFile.value = null
  misstatementDialogVisible.value = true
}

const handleEvidenceChange = (file) => {
  evidenceFile.value = file.raw
}

const handleEvidenceRemove = () => {
  evidenceFile.value = null
}

const submitMisstatement = async () => {
  if (!misstatementForm.description) {
    ElMessage.warning('请填写错报描述')
    return
  }

  const projectId = localStorage.getItem('currentProjectId')
  submitting.value = true

  try {
    const result = await samplingApi.createMisstatement(projectId, {
      sample_id: currentSample.value.id,
      ...misstatementForm
    })

    // 如果有证据文件，上传
    if (evidenceFile.value && result.id) {
      try {
        await samplingApi.uploadMisstatementEvidence(projectId, result.id, evidenceFile.value)
      } catch (uploadError) {
        console.error('证据上传失败:', uploadError)
        ElMessage.warning('错报记录成功，但证据上传失败')
      }
    }

    ElMessage.success('错报记录成功')
    misstatementDialogVisible.value = false
    loadSamples()
  } catch (error) {
    ElMessage.error('记录失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

const openOverrideDialog = (row) => {
  currentSample.value = row
  overrideForm.ai_result_id = row.ai_result_id || ''
  overrideForm.override_conclusion = 'valid'
  overrideForm.override_reason = ''
  overrideDialogVisible.value = true
}

const submitOverride = async () => {
  if (!overrideForm.override_reason) {
    ElMessage.warning('请填写修正原因')
    return
  }

  const projectId = localStorage.getItem('currentProjectId')
  submitting.value = true

  try {
    await samplingApi.manualOverride(projectId, currentSample.value.id, {
      ai_result_id: overrideForm.ai_result_id,
      override_conclusion: overrideForm.override_conclusion,
      override_reason: overrideForm.override_reason
    })
    ElMessage.success('修正成功')
    overrideDialogVisible.value = false
    loadSamples()
  } catch (error) {
    ElMessage.error('修正失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

const viewDetail = async (row) => {
  // 加载AI分析详情
  const projectId = localStorage.getItem('currentProjectId')
  try {
    const detail = await samplingApi.getSampleDetail(projectId, row.id)
    currentSample.value = row
    aiTestDetail.value = detail.ai_test_result_detail || null
    detailDialogVisible.value = true
  } catch (error) {
    // 如果获取详情失败，显示基本信息
    currentSample.value = row
    aiTestDetail.value = {
      ai_conclusion: row.ai_test_result,
      risk_level: row.risk_level,
      risk_score: row.risk_score,
      confidence: 0.7
    }
    detailDialogVisible.value = true
  }
}

const openOverrideFromDetail = () => {
  detailDialogVisible.value = false
  openOverrideDialog(currentSample.value)
}

const getDocTypeLabel = (type) => {
  const map = {
    contract: '合同',
    invoice: '发票',
    receipt: '银行回单',
    logistics: '物流单',
    unknown: '未知'
  }
  return map[type] || type
}

const formatAmount = (amount) => {
  if (amount === null || amount === undefined) return '-'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const getStatusTag = (status) => {
  const map = {
    pending: 'info',
    testing: 'warning',
    completed: 'success',
    suspected_error: 'danger',
    needs_review: 'warning',
    exception: 'danger'
  }
  return map[status] || 'info'
}

const getStatusLabel = (status) => {
  const map = {
    pending: '待测试',
    testing: '测试中',
    completed: '正常',
    suspected_error: '疑似错报',
    needs_review: '需复核',
    exception: '异常'
  }
  return map[status] || status || '待测试'
}

const getAiResultTag = (result) => {
  const map = { valid: 'success', abnormal: 'danger', uncertain: 'warning' }
  return map[result] || 'info'
}

const getAiResultLabel = (result) => {
  const map = { valid: '真实合理', abnormal: '存在异常', uncertain: '无法判断' }
  return map[result] || result || '-'
}

const getRiskColor = (score) => {
  if (score >= 70) return '#f56c6c'
  if (score >= 40) return '#e6a23c'
  return '#67c23a'
}

onMounted(() => {
  loadSamplingRecords()
})
</script>

<style lang="scss" scoped>
/* 覆盖页面容器边距，参考凭证管理页面 */
.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

.progress-card {
  margin-bottom: 20px;
}

.progress-stats {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;

  .stat-item {
    text-align: center;

    .stat-value {
      display: block;
      font-size: 28px;
      font-weight: 600;
      color: #303133;

      &.pending { color: #909399; }
      &.success { color: #67c23a; }
      &.danger { color: #f56c6c; }
      &.warning { color: #e6a23c; }
    }

    .stat-label {
      display: block;
      font-size: 13px;
      color: #909399;
      margin-top: 4px;
    }
  }
}

.large-amount {
  color: #f56c6c;
  font-weight: 600;
}

.error-amount {
  color: #f56c6c;
  font-weight: 600;
}

.text-muted {
  color: #c0c4cc;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.ai-detail-content {
  .detail-section {
    margin-bottom: 24px;

    h4 {
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid #ebeef5;
      font-size: 15px;
      color: #303133;
    }
  }

  .conclusion-box {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px;
    border-radius: 8px;
    background: #f5f7fa;

    &.valid {
      background: #f0f9eb;
      color: #67c23a;
    }

    &.abnormal {
      background: #fef0f0;
      color: #f56c6c;
    }

    &.uncertain {
      background: #fdf6ec;
      color: #e6a23c;
    }

    .conclusion-text {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .conclusion-label {
        font-size: 18px;
        font-weight: 600;
      }

      .confidence {
        font-size: 13px;
        opacity: 0.8;
      }
    }
  }

  .risk-gauge {
    text-align: center;

    .percentage-value {
      display: block;
      font-size: 28px;
      font-weight: 600;
    }

    .percentage-label {
      display: block;
      font-size: 12px;
      color: #909399;
    }
  }

  .risk-factors {
    margin-bottom: 12px;

    .factor-title {
      font-size: 13px;
      color: #606266;
      margin-bottom: 8px;
    }
  }

  .risk-level {
    font-size: 14px;
  }

  .evidence-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 16px;
    background: #f5f7fa;
    border-radius: 8px;
    text-align: center;

    &.active {
      background: #f0f9eb;
    }

    .el-icon {
      font-size: 28px;
      color: #909399;
    }

    span {
      font-size: 13px;
      color: #606266;
    }
  }

  .evidence-status {
    margin-top: 16px;
    display: flex;
    align-items: center;
  }

  .anomaly-section {
    margin-top: 16px;

    .anomaly-title {
      font-size: 13px;
      color: #e6a23c;
      margin-bottom: 8px;
      font-weight: 500;
    }
  }
}
</style>