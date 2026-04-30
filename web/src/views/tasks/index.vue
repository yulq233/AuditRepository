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
        <el-table-column prop="assignee_name" label="负责人" width="120" />
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
        <el-form-item label="任务名称">
          <el-input v-model="taskForm.title" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="taskForm.assignee" style="width: 100%">
            <el-option label="张三" value="1" />
            <el-option label="李四" value="2" />
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
          <el-date-picker v-model="taskForm.deadline" type="datetime" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAssignDialog = false">取消</el-button>
        <el-button type="primary" @click="assignTask">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { formatDate, getPriorityLabel, getTaskStatusLabel } from '@/utils/formatters'

const loading = ref(false)
const tasks = ref([])
const showAssignDialog = ref(false)

const taskForm = reactive({
  title: '',
  assignee: '',
  priority: 'medium',
  deadline: null
})

const viewTask = (row) => {
  // TODO: 查看任务详情
}

const assignTask = async () => {
  // TODO: 分派任务
  showAssignDialog.value = false
}

onMounted(() => {
  // TODO: 加载任务列表
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