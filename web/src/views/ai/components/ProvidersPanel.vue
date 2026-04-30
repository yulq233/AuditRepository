<template>
  <div class="providers-panel">
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="6" v-for="provider in providers" :key="provider.name">
        <el-card class="provider-card" shadow="hover">
          <div class="provider-header">
            <div class="provider-logo">{{ provider.display_name }}</div>
            <el-tag :type="provider.is_available ? 'success' : 'danger'" size="small">
              {{ provider.is_available ? '可用' : '不可用' }}
            </el-tag>
          </div>
          <div class="provider-info">
            <div class="info-row">
              <span class="info-label">API Key</span>
              <el-tag :type="provider.api_key_configured ? 'success' : 'warning'" size="small">
                {{ provider.api_key_configured ? '已配置' : '未配置' }}
              </el-tag>
            </div>
            <div class="info-row">
              <span class="info-label">可用模型</span>
              <span class="info-value">{{ provider.models.length }} 个</span>
            </div>
            <div class="info-row" v-if="provider.base_url">
              <span class="info-label">Base URL</span>
              <span class="info-value url">{{ truncateUrl(provider.base_url) }}</span>
            </div>
          </div>
          <el-button type="primary" link @click="showModels(provider)">
            查看模型列表
          </el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- 配置提示 -->
    <el-alert type="info" :closable="false" class="config-tip">
      <template #title>
        <el-icon><InfoFilled /></el-icon>
        API Key配置说明
      </template>
      API Key通过服务器环境变量配置，请参考 .env.example 文件中的配置示例。
      支持的变量：QWEN_API_KEY、ZHIPU_API_KEY、ERNIE_API_KEY
    </el-alert>

    <!-- 模型列表弹窗 -->
    <el-dialog v-model="showModelsDialog" :title="currentProvider?.display_name + ' - 可用模型'" width="600px">
      <el-table :data="currentProvider?.models || []" stripe>
        <el-table-column prop="" label="模型名称">
          <template #default="{ row }">
            <el-tag effect="plain">{{ row }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'

const providers = ref([])
const showModelsDialog = ref(false)
const currentProvider = ref(null)
const loading = ref(false)

const fetchProviders = async () => {
  loading.value = true
  try {
    const res = await request.get('/ai/providers')
    providers.value = res.data || res
  } catch (error) {
    console.error('获取供应商列表失败:', error)
    ElMessage.error('获取供应商列表失败')
  } finally {
    loading.value = false
  }
}

const showModels = (provider) => {
  currentProvider.value = provider
  showModelsDialog.value = true
}

const truncateUrl = (url) => {
  if (!url) return ''
  if (url.length > 30) {
    return url.substring(0, 30) + '...'
  }
  return url
}

onMounted(() => {
  fetchProviders()
})
</script>

<style lang="scss" scoped>
.providers-panel {
  .provider-card {
    margin-bottom: 20px;

    .provider-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;

      .provider-logo {
        font-size: 18px;
        font-weight: 600;
        color: #303133;
      }
    }

    .provider-info {
      .info-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #f0f0f0;

        &:last-child {
          border-bottom: none;
        }

        .info-label {
          color: #909399;
          font-size: 13px;
        }

        .info-value {
          color: #303133;
          font-size: 14px;

          &.url {
            color: #409eff;
            font-size: 12px;
          }
        }
      }
    }
  }

  .config-tip {
    margin-top: 20px;
  }
}
</style>