/**
 * 移动端API请求模块
 */

// API基础配置
const BASE_URL = 'http://localhost:9000/api'

// Token管理
let token = null

export function setToken(t) {
  token = t
  uni.setStorageSync('token', t)
}

export function getToken() {
  if (!token) {
    token = uni.getStorageSync('token')
  }
  return token
}

export function clearToken() {
  token = null
  uni.removeStorageSync('token')
}

/**
 * 通用请求方法
 */
function request(options) {
  return new Promise((resolve, reject) => {
    const t = getToken()
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        'Authorization': t ? `Bearer ${t}` : '',
        ...options.header
      },
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // Token过期，跳转登录
          clearToken()
          uni.navigateTo({ url: '/pages/login/login' })
          reject(new Error('未登录或登录已过期'))
        } else {
          reject(new Error(res.data?.detail || '请求失败'))
        }
      },
      fail: (err) => {
        reject(new Error(err.errMsg || '网络错误'))
      }
    })
  })
}

// ==================== 认证API ====================
export const authApi = {
  login(data) {
    return request({
      url: '/auth/login',
      method: 'POST',
      data
    }).then(res => {
      if (res.access_token) {
        setToken(res.access_token)
      }
      return res
    })
  },

  register(data) {
    return request({
      url: '/auth/register',
      method: 'POST',
      data
    })
  },

  getCurrentUser() {
    return request({ url: '/auth/me' })
  }
}

// ==================== 项目API ====================
export const projectApi = {
  getList(params = {}) {
    const query = new URLSearchParams(params).toString()
    return request({ url: `/projects?${query}` })
  },

  getDetail(id) {
    return request({ url: `/projects/${id}` })
  },

  create(data) {
    return request({
      url: '/projects',
      method: 'POST',
      data
    })
  },

  update(id, data) {
    return request({
      url: `/projects/${id}`,
      method: 'PUT',
      data
    })
  },

  delete(id) {
    return request({
      url: `/projects/${id}`,
      method: 'DELETE'
    })
  }
}

// ==================== 凭证API ====================
export const voucherApi = {
  getList(projectId, params = {}) {
    const query = new URLSearchParams(params).toString()
    return request({ url: `/projects/${projectId}/vouchers?${query}` })
  },

  getDetail(projectId, voucherId) {
    return request({ url: `/projects/${projectId}/vouchers/${voucherId}` })
  },

  getPopulationStats(projectId) {
    return request({ url: `/projects/${projectId}/vouchers/population-stats` })
  }
}

// ==================== 抽样API ====================
export const samplingApi = {
  getRules(projectId) {
    return request({ url: `/projects/${projectId}/sampling-rules` })
  },

  createRule(projectId, data) {
    return request({
      url: `/projects/${projectId}/sampling-rules`,
      method: 'POST',
      data
    })
  },

  execute(projectId, data) {
    return request({
      url: `/projects/${projectId}/sampling/execute`,
      method: 'POST',
      data
    })
  },

  getRecords(projectId) {
    return request({ url: `/projects/${projectId}/sampling-records` })
  },

  getRecordDetail(projectId, recordId) {
    return request({ url: `/projects/${projectId}/sampling-records/${recordId}` })
  }
}

// ==================== 风险画像API ====================
export const riskApi = {
  getOverview(projectId) {
    return request({ url: `/projects/${projectId}/risk/overview` })
  },

  getSubjects(projectId) {
    return request({ url: `/projects/${projectId}/risk/subjects` })
  },

  generateSubjects(projectId) {
    return request({
      url: `/projects/${projectId}/risk/subjects/generate`,
      method: 'POST'
    })
  }
}

// ==================== 任务API ====================
export const taskApi = {
  getList(projectId, params = {}) {
    const query = new URLSearchParams(params).toString()
    return request({ url: `/projects/${projectId}/tasks?${query}` })
  },

  getProgress(projectId) {
    return request({ url: `/projects/${projectId}/tasks/progress` })
  },

  updateStatus(projectId, taskId, data) {
    return request({
      url: `/projects/${projectId}/tasks/${taskId}/status`,
      method: 'PUT',
      data
    })
  }
}

// ==================== 底稿API ====================
export const paperApi = {
  getList(projectId) {
    return request({ url: `/projects/${projectId}/papers` })
  },

  getDetail(projectId, paperId) {
    return request({ url: `/projects/${projectId}/papers/${paperId}` })
  }
}

// ==================== AI API ====================
export const aiApi = {
  getStatus() {
    return request({ url: '/ai/status' })
  },

  intelligentSample(projectId, data) {
    return request({
      url: '/ai/intelligent-sample',
      method: 'POST',
      data: { project_id: projectId, ...data }
    })
  }
}

export default {
  setToken,
  getToken,
  clearToken,
  authApi,
  projectApi,
  voucherApi,
  samplingApi,
  riskApi,
  taskApi,
  paperApi,
  aiApi
}
