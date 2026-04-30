<template>
  <div class="model-config">
    <!-- 顶部状态概览 -->
    <el-card class="status-card" shadow="never">
      <el-row :gutter="20">
        <el-col :span="8" v-for="(status, key) in purposeStatus" :key="key">
          <div class="status-item" :class="{ 'active': status.is_available }">
            <el-icon :size="24">
              <component :is="status.icon" />
            </el-icon>
            <div class="status-info">
              <div class="status-label">{{ status.label }}</div>
              <div class="status-model">{{ status.model || '未配置' }}</div>
            </div>
            <el-tag :type="status.is_available ? 'success' : 'danger'" size="small">
              {{ status.is_available ? '可用' : '不可用' }}
            </el-tag>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 用途配置列表 -->
    <div class="purpose-list">
      <el-card class="purpose-card" shadow="never" v-for="(config, purpose) in purposeConfigs" :key="purpose">
        <div class="purpose-header" @click="expandPurpose(purpose)">
          <div class="purpose-icon" :class="purpose">
            <el-icon :size="20">
              <component :is="getPurposeIcon(purpose)" />
            </el-icon>
          </div>
          <div class="purpose-title">
            <div class="purpose-name">{{ getPurposeName(purpose) }}</div>
            <div class="purpose-desc">{{ getPurposeDesc(purpose) }}</div>
          </div>
          <div class="purpose-status">
            <el-tag :type="config.is_available ? 'success' : 'danger'" size="small">
              {{ config.is_available ? '可用' : '不可用' }}
            </el-tag>
            <span class="model-tag" v-if="config.model">{{ config.model }}</span>
          </div>
          <el-icon class="expand-icon" :class="{ 'expanded': expandedPurpose === purpose }">
            <ArrowDown />
          </el-icon>
        </div>

        <div class="purpose-body" v-show="expandedPurpose === purpose">
          <el-form label-width="100px">
            <el-form-item label="当前模型">
              <span class="form-value">{{ config.model || '未选择' }}</span>
            </el-form-item>
            <el-form-item label="API Key">
              <el-tag :type="config.has_api_key ? 'success' : 'warning'" size="small">
                {{ config.has_api_key ? '已配置' : '未配置' }}
              </el-tag>
              <el-tooltip content="API Key请在服务器环境变量中配置（如QWEN_API_KEY）">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </el-form-item>
            <el-form-item label="温度参数">
              <el-slider v-model="config.temperature" :min="0" :max="2" :step="0.1" show-input />
            </el-form-item>
            <el-form-item label="最大Token">
              <el-input-number v-model="config.max_tokens" :min="100" :max="8000" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="openModelSelector(purpose)">
                <el-icon><Setting /></el-icon> 选择模型
              </el-button>
              <el-button type="warning" :loading="testing[purpose]" :disabled="!config.model" @click="testModel(purpose)">
                <el-icon><Connection /></el-icon> 测试模型
              </el-button>
              <el-button type="success" :loading="config.saving" @click="saveConfig(purpose)">
                <el-icon><Check /></el-icon> 保存配置
              </el-button>
            </el-form-item>
            <el-form-item v-if="testResults[purpose]">
              <div class="test-result" :class="{ 'success': testResults[purpose].success, 'error': !testResults[purpose].success }">
                <span v-if="testResults[purpose].success">
                  测试成功，耗时 {{ testResults[purpose].elapsed_time }}ms
                </span>
                <span v-else>
                  测试失败：{{ testResults[purpose].error }}
                </span>
              </div>
            </el-form-item>
          </el-form>
        </div>
      </el-card>
    </div>

    <!-- 模型选择器弹窗 -->
    <el-dialog v-model="showModelSelector" title="选择模型" width="500px">
      <el-tabs v-model="modelFilter">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="视觉" name="vision" />
        <el-tab-pane label="文本" name="text" />
      </el-tabs>
      <div class="model-list" v-loading="loadingModels">
        <div
          class="model-item"
          v-for="model in filteredModels"
          :key="model.model"
          :class="{ 'disabled': !model.is_available, 'selected': isSelectedModel(model.model) }"
          @click="selectModel(model)"
        >
          <div class="model-name">{{ model.model }}</div>
          <div class="model-info">
            <el-tag size="small" effect="plain">{{ model.provider }}</el-tag>
            <el-tag v-if="model.supports_image" type="success" size="small">视觉</el-tag>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound, Picture, Warning, Setting, Check, Connection,
  QuestionFilled, ArrowDown
} from '@element-plus/icons-vue'
import request from '@/utils/request'

const expandedPurpose = ref('general')
const showModelSelector = ref(false)
const loadingModels = ref(false)
const modelFilter = ref('all')
const allModels = ref([])

const testing = reactive({
  general: false,
  recognition: false,
  risk_analysis: false
})

const testResults = reactive({
  general: null,
  recognition: null,
  risk_analysis: null
})

const purposeStatus = reactive({
  general: { label: '通用服务', icon: 'ChatDotRound', model: '', is_available: false },
  recognition: { label: '图片识别', icon: 'Picture', model: '', is_available: false },
  risk_analysis: { label: '风险分析', icon: 'Warning', model: '', is_available: false }
})

const purposeConfigs = reactive({
  general: { provider: '', model: '', temperature: 0.7, max_tokens: 2048, is_available: false, has_api_key: false, saving: false },
  recognition: { provider: '', model: '', temperature: 0.3, max_tokens: 2048, is_available: false, has_api_key: false, saving: false },
  risk_analysis: { provider: '', model: '', temperature: 0.3, max_tokens: 2048, is_available: false, has_api_key: false, saving: false }
})

const filteredModels = computed(() => {
  let models = [...allModels.value]
  if (modelFilter.value === 'vision') {
    models = models.filter(m => m.supports_image)
  } else if (modelFilter.value === 'text') {
    models = models.filter(m => !m.supports_image)
  }
  return models.sort((a, b) => b.is_available - a.is_available)
})

const getPurposeIcon = (purpose) => {
  const icons = { general: ChatDotRound, recognition: Picture, risk_analysis: Warning }
  return icons[purpose]
}

const getPurposeName = (purpose) => {
  const names = { general: '通用AI服务', recognition: '图片/PDF识别', risk_analysis: '风险分析' }
  return names[purpose]
}

const getPurposeDesc = (purpose) => {
  const descs = {
    general: '日常对话、问答、文本处理',
    recognition: '凭证附件、发票、合同识别',
    risk_analysis: '凭证风险评估、异常检测'
  }
  return descs[purpose]
}

const expandPurpose = (purpose) => {
  expandedPurpose.value = expandedPurpose.value === purpose ? '' : purpose
}

const isSelectedModel = (modelName) => {
  return purposeConfigs[expandedPurpose.value]?.model === modelName
}

const fetchConfigs = async () => {
  loadingModels.value = true
  try {
    const res = await request.get('/ai/models/purposes')
    const data = res.data || res

    const modelMap = new Map()
    for (const purposeData of data) {
      purposeStatus[purposeData.purpose].model = purposeData.current_model
      purposeStatus[purposeData.purpose].is_available = true

      if (purposeConfigs[purposeData.purpose]) {
        purposeConfigs[purposeData.purpose].model = purposeData.current_model
        purposeConfigs[purposeData.purpose].provider = purposeData.current_provider
        purposeConfigs[purposeData.purpose].is_available = purposeData.models.some(m => m.model === purposeData.current_model && m.is_available)
      }

      for (const model of purposeData.models) {
        if (!modelMap.has(model.model)) {
          modelMap.set(model.model, model)
        }
      }
    }
    allModels.value = Array.from(modelMap.values())

    // 获取配置详情
    const configRes = await request.get('/ai/config/purposes')
    const configs = configRes.data || configRes
    for (const cfg of configs) {
      if (purposeConfigs[cfg.purpose]) {
        Object.assign(purposeConfigs[cfg.purpose], cfg)
        purposeStatus[cfg.purpose].model = cfg.model
        purposeStatus[cfg.purpose].is_available = cfg.is_available
      }
    }
  } catch (error) {
    console.error('获取配置失败:', error)
    ElMessage.error('获取配置失败')
  } finally {
    loadingModels.value = false
  }
}

const openModelSelector = (purpose) => {
  expandedPurpose.value = purpose
  showModelSelector.value = true
}

const selectModel = (model) => {
  if (!model.is_available) {
    ElMessage.warning('该模型当前不可用')
    return
  }
  const purpose = expandedPurpose.value
  purposeConfigs[purpose].model = model.model
  purposeConfigs[purpose].provider = model.provider
  purposeConfigs[purpose].is_available = true
  purposeStatus[purpose].model = model.model
  purposeStatus[purpose].is_available = true
  ElMessage.success(`已选择模型：${model.model}`)
}

const testModel = async (purpose) => {
  if (!purposeConfigs[purpose].model) {
    ElMessage.warning('请先选择模型')
    return
  }

  testing[purpose] = true
  testResults[purpose] = null

  try {
    const res = await request.post('/ai/test-purpose-model', { purpose }, { timeout: 30000 })
    testResults[purpose] = res.data || res
    if (testResults[purpose].success) {
      ElMessage.success(`测试成功，耗时 ${testResults[purpose].elapsed_time}ms`)
    } else {
      ElMessage.error(`测试失败：${testResults[purpose].error}`)
    }
  } catch (error) {
    testResults[purpose] = { success: false, error: error.message }
    ElMessage.error('测试失败')
  } finally {
    testing[purpose] = false
  }
}

const saveConfig = async (purpose) => {
  const config = purposeConfigs[purpose]
  if (!config.model) {
    ElMessage.warning('请先选择模型')
    return
  }

  config.saving = true
  try {
    await request.put('/ai/config/purposes', {
      configs: [{
        purpose,
        provider: config.provider,
        model: config.model,
        temperature: config.temperature,
        max_tokens: config.max_tokens
      }]
    })
    ElMessage.success('配置已保存')
    showModelSelector.value = false
    await fetchConfigs()
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    config.saving = false
  }
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style lang="scss" scoped>
.model-config {
  .status-card {
    margin-bottom: 20px;

    .status-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      border-radius: 8px;
      background: #f5f7fa;
      transition: all 0.3s;

      &.active {
        background: #ecf5ff;
      }

      .status-info {
        flex: 1;
        .status-label { font-size: 14px; font-weight: 500; }
        .status-model { font-size: 12px; color: #909399; }
      }
    }
  }

  .purpose-list {
    .purpose-card {
      margin-bottom: 16px;

      .purpose-header {
        display: flex;
        align-items: center;
        gap: 12px;
        cursor: pointer;

        .purpose-icon {
          width: 40px;
          height: 40px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;

          &.general { background: #409eff; }
          &.recognition { background: #67c23a; }
          &.risk_analysis { background: #e6a23c; }
        }

        .purpose-title {
          flex: 1;
          .purpose-name { font-size: 16px; font-weight: 500; }
          .purpose-desc { font-size: 12px; color: #909399; }
        }

        .model-tag {
          margin-left: 8px;
          font-size: 12px;
          color: #606266;
        }

        .expand-icon {
          transition: transform 0.3s;
          &.expanded { transform: rotate(180deg); }
        }
      }

      .purpose-body {
        padding-top: 20px;
        border-top: 1px solid #f0f0f0;
        margin-top: 16px;

        .form-value {
          color: #606266;
        }

        .help-icon {
          margin-left: 4px;
          color: #909399;
          cursor: help;
        }

        .test-result {
          padding: 8px 12px;
          border-radius: 4px;

          &.success { background: #f0f9eb; color: #67c23a; }
          &.error { background: #fef0f0; color: #f56c6c; }
        }
      }
    }
  }

  .model-list {
    max-height: 300px;
    overflow-y: auto;

    .model-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px;
      margin: 4px 0;
      border-radius: 4px;
      cursor: pointer;
      border: 1px solid #e4e7ed;

      &.disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      &.selected {
        border-color: #409eff;
        background: #ecf5ff;
      }

      &:hover:not(.disabled) {
        background: #f5f7fa;
      }

      .model-info {
        display: flex;
        gap: 4px;
      }
    }
  }
}
</style>