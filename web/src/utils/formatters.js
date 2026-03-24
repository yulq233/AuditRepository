/**
 * 共享格式化工具函数
 * 用于Web和移动端的统一格式化
 */

/**
 * 格式化金额
 * @param {number} amount 金额
 * @param {Object} options 选项
 * @returns {string} 格式化后的金额字符串
 */
export function formatAmount(amount, options = {}) {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '0.00'
  }
  const { prefix = '', suffix = '', decimals = 2 } = options
  const formatted = Number(amount).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
  return `${prefix}${formatted}${suffix}`
}

/**
 * 格式化日期
 * @param {string|Date} date 日期
 * @param {string} format 格式
 * @returns {string} 格式化后的日期字符串
 */
export function formatDate(date, format = 'YYYY-MM-DD HH:mm') {
  if (!date) return '-'

  const d = new Date(date)
  if (isNaN(d.getTime())) return '-'

  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')

  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 获取风险等级类型（用于Element Plus Tag）
 * @param {string} level 风险等级
 * @returns {string} 类型
 */
export function getRiskType(level) {
  const types = {
    high: 'danger',
    medium: 'warning',
    low: 'success'
  }
  return types[level] || 'info'
}

/**
 * 获取风险等级标签
 * @param {string} level 风险等级
 * @returns {string} 标签文本
 */
export function getRiskLabel(level) {
  const labels = {
    high: '高风险',
    medium: '中风险',
    low: '低风险'
  }
  return labels[level] || level
}

/**
 * 获取风险等级颜色
 * @param {string} level 风险等级
 * @returns {string} 颜色值
 */
export function getRiskColor(level) {
  const colors = {
    high: '#f56c6c',
    medium: '#e6a23c',
    low: '#67c23a'
  }
  return colors[level] || '#909399'
}

/**
 * 获取优先级类型
 * @param {string} priority 优先级
 * @returns {string} 类型
 */
export function getPriorityType(priority) {
  const types = {
    high: 'danger',
    medium: 'warning',
    low: 'info'
  }
  return types[priority] || 'info'
}

/**
 * 获取优先级标签
 * @param {string} priority 优先级
 * @returns {string} 标签文本
 */
export function getPriorityLabel(priority) {
  const labels = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return labels[priority] || '中'
}

/**
 * 获取项目状态类型
 * @param {string} status 状态
 * @returns {string} 类型
 */
export function getProjectStatusType(status) {
  const types = {
    active: 'success',
    completed: 'info',
    archived: 'warning'
  }
  return types[status] || 'info'
}

/**
 * 获取项目状态标签
 * @param {string} status 状态
 * @returns {string} 标签文本
 */
export function getProjectStatusLabel(status) {
  const labels = {
    active: '进行中',
    completed: '已完成',
    archived: '已归档'
  }
  return labels[status] || status
}

/**
 * 获取任务状态标签
 * @param {string} status 状态
 * @returns {string} 标签文本
 */
export function getTaskStatusLabel(status) {
  const labels = {
    pending: '待处理',
    assigned: '已分派',
    in_progress: '进行中',
    review: '待复核',
    completed: '已完成',
    blocked: '已阻塞',
    overdue: '已超期'
  }
  return labels[status] || status
}

/**
 * 获取匹配状态标签
 * @param {string} status 状态
 * @returns {string} 标签文本
 */
export function getMatchStatusLabel(status) {
  const labels = {
    fully_matched: '完全匹配',
    partially_matched: '部分匹配',
    not_matched: '未匹配',
    exception: '异常'
  }
  return labels[status] || status
}

/**
 * 获取匹配状态类型
 * @param {string} status 状态
 * @returns {string} 类型
 */
export function getMatchStatusType(status) {
  const types = {
    fully_matched: 'success',
    partially_matched: 'warning',
    not_matched: 'danger',
    exception: 'info'
  }
  return types[status] || 'info'
}

/**
 * 截断文本
 * @param {string} text 文本
 * @param {number} maxLength 最大长度
 * @returns {string} 截断后的文本
 */
export function truncate(text, maxLength = 50) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}