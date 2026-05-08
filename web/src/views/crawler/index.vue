<template>
  <div class="crawler-page">
    <div class="page-header">
      <h2 class="page-title">数据爬取</h2>
      <div class="header-actions">
        <el-select
          v-model="projectId"
          placeholder="选择项目"
          style="width: 220px; margin-right: 12px"
          @change="onProjectChange"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
        <el-button
          type="primary"
          @click="showStartDialog"
          :disabled="!projectId"
        >
          <el-icon><Download /></el-icon>
          启动爬取
        </el-button>
        <el-button
          type="success"
          @click="showImportDialog"
          :disabled="!projectId"
        >
          <el-icon><Upload /></el-icon>
          Excel导入
        </el-button>
      </div>
    </div>

    <!-- 平台信息卡片 -->
    <div class="platform-cards" v-if="platforms.length">
      <el-card
        v-for="platform in platforms"
        :key="platform.id"
        class="platform-card"
        shadow="hover"
        :class="{ 'disabled': platform.status === 'coming_soon' }"
      >
        <div class="platform-info">
          <div class="platform-icon">
            <el-icon size="32"><Download /></el-icon>
          </div>
          <div class="platform-details">
            <h3>
              {{ platform.name }}
              <el-tag v-if="platform.status === 'coming_soon'" type="info" size="small">开发中</el-tag>
            </h3>
            <p>{{ platform.description }}</p>
            <el-tag v-if="platform.supports_attachments" type="success" size="small">
              支持附件下载
            </el-tag>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 任务列表 -->
    <el-card class="task-list-card">
      <template #header>
        <div class="card-header">
          <span>爬取任务列表</span>
          <el-button text @click="loadTasks">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="tasks" v-loading="loading" stripe>
        <el-table-column prop="platform" label="平台" width="150">
          <template #default="{ row }">
            {{ getPlatformName(row.platform) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="200">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress
                :percentage="getProgress(row)"
                :status="getProgressStatus(row.status)"
              />
              <span class="progress-text">{{ row.success_count }} / {{ row.total_count || row.success_count }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="finished_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.finished_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="150">
          <template #default="{ row }">
            <el-text v-if="row.error_message" type="danger">
              {{ row.error_message }}
            </el-text>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'running'"
              type="danger"
              size="small"
              @click="stopTask(row.id)"
            >
              停止
            </el-button>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 启动爬取对话框 -->
    <el-dialog
      v-model="startDialogVisible"
      title="启动爬取"
      width="500px"
    >
      <el-form :model="crawlForm" label-width="100px">
        <el-form-item label="目标平台">
          <el-select v-model="crawlForm.platform" style="width: 100%">
            <el-option
              v-for="platform in availablePlatforms"
              :key="platform.id"
              :label="platform.name"
              :value="platform.id"
              :disabled="platform.status === 'coming_soon'"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数据年份">
          <el-date-picker
            v-model="crawlForm.year"
            type="year"
            placeholder="选择年份"
            style="width: 100%"
            value-format="YYYY"
          />
        </el-form-item>
        <el-form-item label="爬取数量">
          <el-slider
            v-model="crawlForm.count"
            :min="10"
            :max="500"
            :step="10"
            show-input
          />
        </el-form-item>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-top: 10px"
        >
          <template #title>
            将生成 {{ crawlForm.count }} 条模拟凭证数据（含凭证附件图片）
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="startDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startCrawl" :loading="starting">
          开始爬取
        </el-button>
      </template>
    </el-dialog>

    <!-- Excel导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="Excel导入"
      width="550px"
    >
      <el-form label-width="100px">
        <el-form-item label="选择文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".xlsx,.xls,.csv"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将Excel文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 .xlsx, .xls, .csv 格式
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" link @click="downloadTemplate">
            <el-icon><Download /></el-icon>
            下载导入模板
          </el-button>
        </el-form-item>
        <el-alert
          type="warning"
          :closable="false"
          show-icon
        >
          <template #title>
            Excel需包含以下列：凭证号、凭证日期、金额（必填），科目代码、科目名称、摘要、交易对手（可选）
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="importExcel" :loading="importing" :disabled="!selectedFile">
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh, Upload, UploadFilled } from '@element-plus/icons-vue'
import { crawlerApi, projectApi } from '@/api'

// 项目选择
const projects = ref([])
const projectId = ref(localStorage.getItem('currentProjectId') || '')

// 平台列表
const platforms = ref([])

// 可用平台（排除开发中的）
const availablePlatforms = computed(() => {
  return platforms.value.filter(p => p.id !== 'excel_import')
})

// 任务列表
const tasks = ref([])
const loading = ref(false)

// 启动对话框
const startDialogVisible = ref(false)
const starting = ref(false)
const crawlForm = ref({
  platform: 'mock_platform',
  year: '2024',
  count: 100
})

// Excel导入
const importDialogVisible = ref(false)
const importing = ref(false)
const selectedFile = ref(null)
const uploadRef = ref(null)

// 轮询定时器
let pollingTimer = null

// 加载项目列表
const loadProjects = async () => {
  try {
    const res = await projectApi.getList({ page: 1, page_size: 100 })
    projects.value = res.items || []
  } catch (error) {
    console.error('加载项目列表失败:', error)
  }
}

// 加载平台列表
const loadPlatforms = async () => {
  try {
    platforms.value = await crawlerApi.getPlatforms()
  } catch (error) {
    console.error('加载平台列表失败:', error)
  }
}

// 加载任务列表
const loadTasks = async () => {
  if (!projectId.value) return

  loading.value = true
  try {
    tasks.value = await crawlerApi.getTasks(projectId.value)
  } catch (error) {
    console.error('加载任务列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 项目变更
const onProjectChange = (val) => {
  localStorage.setItem('currentProjectId', val)
  loadTasks()
}

// 显示启动对话框
const showStartDialog = () => {
  crawlForm.value = {
    platform: 'mock_platform',
    year: '2024',
    count: 100
  }
  startDialogVisible.value = true
}

// 显示导入对话框
const showImportDialog = () => {
  selectedFile.value = null
  importDialogVisible.value = true
}

// 启动爬取
const startCrawl = async () => {
  starting.value = true
  try {
    await crawlerApi.start({
      project_id: projectId.value,
      platform: crawlForm.value.platform,
      count: crawlForm.value.count,
      year: parseInt(crawlForm.value.year)
    })
    ElMessage.success('爬取任务已启动')
    startDialogVisible.value = false
    loadTasks()
  } catch (error) {
    ElMessage.error('启动失败: ' + (error.message || '未知错误'))
  } finally {
    starting.value = false
  }
}

// 文件选择变化
const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

// 超出限制
const handleExceed = () => {
  ElMessage.warning('只能上传一个文件')
}

// 下载模板
const downloadTemplate = async () => {
  try {
    const blob = await crawlerApi.downloadTemplate()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'voucher_import_template.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('下载模板失败')
  }
}

// Excel导入
const importExcel = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  importing.value = true
  try {
    const result = await crawlerApi.importExcel(projectId.value, selectedFile.value)
    ElMessage.success('导入任务已启动')
    importDialogVisible.value = false
    loadTasks()
  } catch (error) {
    ElMessage.error('导入失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    importing.value = false
  }
}

// 停止任务
const stopTask = async (taskId) => {
  try {
    await crawlerApi.stop(taskId)
    ElMessage.success('任务已停止')
    loadTasks()
  } catch (error) {
    ElMessage.error('停止失败: ' + (error.message || '未知错误'))
  }
}

// 获取平台名称
const getPlatformName = (platformId) => {
  const platform = platforms.value.find(p => p.id === platformId)
  return platform ? platform.name : platformId
}

// 获取状态类型
const getStatusType = (status) => {
  const types = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    stopped: 'info'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const texts = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止'
  }
  return texts[status] || status
}

// 计算进度
const getProgress = (row) => {
  if (!row.total_count) return row.success_count > 0 ? 100 : 0
  return Math.round((row.success_count / row.total_count) * 100)
}

// 获取进度条状态
const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return null
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

// 开始轮询
const startPolling = () => {
  pollingTimer = setInterval(() => {
    const hasRunning = tasks.value.some(t => t.status === 'running' || t.status === 'pending')
    if (hasRunning && projectId.value) {
      loadTasks()
    }
  }, 3000)
}

// 停止轮询
const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

onMounted(() => {
  loadProjects()
  loadPlatforms()
  loadTasks()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped lang="scss">
.crawler-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .page-title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.platform-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 20px;

  .platform-card {
    &.disabled {
      opacity: 0.6;
    }

    .platform-info {
      display: flex;
      gap: 16px;

      .platform-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 60px;
        height: 60px;
        background: var(--el-fill-color-light);
        border-radius: 8px;
        color: var(--el-color-primary);
      }

      .platform-details {
        flex: 1;

        h3 {
          margin: 0 0 8px 0;
          font-size: 16px;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        p {
          margin: 0 0 8px 0;
          font-size: 13px;
          color: var(--el-text-color-secondary);
        }
      }
    }
  }
}

.task-list-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.progress-cell {
  .progress-text {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 4px;
    display: block;
  }
}

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