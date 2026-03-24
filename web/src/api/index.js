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

  // 获取凭证详情
  getDetail(projectId, voucherId) {
    return request.get(`/projects/${projectId}/vouchers/${voucherId}`)
  },

  // 导入凭证
  import(projectId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`/projects/${projectId}/vouchers/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 上传附件
  uploadAttachment(projectId, voucherId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`/projects/${projectId}/vouchers/${voucherId}/attachment`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // OCR识别
  ocr(projectId, voucherId) {
    return request.post(`/projects/${projectId}/vouchers/${voucherId}/ocr`)
  },

  // 获取OCR结果
  getOcrResult(projectId, voucherId) {
    return request.get(`/projects/${projectId}/vouchers/${voucherId}/ocr`)
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

  // 执行抽样
  execute(projectId, data) {
    return request.post(`/projects/${projectId}/sampling/execute`, data)
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
  }
}

// 风险画像API
export const riskApi = {
  // 生成风险画像
  generate(projectId, data) {
    return request.post(`/projects/${projectId}/risk-profile/generate`, data)
  },

  // 获取风险画像
  get(projectId) {
    return request.get(`/projects/${projectId}/risk-profile`)
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

  // 分析凭证
  analyze(data) {
    return request.post('/ai/analyze', data)
  },

  // 智能抽样
  intelligentSample(data) {
    return request.post('/ai/intelligent-sample', data)
  },

  // 理解凭证
  describeVoucher(data) {
    return request.post('/ai/describe-voucher', data)
  },

  // 语义搜索
  semanticSearch(data) {
    return request.post('/ai/semantic-search', data)
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