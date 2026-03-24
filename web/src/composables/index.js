/**
 * 共享 Composables
 * Vue 3 组合式 API 的共享逻辑
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { formatDate, formatAmount } from '@/utils/formatters'

/**
 * 分页逻辑
 * @param {Object} options 选项
 * @returns {Object} 分页状态和方法
 */
export function usePagination(options = {}) {
  const {
    defaultPage = 1,
    defaultPageSize = 20,
    pageSizeOptions = [10, 20, 50, 100]
  } = options

  const page = ref(defaultPage)
  const pageSize = ref(defaultPageSize)
  const total = ref(0)

  const offset = computed(() => (page.value - 1) * pageSize.value)
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

  const setPage = (newPage) => {
    page.value = newPage
  }

  const setPageSize = (newSize) => {
    pageSize.value = newSize
    page.value = 1 // 重置到第一页
  }

  const setTotal = (newTotal) => {
    total.value = newTotal
  }

  const reset = () => {
    page.value = defaultPage
    pageSize.value = defaultPageSize
  }

  return {
    page,
    pageSize,
    total,
    offset,
    totalPages,
    pageSizeOptions,
    setPage,
    setPageSize,
    setTotal,
    reset
  }
}

/**
 * 加载状态
 * @returns {Object} 加载状态和方法
 */
export function useLoading(initialState = false) {
  const loading = ref(initialState)

  const startLoading = () => {
    loading.value = true
  }

  const stopLoading = () => {
    loading.value = false
  }

  const withLoading = async (asyncFn) => {
    loading.value = true
    try {
      return await asyncFn()
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    startLoading,
    stopLoading,
    withLoading
  }
}

/**
 * 对话框状态
 * @returns {Object} 对话框状态和方法
 */
export function useDialog() {
  const visible = ref(false)
  const data = ref(null)

  const open = (newData = null) => {
    data.value = newData
    visible.value = true
  }

  const close = () => {
    visible.value = false
  }

  const toggle = () => {
    visible.value = !visible.value
  }

  return {
    visible,
    data,
    open,
    close,
    toggle
  }
}

/**
 * 搜索过滤
 * @param {Array} items 数据列表
 * @param {Array} fields 搜索字段
 * @returns {Object} 搜索状态和方法
 */
export function useSearch(items, fields = []) {
  const keyword = ref('')

  const filteredItems = computed(() => {
    if (!keyword.value || !fields.length) return items.value

    const lowerKeyword = keyword.value.toLowerCase()
    return items.value.filter(item => {
      return fields.some(field => {
        const value = item[field]
        return value && String(value).toLowerCase().includes(lowerKeyword)
      })
    })
  })

  const clearKeyword = () => {
    keyword.value = ''
  }

  return {
    keyword,
    filteredItems,
    clearKeyword
  }
}

/**
 * 表单重置
 * @param {Object} initialValues 初始值
 * @returns {Object} 表单状态和方法
 */
export function useForm(initialValues = {}) {
  const form = ref({ ...initialValues })
  const originalValues = { ...initialValues }

  const resetForm = () => {
    form.value = { ...originalValues }
  }

  const setFieldValue = (field, value) => {
    form.value[field] = value
  }

  const updateForm = (newValues) => {
    form.value = { ...form.value, ...newValues }
  }

  return {
    form,
    resetForm,
    setFieldValue,
    updateForm
  }
}

/**
 * 窗口尺寸
 * @returns {Object} 窗口尺寸
 */
export function useWindowSize() {
  const width = ref(window.innerWidth)
  const height = ref(window.innerHeight)

  const update = () => {
    width.value = window.innerWidth
    height.value = window.innerHeight
  }

  onMounted(() => {
    window.addEventListener('resize', update)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', update)
  })

  return {
    width,
    height,
    isMobile: computed(() => width.value < 768),
    isTablet: computed(() => width.value >= 768 && width.value < 1024),
    isDesktop: computed(() => width.value >= 1024)
  }
}

/**
 * 本地存储
 * @param {string} key 键名
 * @param {*} defaultValue 默认值
 * @returns {Object} 响应式存储值
 */
export function useLocalStorage(key, defaultValue = null) {
  const storedValue = localStorage.getItem(key)
  const value = ref(storedValue ? JSON.parse(storedValue) : defaultValue)

  const setValue = (newValue) => {
    value.value = newValue
    if (newValue === null) {
      localStorage.removeItem(key)
    } else {
      localStorage.setItem(key, JSON.stringify(newValue))
    }
  }

  const removeValue = () => {
    value.value = defaultValue
    localStorage.removeItem(key)
  }

  return {
    value,
    setValue,
    removeValue
  }
}

/**
 * 计数器（用于刷新组件）
 * @returns {Object} 刷新方法
 */
export function useRefresh() {
  const key = ref(0)

  const refresh = () => {
    key.value++
  }

  return {
    key,
    refresh
  }
}