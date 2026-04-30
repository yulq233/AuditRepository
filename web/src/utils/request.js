import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建axios实例
const request = axios.create({
  baseURL: '/api',
  timeout: 120000  // 增加到120秒，支持AI识别等耗时操作
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const { response } = error

    if (response) {
      // 将详细信息附加到error对象，让调用方自己处理
      error.detail = response.data?.detail

      switch (response.status) {
        case 401:
          ElMessage.error('登录已过期，请重新登录')
          localStorage.removeItem('token')
          router.push('/login')
          break
        case 403:
          ElMessage.error('没有权限访问')
          break
        case 404:
          // 404错误不自动显示，让调用方自己处理
          // 这样可以根据具体业务场景显示更友好的提示
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          // 其他错误显示后端返回的详细信息
          if (response.data?.detail) {
            ElMessage.error(response.data.detail)
          }
      }
    } else {
      ElMessage.error('网络连接失败')
    }

    return Promise.reject(error)
  }
)

export default request