<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">执行抽样</h2>
    </div>

    <el-row :gutter="20">
      <!-- 规则配置 -->
      <el-col :span="8">
        <el-card class="card-container">
          <template #header>抽样规则</template>
          <el-form :model="ruleForm" label-width="100px">
            <el-form-item label="规则名称">
              <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
            </el-form-item>
            <el-form-item label="规则类型">
              <el-select v-model="ruleForm.rule_type" @change="onRuleTypeChange">
                <el-option label="随机抽样" value="random" />
                <el-option label="金额抽样" value="amount" />
                <el-option label="科目抽样" value="subject" />
                <el-option label="日期范围" value="date" />
              </el-select>
            </el-form-item>

            <!-- 随机抽样配置 -->
            <template v-if="ruleForm.rule_type === 'random'">
              <el-form-item label="抽样比例">
                <el-input-number v-model="ruleForm.rule_config.percentage" :min="1" :max="100" />
                <span style="margin-left: 5px">%</span>
              </el-form-item>
              <el-form-item label="样本数量">
                <el-input-number v-model="ruleForm.rule_config.sample_size" :min="1" />
              </el-form-item>
            </template>

            <!-- 金额抽样配置 -->
            <template v-if="ruleForm.rule_type === 'amount'">
              <el-form-item label="最小金额">
                <el-input-number v-model="ruleForm.rule_config.min_amount" :min="0" />
              </el-form-item>
              <el-form-item label="最大金额">
                <el-input-number v-model="ruleForm.rule_config.max_amount" />
              </el-form-item>
              <el-form-item label="抽样比例">
                <el-input-number v-model="ruleForm.rule_config.percentage" :min="1" :max="100" />
                <span style="margin-left: 5px">%</span>
              </el-form-item>
            </template>

            <!-- 科目抽样配置 -->
            <template v-if="ruleForm.rule_type === 'subject'">
              <el-form-item label="科目代码">
                <el-select v-model="ruleForm.rule_config.subject_codes" multiple filterable placeholder="选择科目">
                  <el-option v-for="subject in subjectOptions" :key="subject.code" :label="subject.name" :value="subject.code" />
                </el-select>
              </el-form-item>
            </template>

            <!-- 日期抽样配置 -->
            <template v-if="ruleForm.rule_type === 'date'">
              <el-form-item label="开始日期">
                <el-date-picker v-model="ruleForm.rule_config.start_date" type="date" placeholder="选择日期" />
              </el-form-item>
              <el-form-item label="结束日期">
                <el-date-picker v-model="ruleForm.rule_config.end_date" type="date" placeholder="选择日期" />
              </el-form-item>
            </template>

            <el-form-item>
              <el-button type="primary" @click="executeSampling" :loading="executing">
                执行抽样
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 已有规则 -->
      <el-col :span="16">
        <el-card class="card-container">
          <template #header>已保存规则</template>
          <el-table :data="rules" style="width: 100%">
            <el-table-column prop="name" label="规则名称" min-width="150" />
            <el-table-column prop="rule_type" label="类型" width="100">
              <template #default="{ row }">
                {{ getRuleTypeLabel(row.rule_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button type="primary" link @click="useRule(row)">使用</el-button>
                <el-button type="danger" link @click="deleteRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- AI智能抽样 -->
        <el-card class="card-container" style="margin-top: 20px">
          <template #header>
            <div style="display: flex; align-items: center">
              <el-icon color="#409eff" style="margin-right: 5px"><MagicStick /></el-icon>
              AI智能抽样
            </div>
          </template>
          <el-form :model="aiForm" label-width="100px">
            <el-form-item label="样本数量">
              <el-input-number v-model="aiForm.sample_size" :min="10" :max="500" />
            </el-form-item>
            <el-form-item label="重点关注">
              <el-checkbox-group v-model="aiForm.focus_areas">
                <el-checkbox label="大额交易">大额交易</el-checkbox>
                <el-checkbox label="异常日期">异常日期</el-checkbox>
                <el-checkbox label="关联方">关联方</el-checkbox>
                <el-checkbox label="跨期调整">跨期调整</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="aiSampling" :loading="aiExecuting">
                <el-icon><MagicStick /></el-icon>
                AI推荐抽样
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { samplingApi, aiApi } from '@/api'
import dayjs from 'dayjs'

const router = useRouter()
const executing = ref(false)
const aiExecuting = ref(false)

const projectId = ref(localStorage.getItem('currentProjectId') || '')

const ruleForm = reactive({
  name: '',
  rule_type: 'random',
  rule_config: {
    percentage: 10,
    sample_size: null,
    min_amount: null,
    max_amount: null,
    subject_codes: [],
    start_date: null,
    end_date: null
  }
})

const aiForm = reactive({
  sample_size: 50,
  focus_areas: []
})

const rules = ref([])
const subjectOptions = ref([])

const formatDate = (date) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'

const getRuleTypeLabel = (type) => {
  const labels = { random: '随机抽样', amount: '金额抽样', subject: '科目抽样', date: '日期范围' }
  return labels[type] || type
}

const onRuleTypeChange = () => {
  // 重置配置
  ruleForm.rule_config = {
    percentage: 10,
    sample_size: null,
    min_amount: null,
    max_amount: null,
    subject_codes: [],
    start_date: null,
    end_date: null
  }
}

const loadRules = async () => {
  if (!projectId.value) return
  try {
    rules.value = await samplingApi.getRules(projectId.value)
  } catch (error) {
    console.error(error)
  }
}

const executeSampling = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  if (!ruleForm.name) {
    ElMessage.warning('请输入规则名称')
    return
  }

  executing.value = true
  try {
    // 创建规则
    const rule = await samplingApi.createRule(projectId.value, {
      name: ruleForm.name,
      rule_type: ruleForm.rule_type,
      rule_config: ruleForm.rule_config
    })

    // 执行抽样
    await samplingApi.execute(projectId.value, {
      rule_id: rule.id,
      sample_size: ruleForm.rule_config.sample_size
    })

    ElMessage.success('抽样执行成功')
    router.push('/sampling/results')
  } catch (error) {
    console.error(error)
  } finally {
    executing.value = false
  }
}

const useRule = async (rule) => {
  executing.value = true
  try {
    await samplingApi.execute(projectId.value, { rule_id: rule.id })
    ElMessage.success('抽样执行成功')
    router.push('/sampling/results')
  } catch (error) {
    console.error(error)
  } finally {
    executing.value = false
  }
}

const deleteRule = async (rule) => {
  try {
    await ElMessageBox.confirm('确定要删除该规则吗？', '提示', { type: 'warning' })
    // TODO: 实现删除规则API
    loadRules()
  } catch (error) {
    // 取消删除
  }
}

const aiSampling = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  aiExecuting.value = true
  try {
    await aiApi.intelligentSample({
      project_id: projectId.value,
      sample_size: aiForm.sample_size,
      focus_areas: aiForm.focus_areas.length > 0 ? aiForm.focus_areas : null
    })
    ElMessage.success('AI智能抽样完成')
    router.push('/sampling/results')
  } catch (error) {
    console.error(error)
  } finally {
    aiExecuting.value = false
  }
}

onMounted(() => {
  loadRules()
})
</script>