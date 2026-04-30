<template>
  <div class="playground-panel">
    <el-row :gutter="20">
      <!-- 左侧配置 -->
      <el-col :xs="24" :md="6">
        <el-card class="config-card" shadow="never">
          <el-form label-position="top">
            <el-form-item label="供应商">
              <el-select v-model="config.provider" @change="onProviderChange" style="width: 100%">
                <el-option label="通义千问" value="qwen" />
                <el-option label="智谱GLM" value="zhipu" />
                <el-option label="百度文心" value="ernie" />
                <el-option label="本地模型" value="ollama" />
              </el-select>
            </el-form-item>
            <el-form-item label="模型">
              <el-select v-model="config.model" :loading="loadingModels" style="width: 100%">
                <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>
            <el-form-item label="用途">
              <el-select v-model="config.purpose" style="width: 100%">
                <el-option label="通用服务" value="general" />
                <el-option label="图片识别" value="recognition" />
                <el-option label="风险分析" value="risk_analysis" />
              </el-select>
            </el-form-item>
            <el-form-item label="温度">
              <el-slider v-model="config.temperature" :min="0" :max="2" :step="0.1" show-input />
            </el-form-item>
            <el-form-item label="最大Token">
              <el-input-number v-model="config.max_tokens" :min="100" :max="8000" :step="100" style="width: 100%" />
            </el-form-item>
            <el-button type="primary" :loading="testing" @click="runTest" style="width: 100%">
              <el-icon><Cpu /></el-icon>
              运行测试
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧输入输出 -->
      <el-col :xs="24" :md="18">
        <el-card class="io-card" shadow="never">
          <div class="input-section">
            <div class="section-header">
              <span>输入 Prompt</span>
              <el-button type="text" size="small" @click="clearInput">清空</el-button>
            </div>
            <el-input
              v-model="testPrompt"
              type="textarea"
              :rows="6"
              placeholder="输入测试内容，例如：请分析这张凭证的风险..."
            />
          </div>

          <div class="output-section" v-loading="testing">
            <div class="section-header">
              <span>响应结果</span>
              <div class="stats" v-if="testResult">
                <el-tag size="small">耗时: {{ testResult.latency_ms }}ms</el-tag>
                <el-tag size="small" type="success">输入: {{ testResult.input_tokens }} tokens</el-tag>
                <el-tag size="small" type="warning">输出: {{ testResult.output_tokens }} tokens</el-tag>
              </div>
            </div>
            <div class="output-content">
              <pre v-if="testResult?.response">{{ testResult.response }}</pre>
              <span v-else class="placeholder">等待测试...</span>
            </div>
            <el-alert v-if="testResult?.error" type="error" :title="testResult.error" :closable="false" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu } from '@element-plus/icons-vue'
import request from '@/utils/request'

const config = reactive({
  provider: 'qwen',
  model: '',
  purpose: 'general',
  temperature: 0.7,
  max_tokens: 1024
})

const testPrompt = ref('你好，请介绍一下审计抽样的基本原则。')
const testResult = ref(null)
const testing = ref(false)
const loadingModels = ref(false)
const availableModels = ref([])

const fetchModels = async () => {
  loadingModels.value = true
  try {
    const res = await request.get('/ai/providers')
    const providers = res.data || res
    const provider = providers.find(p => p.name === config.provider)
    availableModels.value = provider?.models || []
    if (availableModels.value.length > 0) {
      config.model = availableModels.value[0]
    }
  } catch (error) {
    console.error('获取模型列表失败:', error)
  } finally {
    loadingModels.value = false
  }
}

const onProviderChange = () => {
  config.model = ''
  fetchModels()
}

const runTest = async () => {
  if (!testPrompt.value.trim()) {
    ElMessage.warning('请输入测试内容')
    return
  }
  if (!config.model) {
    ElMessage.warning('请选择模型')
    return
  }

  testing.value = true
  testResult.value = null

  try {
    const res = await request.post('/ai/test-model', {
      provider: config.provider,
      model: config.model,
      purpose: config.purpose,
      prompt: testPrompt.value,
      temperature: config.temperature,
      max_tokens: config.max_tokens
    }, { timeout: 60000 })

    testResult.value = res.data || res
    if (testResult.value.success) {
      ElMessage.success('测试成功')
    } else {
      ElMessage.error('测试失败: ' + testResult.value.error)
    }
  } catch (error) {
    console.error('测试失败:', error)
    testResult.value = {
      success: false,
      error: error.message || '请求失败'
    }
    ElMessage.error('测试失败')
  } finally {
    testing.value = false
  }
}

const clearInput = () => {
  testPrompt.value = ''
  testResult.value = null
}

onMounted(() => {
  fetchModels()
})
</script>

<style lang="scss" scoped>
.playground-panel {
  .config-card {
    height: 100%;
  }

  .io-card {
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      font-weight: 500;
      color: #303133;

      .stats {
        display: flex;
        gap: 8px;
      }
    }

    .input-section {
      margin-bottom: 20px;
    }

    .output-section {
      .output-content {
        background: #f5f7fa;
        border-radius: 8px;
        padding: 16px;
        min-height: 150px;

        pre {
          white-space: pre-wrap;
          word-break: break-word;
          font-family: inherit;
          margin: 0;
        }

        .placeholder {
          color: #909399;
        }
      }
    }
  }
}
</style>