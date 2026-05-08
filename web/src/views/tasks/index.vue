<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">任务管理</h2>
      <el-button type="primary" @click="showAssignDialog = true">
        <el-icon><Plus /></el-icon>
        分派任务
      </el-button>
    </div>

    <el-card class="card-container">
      <el-table :data="tasks" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="任务名称" min-width="200" />
        <el-table-column prop="assignee_name" label="负责人" width="120">
          <template #default="{ row }">
            {{ row.assignee_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.priority === 'high' ? 'blocked' : row.priority]">
              {{ getPriorityLabel(row.priority) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止时间" width="180">
          <template #default="{ row }">
            {{ row.deadline ? formatDate(row.deadline) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.status]">
              {{ getTaskStatusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.progress || 0" :stroke-width="8" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewTask(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showAssignDialog" title="分派任务" width="500px">
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="任务名称" required>
          <el-input v-model="taskForm.title" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="taskForm.assignee_id" style="width: 100%" placeholder="选择负责人">
            <el-option v-for="m in teamMembers" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-radio-group v-model="taskForm.priority">
            <el-radio label="high">高</el-radio>
            <el-radio label="medium">中</el-radio>
            <el-radio label="low">低</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker v-model="taskForm.deadline" type="datetime" style="width: 100%" placeholder="选择截止时间" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="taskForm.notes" type="textarea" rows="3" placeholder="任务说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAssignDialog = false">取消</el-button>
        <el-button type="primary" @click="assignTask" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showTaskDetail" title="任务详情" width="600px">
      <el-descriptions :column="2" border v-if="currentTask">
        <el-descriptions-item label="任务名称" :span="2">{{ currentTask.title }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ currentTask.assignee_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ getPriorityLabel(currentTask.priority) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ getTaskStatusLabel(currentTask.status) }}</el-descriptions-item>
        <el-descriptions-item label="进度">
          <el-progress :percentage="currentTask.progress || 0" />
        </el-descriptions-item>
        <el-descriptions-item label="截止时间">{{ currentTask.deadline ? formatDate(currentTask.deadline) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(currentTask.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="showTaskDetail = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { formatDate, getPriorityLabel, getTaskStatusLabel } from '@/utils/formatters'
import { projectApi, taskApi } from '@/api'
import { useRoute } from 'vue-router'

const route = useRoute()
const projectId = computed(() => route.params.projectId || localStorage.getItem('currentProjectId'))

const loading = ref(false)
const submitting = ref(false)
const tasks = ref([])
const teamMembers = ref([])
const showAssignDialog = ref(false)
const showTaskDetail = ref(false)
const currentTask = ref(null)

const taskForm = reactive({
  title: '',
  assignee_id: '',
  priority: 'medium',
  deadline: null,
  notes: ''
})

const loadTasks = async () => {
  if (!projectId.value) return

  loading.value = true
  try {
    const res = await taskApi.getList(projectId.value)
    tasks.value = res.items || []
  } catch (e) {
    console.error('加载任务列表失败:', e)
  } finally {
    loading.value = false
  }
}

const loadTeamMembers = async () => {
  if (!projectId.value) return

  try {
    const res = await taskApi.getTeamMembers(projectId.value)
    teamMembers.value = res || []
  } catch (e) {
    console.error('加载团队成员失败:', e)
  }
}

const viewTask = (row) => {
  currentTask.value = row
  showTaskDetail.value = true
}

const assignTask = async () => {
  if (!taskForm.title) {
    ElMessage.warning('请输入任务名称')
    return
  }

  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  submitting.value = true
  try {
    await taskApi.create(projectId.value, {
      title: taskForm.title,
      assignee_id: taskForm.assignee_id,
      priority: taskForm.priority,
      deadline: taskForm.deadline,
      notes: taskForm.notes,
      sample_ids: []
    })
    ElMessage.success('任务创建成功')
    showAssignDialog.value = false
    resetForm()
    loadTasks()
  } catch (e) {
    ElMessage.error('创建任务失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  taskForm.title = ''
  taskForm.assignee_id = ''
  taskForm.priority = 'medium'
  taskForm.deadline = null
  taskForm.notes = ''
}

onMounted(() => {
  loadTasks()
  loadTeamMembers()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

.status-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;

  &.high, &.blocked {
    background: #fef0f0;
    color: #f56c6c;
  }

  &.medium {
    background: #fdf6ec;
    color: #e6a23c;
  }

  &.low {
    background: #f0f9eb;
    color: #67c23a;
  }

  &.pending {
    background: #f4f4f5;
    color: #909399;
  }

  &.in_progress {
    background: #ecf5ff;
    color: #409eff;
  }

  &.completed {
    background: #f0f9eb;
    color: #67c23a;
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