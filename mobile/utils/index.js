/**
 * 移动端共享工具函数
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
export function formatDate(date, format = 'YYYY-MM-DD') {
  if (!date) return '-'

  const d = new Date(date)
  if (isNaN(d.getTime())) return '-'

  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')

  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
}

/**
 * 获取状态文本
 * @param {string} status 状态
 * @returns {string} 状态文本
 */
export function getStatusText(status) {
  const map = {
    active: '进行中',
    completed: '已完成',
    archived: '已归档',
    pending: '待处理',
    in_progress: '进行中',
    review: '待复核',
    blocked: '已阻塞',
    overdue: '已超期'
  }
  return map[status] || status
}

/**
 * 获取风险等级文本
 * @param {string} level 风险等级
 * @returns {string} 风险等级文本
 */
export function getRiskText(level) {
  const map = {
    high: '高风险',
    medium: '中风险',
    low: '低风险'
  }
  return map[level] || level
}

/**
 * 获取风险等级样式类名
 * @param {string} level 风险等级
 * @returns {string} 样式类名
 */
export function getRiskClass(level) {
  return `risk-tag ${level}`
}

/**
 * 获取优先级文本
 * @param {string} priority 优先级
 * @returns {string} 优先级文本
 */
export function getPriorityText(priority) {
  const map = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return map[priority] || '中'
}

/**
 * 显示加载中
 * @param {string} title 标题
 */
export function showLoading(title = '加载中...') {
  uni.showLoading({
    title,
    mask: true
  })
}

/**
 * 隐藏加载中
 */
export function hideLoading() {
  uni.hideLoading()
}

/**
 * 显示提示
 * @param {string} title 标题
 * @param {string} icon 图标
 */
export function showToast(title, icon = 'none') {
  uni.showToast({
    title,
    icon,
    duration: 2000
  })
}

/**
 * 显示成功提示
 * @param {string} title 标题
 */
export function showSuccess(title) {
  showToast(title, 'success')
}

/**
 * 显示错误提示
 * @param {string} title 标题
 */
export function showError(title) {
  showToast(title, 'error')
}

/**
 * 页面跳转
 * @param {string} url 页面地址
 */
export function navigateTo(url) {
  uni.navigateTo({ url })
}

/**
 * 页面返回
 * @param {number} delta 返回层数
 */
export function navigateBack(delta = 1) {
  uni.navigateBack({ delta })
}

/**
 * 切换Tab
 * @param {string} url Tab地址
 */
export function switchTab(url) {
  uni.switchTab({ url })
}

/**
 * 存储数据
 * @param {string} key 键
 * @param {*} value 值
 */
export function setStorage(key, value) {
  uni.setStorageSync(key, value)
}

/**
 * 获取存储数据
 * @param {string} key 键
 * @param {*} defaultValue 默认值
 * @returns {*} 存储的值
 */
export function getStorage(key, defaultValue = null) {
  const value = uni.getStorageSync(key)
  return value || defaultValue
}

/**
 * 删除存储数据
 * @param {string} key 键
 */
export function removeStorage(key) {
  uni.removeStorageSync(key)
}

/**
 * 截断文本
 * @param {string} text 文本
 * @param {number} maxLength 最大长度
 * @returns {string} 截断后的文本
 */
export function truncate(text, maxLength = 30) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}