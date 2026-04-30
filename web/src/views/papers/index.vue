<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">工作底稿</h2>
      <div style="display: flex; gap: 12px; align-items: center;">
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
        <el-button type="primary" @click="openGenerateDialog" :loading="generating" :disabled="!projectId">
          <el-icon><Document /></el-icon>
          生成底稿
        </el-button>
      </div>
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
                导出 PDF
              </el-button>
            </div>
          </template>
          <el-table :data="papers" style="width: 100%" @row-click="selectPaper" highlight-current-row>
            <el-table-column prop="title" label="底稿名称" min-width="200" />
            <el-table-column prop="paper_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ getPaperTypeLabel(row.paper_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="生成时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button type="danger" link size="small" @click.stop="deletePaper(row)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="papers.length === 0" description="暂无已生成底稿" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <el-card class="card-container" v-if="selectedPaper">
      <template #header>
        <span class="card-title">底稿预览</span>
      </template>
      <div class="paper-preview">
        <h3>{{ selectedPaper.title }}</h3>
        <div class="paper-content">{{ selectedPaper.ai_description }}</div>
      </div>
    </el-card>

    <!-- 生成底稿对话框 -->
    <el-dialog v-model="dialogVisible" title="生成底稿" width="500px">
      <el-form :model="generateForm" label-width="100px">
        <el-form-item label="底稿类型">
          <el-select v-model="generateForm.paper_type" style="width: 100%">
            <el-option
              v-for="type in paperTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="科目代码" v-if="generateForm.paper_type === 'substantive_test'">
          <el-select v-model="generateForm.subject_code" placeholder="选择科目" style="width: 100%">
            <el-option
              v-for="subject in subjectOptions"
              :key="subject.code"
              :label="`${subject.code} - ${subject.name}`"
              :value="subject.code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="包含 AI 描述">
          <el-checkbox v-model="generateForm.include_ai_description" :checked="true" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmGenerate" :loading="generating">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Download, Notebook, Delete } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/formatters'
import { paperApi, projectApi, samplingApi } from '@/api'

const generating = ref(false)
const selectedTemplate = ref('standard')
const selectedPaper = ref(null)
const papers = ref([])
const projectId = ref(localStorage.getItem('currentProjectId') || '')
const projects = ref([])
const dialogVisible = ref(false)
const generateForm = reactive({
  paper_type: 'sampling_summary',
  subject_code: '',
  include_ai_description: true
})

const paperTypes = [
  { value: 'sampling_summary', label: '抽样情况汇总表' },
  { value: 'substantive_test', label: '实质性程序测试底稿' },
  { value: 'compliance_test', label: '合规性测试底稿' },
  { value: 'risk_assessment', label: '风险评估底稿' }
]

const subjectOptions = ref([])

const templates = [
  { id: 'standard', name: '标准底稿模板' },
  { id: 'simplified', name: '简化底稿模板' },
  { id: 'detailed', name: '详细底稿模板' }
]

const getPaperTypeLabel = (type) => {
  const labels = {
    sampling_summary: '抽样汇总',
    substantive_test: '实质性测试',
    compliance_test: '合规性测试',
    risk_assessment: '风险评估'
  }
  return labels[type] || type
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

const loadSubjectOptions = async () => {
  if (!projectId.value) return
  try {
    const res = await samplingApi.getPopulationStats(projectId.value)
    subjectOptions.value = res.subjects || []
  } catch (error) {
    console.error(error)
  }
}

const loadPapers = async () => {
  if (!projectId.value) return
  try {
    const res = await paperApi.getList(projectId.value)
    papers.value = res.items || []
  } catch (error) {
    console.error(error)
    ElMessage.error('加载底稿列表失败')
  }
}

const onProjectChange = (val) => {
  localStorage.setItem('currentProjectId', val)
  loadSubjectOptions()
  loadPapers()
}

const openGenerateDialog = () => {
  generateForm.paper_type = 'sampling_summary'
  generateForm.subject_code = ''
  dialogVisible.value = true
}

const confirmGenerate = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  generating.value = true
  try {
    const data = {
      paper_type: generateForm.paper_type,
      include_ai_description: generateForm.include_ai_description
    }
    if (generateForm.paper_type === 'substantive_test' && generateForm.subject_code) {
      data.subject_code = generateForm.subject_code
    }

    const res = await paperApi.generate(projectId.value, data)
    ElMessage.success('底稿生成成功')
    dialogVisible.value = false
    await loadPapers()

    // 加载生成的底稿详情
    if (res.paper_id) {
      const detail = await paperApi.getDetail(projectId.value, res.paper_id)
      selectedPaper.value = detail
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('生成失败：' + (error.response?.data?.detail || error.message))
  } finally {
    generating.value = false
  }
}

const selectPaper = async (row) => {
  selectedPaper.value = row
  // 加载底稿详情
  try {
    const detail = await paperApi.getDetail(projectId.value, row.id)
    selectedPaper.value = detail
  } catch (error) {
    console.error(error)
  }
}

const exportPaper = async () => {
  if (!selectedPaper.value || !projectId.value) {
    ElMessage.warning('请先选择要导出的底稿')
    return
  }

  try {
    const blob = await paperApi.export(projectId.value, selectedPaper.value.id, 'pdf')
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${selectedPaper.value.title}.pdf`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('导出失败')
  }
}

const deletePaper = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除底稿「${row.title}」吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await paperApi.delete(projectId.value, row.id)
    ElMessage.success('删除成功')

    if (selectedPaper.value?.id === row.id) {
      selectedPaper.value = null
    }
    await loadPapers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('删除失败')
    }
  }
}

onMounted(async () => {
  await loadProjects()
  if (projectId.value) {
    await loadSubjectOptions()
    await loadPapers()
  }
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

/* 覆盖页面容器边距，参考凭证管理页面 */
.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

.template-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 1px solid $border-lighter;
  border-radius: $border-radius-lg;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: $primary-light;
    background: $background-hover;
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
    font-size: $font-size-xl;
  }

  .paper-content {
    color: $text-regular;
    line-height: 1.8;
  }
}

// 表格横向滚动
:deep(.el-table) {
  .el-table__body-wrapper {
    overflow-x: auto;
  }

  .el-table__cell .cell {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}
</style>
