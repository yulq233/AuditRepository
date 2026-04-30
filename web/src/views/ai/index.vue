<template>
  <div class="page-container page-enter">
    <div class="page-header">
      <div>
        <h2 class="page-title">AI服务管理</h2>
        <p class="page-subtitle">管理AI模型配置、用量统计与调用监控</p>
      </div>
    </div>

    <!-- Tab页签布局 -->
    <el-tabs v-model="activeTab" class="ai-tabs" type="border-card">
      <!-- Tab 1: 模型配置 -->
      <el-tab-pane label="模型配置" name="config">
        <ModelConfig />
      </el-tab-pane>

      <!-- Tab 2: 供应商管理 -->
      <el-tab-pane label="供应商管理" name="providers">
        <ProvidersPanel />
      </el-tab-pane>

      <!-- Tab 3: Playground测试 -->
      <el-tab-pane label="Playground" name="playground">
        <PlaygroundPanel />
      </el-tab-pane>

      <!-- Tab 4: 用量统计 -->
      <el-tab-pane label="用量统计" name="usage">
        <UsagePanel />
      </el-tab-pane>

      <!-- Tab 5: 调用日志 -->
      <el-tab-pane label="调用日志" name="logs">
        <LogsPanel />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ModelConfig from './components/ModelConfig.vue'
import ProvidersPanel from './components/ProvidersPanel.vue'
import PlaygroundPanel from './components/PlaygroundPanel.vue'
import UsagePanel from './components/UsagePanel.vue'
import LogsPanel from './components/LogsPanel.vue'

const activeTab = ref('config')
</script>

<style lang="scss" scoped>
.page-container {
  .page-header {
    margin-bottom: 20px;
  }

  .ai-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 0;
    }

    :deep(.el-tabs__content) {
      padding: 20px;
    }
  }
}
</style>