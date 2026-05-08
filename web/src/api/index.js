import request from '@/utils/request'

// 项目管理API
export const projectApi = {
  // 获取项目列表
  getList(params) {
    return request.get('/projects', { params })
  },

  // 获取项目详情
  getDetail(id) {
    return request.get(`/projects/${id}`)
  },

  // 创建项目
  create(data) {
    return request.post('/projects', data)
  },

  // 更新项目
  update(id, data) {
    return request.put(`/projects/${id}`, data)
  },

  // 删除项目
  delete(id) {
    return request.delete(`/projects/${id}`)
  }
}

// 凭证管理API
export const voucherApi = {
  // 获取凭证列表
  getList(projectId, params) {
    return request.get(`/projects/${projectId}/vouchers`, { params })
  },

  // 获取总体统计（用于抽样向导）
  getPopulationStats(projectId, params) {
    return request.get(`/projects/${projectId}/vouchers/population-stats`, { params })
  },

  // 获取凭证详情
  getDetail(projectId, voucherId) {
    return request.get(`/projects/${projectId}/vouchers/${voucherId}`)
  },

  // 更新凭证
  update(projectId, voucherId, data) {
    return request.put(`/projects/${projectId}/vouchers/${voucherId}`, data)
  },

  // 导入凭证
  import(projectId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`/projects/${projectId}/vouchers/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 上传附件（单个）
  uploadAttachment(projectId, voucherId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`/projects/${projectId}/vouchers/${voucherId}/attachment`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 获取附件列表
  getAttachments(projectId, voucherId) {
    return request.get(`/projects/${projectId}/vouchers/${voucherId}/attachments`)
  },

  // 批量上传附件
  uploadAttachments(projectId, voucherId, files) {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return request.post(`/projects/${projectId}/vouchers/${voucherId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 删除附件
  deleteAttachment(projectId, voucherId, attachmentId) {
    return request.delete(`/projects/${projectId}/vouchers/${voucherId}/attachments/${attachmentId}`)
  },

  // 删除凭证
  delete(projectId, voucherId) {
    return request.delete(`/projects/${projectId}/vouchers/${voucherId}`)
  },

  // 批量删除凭证
  batchDelete(projectId, voucherIds) {
    return request.post(`/projects/${projectId}/vouchers/batch-delete`, {
      voucher_ids: voucherIds
    })
  },

  // OCR识别
  ocr(projectId, voucherId) {
    return request.post(`/projects/${projectId}/vouchers/${voucherId}/ocr`)
  },

  // 获取OCR结果
  getOcrResult(projectId, voucherId) {
    return request.get(`/projects/${projectId}/vouchers/${voucherId}/ocr`)
  },

  // AI识别
  aiRecognize(projectId, voucherId) {
    return request.post(`/projects/${projectId}/vouchers/${voucherId}/ai-recognize`)
  },

  // 附件AI识别
  recognizeAttachment(projectId, voucherId, attachmentId) {
    return request.post(`/projects/${projectId}/vouchers/${voucherId}/attachments/${attachmentId}/recognize`)
  },

  // 获取附件识别结果
  getAttachmentRecognitionResult(projectId, voucherId, attachmentId) {
    return request.get(`/projects/${projectId}/vouchers/${voucherId}/attachments/${attachmentId}/recognition-result`)
  }
}

// 抽样API
export const samplingApi = {
  // 获取规则列表
  getRules(projectId) {
    return request.get(`/projects/${projectId}/sampling-rules`)
  },

  // 创建规则
  createRule(projectId, data) {
    return request.post(`/projects/${projectId}/sampling-rules`, data)
  },

  // 更新规则
  updateRule(projectId, ruleId, data) {
    return request.put(`/projects/${projectId}/sampling-rules/${ruleId}`, data)
  },

  // 删除规则
  deleteRule(projectId, ruleId) {
    return request.delete(`/projects/${projectId}/sampling-rules/${ruleId}`)
  },

  // 执行抽样
  execute(projectId, data) {
    return request.post(`/projects/${projectId}/sampling/execute`, data)
  },

  // 获取抽样记录列表
  getRecords(projectId) {
    return request.get(`/projects/${projectId}/sampling-records`)
  },

  // 获取抽样记录详情
  getRecordDetail(projectId, recordId) {
    return request.get(`/projects/${projectId}/sampling-records/${recordId}`)
  },

  // 删除抽样记录
  deleteRecord(projectId, recordId) {
    return request.delete(`/projects/${projectId}/sampling-records/${recordId}`)
  },

  // 导出抽样记录
  exportRecord(projectId, recordId, format = 'excel') {
    return request.post(`/projects/${projectId}/sampling-records/${recordId}/export`, null, {
      params: { format },
      responseType: 'blob'
    })
  },

  // 获取抽样结果
  getResults(projectId, params) {
    return request.get(`/projects/${projectId}/samples`, { params })
  },

  // 导出抽样结果
  export(projectId, params) {
    return request.get(`/projects/${projectId}/samples/export`, {
      params,
      responseType: 'blob'
    })
  },

  // 预览分层抽样
  previewStratified(projectId, data) {
    return request.post(`/projects/${projectId}/sampling/stratified-preview`, data)
  },

  // MUS抽样预览
  previewMUS(projectId, data) {
    return request.post(`/projects/${projectId}/sampling/mus-preview`, data)
  },

  // 执行MUS抽样
  executeMUS(projectId, data) {
    return request.post(`/projects/${projectId}/sampling/mus-execute`, data)
  },

  // 系统抽样预览
  previewSystematic(projectId, data) {
    return request.post(`/projects/${projectId}/sampling/systematic-preview`, data)
  },

  // 执行系统抽样
  executeSystematic(projectId, data) {
    return request.post(`/projects/${projectId}/sampling/systematic-execute`, data)
  },

  // 执行样本测试
  executeTest(projectId, data) {
    return request.post(`/projects/${projectId}/samples/test`, data)
  },

  // 获取样本详情
  getSampleDetail(projectId, sampleId) {
    return request.get(`/projects/${projectId}/samples/${sampleId}`)
  },

  // 获取测试统计
  getTestStatistics(projectId, recordId = null) {
    return request.get(`/projects/${projectId}/test-statistics`, {
      params: { record_id: recordId }
    })
  },

  // 创建错报记录
  createMisstatement(projectId, data) {
    return request.post(`/projects/${projectId}/misstatements`, data)
  },

  // 获取错报列表
  getMisstatements(projectId, sampleId = null) {
    return request.get(`/projects/${projectId}/misstatements`, {
      params: { sample_id: sampleId }
    })
  },

  // 上传错报证据
  uploadMisstatementEvidence(projectId, misstatementId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`/projects/${projectId}/misstatements/${misstatementId}/evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 人工修正判定
  manualOverride(projectId, sampleId, data) {
    return request.put(`/projects/${projectId}/samples/${sampleId}/override`, data)
  },

  // 执行总体推断
  executeInference(projectId, data) {
    return request.post(`/projects/${projectId}/inference`, data)
  },

  // 获取推断结果
  getInferenceResult(projectId, inferenceId) {
    return request.get(`/projects/${projectId}/inference/${inferenceId}`)
  },

  // 获取推断摘要列表
  getInferenceSummaries(projectId) {
    return request.get(`/projects/${projectId}/inference-summary`)
  },

  // 计算样本量
  calculateSampleSize(projectId, data) {
    return request.post(`/projects/${projectId}/sample-size`, data)
  },

  // 获取总体统计信息
  getPopulationStats(projectId, subjectCode = null) {
    return request.get(`/projects/${projectId}/population-stats`, {
      params: { subject_code: subjectCode }
    })
  },

  // 获取抽样策略推荐
  getStrategyRecommend(projectId, subjectCode = null, params = {}) {
    const queryParams = { ...params }
    if (subjectCode) {
      queryParams.subject_code = subjectCode
    }
    return request.get(`/projects/${projectId}/strategy/recommend`, {
      params: queryParams
    })
  }
}

// 风险画像API
export const riskApi = {
  // ========== 项目风险概览 ==========
  // 获取项目风险概览
  getOverview(projectId) {
    return request.get(`/projects/${projectId}/risk/overview`)
  },

  // 生成项目风险概览
  generateOverview(projectId) {
    return request.post(`/projects/${projectId}/risk/overview/generate`, null, {
      timeout: 300000  // 5分钟超时
    })
  },

  // 获取风险趋势
  getTrend(projectId, periods = 6) {
    return request.get(`/projects/${projectId}/risk/trend`, { params: { periods } })
  },

  // ========== 多维风险分析 ==========
  // 获取交易对手风险分析
  getCounterpartyAnalysis(projectId) {
    return request.get(`/projects/${projectId}/risk/dimensions/counterparty`)
  },

  // 获取时间维度风险分析
  getTimeAnalysis(projectId, periodType = 'monthly') {
    return request.get(`/projects/${projectId}/risk/dimensions/time`, { params: { period_type: periodType } })
  },

  // 获取文档完整性分析
  getDocumentAnalysis(projectId) {
    return request.get(`/projects/${projectId}/risk/dimensions/document`)
  },

  // ========== 交易风险清单 ==========
  // 获取交易风险清单
  getTransactionList(projectId, params) {
    return request.get(`/projects/${projectId}/risk/transactions`, { params })
  },

  // 获取交易风险详情
  getTransactionDetail(projectId, voucherId) {
    return request.get(`/projects/${projectId}/risk/transactions/${voucherId}`)
  },

  // 批量加入抽样
  batchAddToSampling(projectId, voucherIds, reason = '风险画像批量添加') {
    return request.post(`/projects/${projectId}/risk/transactions/batch-add-sampling`, {
      voucher_ids: voucherIds,
      reason
    })
  },

  // ========== 风险标签 ==========
  // 获取风险标签统计
  getTagStatistics(projectId) {
    return request.get(`/projects/${projectId}/risk/tags`)
  },

  // 获取凭证风险标签
  getVoucherTags(projectId, voucherId) {
    return request.get(`/projects/${projectId}/risk/tags/by-voucher/${voucherId}`)
  },

  // ========== 高风险科目 ==========
  getHighRiskSubjects(projectId, limit = 5) {
    return request.get(`/projects/${projectId}/risk/high-risk-subjects`, { params: { limit } })
  },

  // ========== 科目风险画像 ==========
  // 获取所有科目风险画像
  getSubjects(projectId) {
    return request.get(`/projects/${projectId}/risk/subjects`)
  },

  // 生成科目风险画像
  generateSubjects(projectId, useAi = true) {
    return request.post(`/projects/${projectId}/risk/subjects/generate`, null, {
      params: { use_ai: useAi },
      timeout: 300000  // 5分钟超时，AI分析需要较长时间
    })
  },

  // 获取科目风险画像详情
  getSubjectDetail(projectId, subjectCode) {
    return request.get(`/projects/${projectId}/risk/subjects/${subjectCode}`)
  },

  // ========== 分层抽样建议 ==========
  getLayeredSampling(projectId, highRatio = 1.0, mediumRatio = 0.3, lowRatio = 0.05) {
    return request.get(`/projects/${projectId}/risk/layered-sampling`, {
      params: {
        high_ratio: highRatio,
        medium_ratio: mediumRatio,
        low_ratio: lowRatio
      }
    })
  },

  // 执行风险分层抽样
  executeLayeredSampling(projectId, highRatio = 1.0, mediumRatio = 0.3, lowRatio = 0.05, useAi = false) {
    return request.post(`/projects/${projectId}/risk/execute-layered-sampling`, {
      high_ratio: highRatio,
      medium_ratio: mediumRatio,
      low_ratio: lowRatio,
      use_ai: useAi
    })
  },

  // ========== 风险配置 ==========
  // 获取权重配置
  getWeights(projectId) {
    return request.get(`/projects/${projectId}/risk/config/weights`)
  },

  // 更新权重配置
  updateWeights(projectId, weights) {
    return request.put(`/projects/${projectId}/risk/config/weights`, { weights })
  },

  // 获取阈值配置
  getThresholds(projectId) {
    return request.get(`/projects/${projectId}/risk/config/thresholds`)
  },

  // 更新阈值配置
  updateThresholds(projectId, thresholds) {
    return request.put(`/projects/${projectId}/risk/config/thresholds`, { thresholds })
  },

  // 获取规则列表
  getRules(projectId) {
    return request.get(`/projects/${projectId}/risk/config/rules`)
  },

  // 切换规则开关
  toggleRule(projectId, ruleCode, enabled) {
    return request.put(`/projects/${projectId}/risk/config/rules/${ruleCode}`, { enabled })
  },

  // 获取配置模板列表
  getTemplates(projectId) {
    return request.get(`/projects/${projectId}/risk/config/templates`)
  },

  // 保存配置模板
  saveTemplate(projectId, templateName) {
    return request.post(`/projects/${projectId}/risk/config/templates/save`, { template_name: templateName })
  },

  // 加载配置模板
  loadTemplate(projectId, templateName) {
    return request.post(`/projects/${projectId}/risk/config/templates/load`, { template_name: templateName })
  },

  // 删除配置模板
  deleteTemplate(projectId, templateName) {
    return request.delete(`/projects/${projectId}/risk/config/templates/${templateName}`)
  },

  // 获取完整配置
  getFullConfig(projectId) {
    return request.get(`/projects/${projectId}/risk/config/full`)
  },

  // 重置为默认配置
  resetConfig(projectId) {
    return request.post(`/projects/${projectId}/risk/config/reset`)
  },

  // ========== 兼容旧API ==========
  // 生成风险画像（兼容旧版本）
  generate(projectId, data) {
    return request.post(`/projects/${projectId}/risk/subjects/generate`)
  },

  // 获取风险画像（兼容旧版本）
  get(projectId) {
    return request.get(`/projects/${projectId}/risk/subjects`)
  }
}

// AI服务API
export const aiApi = {
  // 获取模型列表
  getModels() {
    return request.get('/ai/models')
  },

  // 获取服务状态
  getStatus() {
    return request.get('/ai/status')
  },

  // 更新配置
  updateConfig(data) {
    return request.put('/ai/config', data)
  },

  // 获取用途配置
  getPurposeConfigs() {
    return request.get('/ai/config/purposes')
  },

  // 更新用途配置
  updatePurposeConfigs(data) {
    return request.put('/ai/config/purposes', data)
  },

  // 分析凭证
  analyze(data) {
    return request.post('/ai/analyze', data, { timeout: 300000 }) // 5分钟超时
  },

  // 智能抽样 - 需要较长超时时间
  intelligentSample(data) {
    return request.post('/ai/intelligent-sample', data, { timeout: 180000 })
  },

  // 理解凭证
  describeVoucher(data) {
    return request.post('/ai/describe-voucher', data)
  },

  // 语义搜索
  semanticSearch(data) {
    return request.post('/ai/semantic-search', data)
  },

  // 测试用途模型
  testPurposeModel(data) {
    return request.post('/ai/test-purpose-model', data, { timeout: 30000 })
  },

  // ========== 用量统计API ==========
  // 获取用量统计汇总
  getUsageSummary(params) {
    return request.get('/ai/usage/summary', { params })
  },

  // 获取每日用量
  getDailyUsage(params) {
    return request.get('/ai/usage/daily', { params })
  },

  // ========== 调用日志API ==========
  // 获取调用日志列表
  getLogs(params) {
    return request.get('/ai/logs', { params })
  },

  // 获取单条日志详情
  getLogDetail(logId) {
    return request.get(`/ai/logs/${logId}`)
  },

  // ========== 供应商管理API ==========
  // 获取供应商列表
  getProviders() {
    return request.get('/ai/providers')
  },

  // ========== Playground测试API ==========
  // Playground模型测试
  testModel(data) {
    return request.post('/ai/test-model', data, { timeout: 60000 })
  }
}

// 任务管理API
export const taskApi = {
  // 获取任务列表
  getList(projectId, params) {
    return request.get(`/projects/${projectId}/tasks`, { params })
  },

  // 获取任务详情
  getDetail(projectId, taskId) {
    return request.get(`/projects/${taskId}/tasks/${taskId}`)
  },

  // 创建任务
  create(projectId, data) {
    return request.post(`/projects/${projectId}/tasks`, data)
  },

  // 更新任务状态
  updateStatus(projectId, taskId, data) {
    return request.put(`/projects/${projectId}/tasks/${taskId}/status`, data)
  },

  // 自动分派
  autoAssign(projectId, data) {
    return request.post(`/projects/${projectId}/tasks/auto-assign`, data)
  },

  // 获取进度
  getProgress(projectId) {
    return request.get(`/projects/${projectId}/tasks/progress`)
  },

  // 获取团队成员
  getTeamMembers(projectId) {
    return request.get(`/projects/${projectId}/team-members`)
  },

  // 添加团队成员
  addTeamMember(projectId, data) {
    return request.post(`/projects/${projectId}/team-members`, data)
  }
}

// 底稿API
export const paperApi = {
  // 获取底稿列表
  getList(projectId, params) {
    return request.get(`/projects/${projectId}/papers`, { params })
  },

  // 获取底稿详情
  getDetail(projectId, paperId) {
    return request.get(`/projects/${projectId}/papers/${paperId}`)
  },

  // 生成底稿
  generate(projectId, data) {
    return request.post(`/projects/${projectId}/papers/generate`, data)
  },

  // 导出底稿
  export(projectId, paperId, format) {
    return request.get(`/projects/${projectId}/papers/${paperId}/export`, {
      params: { format },
      responseType: 'blob'
    })
  },

  // 获取底稿类型
  getTypes() {
    return request.get('/paper-types')
  },

  // 删除底稿
  delete(projectId, paperId) {
    return request.delete(`/projects/${projectId}/papers/${paperId}`)
  }
}

// 审计轨迹API
export const auditTrailApi = {
  // 查询轨迹
  query(projectId, params) {
    return request.get(`/projects/${projectId}/audit-trail`, { params })
  },

  // 获取统计
  getStatistics(projectId, params) {
    return request.get(`/projects/${projectId}/audit-trail/statistics`, { params })
  },

  // 获取样本轨迹
  getSampleTrail(projectId, sampleId) {
    return request.get(`/projects/${projectId}/audit-trail/samples/${sampleId}`)
  },

  // 导出轨迹
  export(projectId, params) {
    return request.get(`/projects/${projectId}/audit-trail/export`, { params })
  }
}

// 认证API
export const authApi = {
  // 登录
  login(data) {
    return request.post('/auth/login', data)
  },

  // 注册
  register(data) {
    return request.post('/auth/register', data)
  },

  // 获取当前用户
  getCurrentUser() {
    return request.get('/auth/me')
  }
}

// 爬虫API
export const crawlerApi = {
  // 获取平台列表
  getPlatforms() {
    return request.get('/crawler/platforms')
  },

  // 启动爬虫
  start(data) {
    return request.post('/crawler/start', data)
  },

  // 获取任务状态
  getStatus(taskId) {
    return request.get(`/crawler/status/${taskId}`)
  },

  // 停止任务
  stop(taskId) {
    return request.post('/crawler/stop', null, {
      params: { task_id: taskId }
    })
  },

  // 获取项目任务列表
  getTasks(projectId) {
    return request.get(`/crawler/tasks/${projectId}`)
  }
}

// 合规检查API
export const complianceApi = {
  // 获取规则列表
  getRules(projectId) {
    return request.get(`/projects/${projectId}/compliance/rules`)
  },

  // 执行合规检查
  runCheck(projectId, ruleCodes = null) {
    return request.post(`/projects/${projectId}/compliance/check`, {
      rule_codes: ruleCodes
    })
  },

  // 获取预警列表
  getAlerts(projectId, params = {}) {
    return request.get(`/projects/${projectId}/compliance/alerts`, { params })
  },

  // 处理预警
  resolveAlert(projectId, alertId) {
    return request.put(`/projects/${projectId}/compliance/alerts/${alertId}/resolve`)
  },

  // 获取统计
  getStatistics(projectId) {
    return request.get(`/projects/${projectId}/compliance/statistics`)
  }
}

// 三单匹配API
export const matchingApi = {
  // 执行匹配
  execute(projectId, params = {}) {
    return request.post(`/projects/${projectId}/matching/execute`, null, { params })
  },

  // 获取匹配结果
  getResults(projectId, status = null) {
    return request.get(`/projects/${projectId}/matching/results`, {
      params: { status }
    })
  },

  // 清空匹配结果
  clearResults(projectId) {
    return request.delete(`/projects/${projectId}/matching/results`)
  }
}