<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">工作底稿</h2>
      <el-button type="primary" @click="generatePaper" :loading="generating">
        <el-icon><Document /></el-icon>
        生成底稿
      </el-button>
    </div>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="card-container">
          <template #header>
            <span class="card-title">底稿模板</span>
          </template>
          <div class="template-list">
            <div
              v-for="tpl in templates"
              :key="tpl.id"
              :class="['template-item', { active: selectedTemplate === tpl.id }]"
              @click="selectedTemplate = tpl.id"
            >
              <el-icon :size="24"><Notebook /></el-icon>
              <span>{{ tpl.name }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card class="card-container">
          <template #header>
            <div class="card-header">
              <span class="card-title">已生成底稿</span>
              <el-button type="primary" link @click="exportPaper" :disabled="!selectedPaper">
                <el-icon><Download /></el-icon>
                导出PDF
              </el-button>
            </div>
          </template>
          <el-table :data="papers" style="width: 100%" @row-click="selectPaper" highlight-current-row>
            <el-table-column prop="title" label="底稿名称" min-width="200" />
            <el-table-column prop="paper_type" label="类型" width="100" />
            <el-table-column prop="generated_at" label="生成时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.generated_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="card-container" v-if="selectedPaper">
      <template #header>
        <span class="card-title">底稿预览</span>
      </template>
      <div class="paper-preview">
        <h3>{{ selectedPaper.title }}</h3>
        <div class="paper-content" v-html="selectedPaper.ai_description"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { formatDate } from '@/utils/formatters'

const generating = ref(false)
const selectedTemplate = ref('standard')
const selectedPaper = ref(null)
const papers = ref([])

const templates = [
  { id: 'standard', name: '标准底稿模板' },
  { id: 'simplified', name: '简化底稿模板' },
  { id: 'detailed', name: '详细底稿模板' }
]

const generatePaper = async () => {
  generating.value = true
  // TODO: 调用API生成底稿
  setTimeout(() => {
    generating.value = false
  }, 1000)
}

const selectPaper = (row) => {
  selectedPaper.value = row
}

const exportPaper = () => {
  // TODO: 导出PDF
}

onMounted(() => {
  // TODO: 加载底稿列表
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.template-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: $primary-color;
  }

  &.active {
    border-color: $primary-color;
    background: $primary-lighter;
  }
}

.paper-preview {
  h3 {
    margin-bottom: $spacing-md;
    color: $text-primary;
  }

  .paper-content {
    color: $text-regular;
    line-height: 1.8;
  }
}
</style>