<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">AI服务</h2>
      <p class="page-subtitle">配置和管理AI模型</p>
    </div>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="card-container">
          <template #header>
            <span class="card-title">模型配置</span>
          </template>
          <el-form :model="config" label-width="100px">
            <el-form-item label="服务提供商">
              <el-select v-model="config.provider" style="width: 100%">
                <el-option label="Ollama (本地)" value="ollama" />
                <el-option label="通义千问" value="qwen" />
                <el-option label="文心一言" value="ernie" />
                <el-option label="智谱GLM" value="glm" />
              </el-select>
            </el-form-item>
            <el-form-item label="模型">
              <el-select v-model="config.model" style="width: 100%">
                <el-option
                  v-for="m in availableModels"
                  :key="m.value"
                  :label="m.label"
                  :value="m.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="API密钥" v-if="config.provider !== 'ollama'">
              <el-input v-model="config.apiKey" type="password" show-password />
            </el-form-item>
            <el-form-item label="服务地址" v-if="config.provider === 'ollama'">
              <el-input v-model="config.baseUrl" placeholder="http://localhost:11434" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveConfig">保存配置</el-button>
              <el-button @click="testConnection" :loading="testing">测试连接</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card class="card-container">
          <template #header>
            <div class="card-header">
              <span class="card-title">AI能力测试</span>
            </div>
          </template>
          <el-form :model="testForm" label-width="80px">
            <el-form-item label="输入文本">
              <el-input
                v-model="testForm.input"
                type="textarea"
                :rows="4"
                placeholder="输入凭证描述或问题..."
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runTest" :loading="running">
                执行分析
              </el-button>
            </el-form-item>
          </el-form>
          <el-divider />
          <div class="test-result" v-if="testResult">
            <h4>分析结果</h4>
            <div class="result-content">{{ testResult }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="card-container">
      <template #header>
        <span class="card-title">服务状态</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="status-item">
            <el-icon :size="32" :color="status.ollama ? '#67c23a' : '#f56c6c'">
              <CircleCheckFilled v-if="status.ollama" />
              <CircleCloseFilled v-else />
            </el-icon>
            <span>Ollama</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <el-icon :size="32" :color="status.qwen ? '#67c23a' : '#909399'">
              <CircleCheckFilled v-if="status.qwen" />
              <CircleCloseFilled v-else />
            </el-icon>
            <span>通义千问</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <el-icon :size="32" :color="status.ernie ? '#67c23a' : '#909399'">
              <CircleCheckFilled v-if="status.ernie" />
              <CircleCloseFilled v-else />
            </el-icon>
            <span>文心一言</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-item">
            <el-icon :size="32" :color="status.glm ? '#67c23a' : '#909399'">
              <CircleCheckFilled v-if="status.glm" />
              <CircleCloseFilled v-else />
            </el-icon>
            <span>智谱GLM</span>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'

const testing = ref(false)
const running = ref(false)
const testResult = ref('')

const config = reactive({
  provider: 'ollama',
  model: 'qwen2.5:14b',
  apiKey: '',
  baseUrl: 'http://localhost:11434'
})

const testForm = reactive({
  input: ''
})

const status = reactive({
  ollama: false,
  qwen: false,
  ernie: false,
  glm: false
})

const availableModels = computed(() => {
  const models = {
    ollama: [
      { label: 'Qwen2.5 14B', value: 'qwen2.5:14b' },
      { label: 'Qwen2.5 7B', value: 'qwen2.5:7b' },
      { label: 'Llama3 8B', value: 'llama3:8b' }
    ],
    qwen: [
      { label: '通义千问-Turbo', value: 'qwen-turbo' },
      { label: '通义千问-Plus', value: 'qwen-plus' },
      { label: '通义千问-Max', value: 'qwen-max' }
    ],
    ernie: [
      { label: 'ERNIE 4.0', value: 'ernie-4.0-8k' },
      { label: 'ERNIE 3.5', value: 'ernie-3.5-8k' }
    ],
    glm: [
      { label: 'GLM-4', value: 'glm-4' },
      { label: 'GLM-3-Turbo', value: 'glm-3-turbo' }
    ]
  }
  return models[config.provider] || []
})

const saveConfig = async () => {
  // TODO: 保存配置
}

const testConnection = async () => {
  testing.value = true
  // TODO: 测试连接
  setTimeout(() => {
    status.ollama = true
    testing.value = false
  }, 1000)
}

const runTest = async () => {
  running.value = true
  // TODO: 运行测试
  setTimeout(() => {
    testResult.value = '这是一个测试结果...'
    running.value = false
  }, 1000)
}

onMounted(() => {
  testConnection()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;

  span {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.test-result {
  h4 {
    margin-bottom: $spacing-sm;
    color: $text-primary;
  }

  .result-content {
    padding: $spacing-md;
    background: $background-color;
    border-radius: $border-radius-md;
    white-space: pre-wrap;
    font-family: monospace;
  }
}
</style>