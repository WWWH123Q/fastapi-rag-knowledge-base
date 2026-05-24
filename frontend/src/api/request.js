import axios from 'axios'

/** 后端 API 根地址，可通过 VITE_API_BASE_URL 覆盖 */
export const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

const request = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
})

request.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('rag_api_key')
  if (apiKey) {
    config.headers = config.headers || {}
    config.headers['X-API-Key'] = apiKey
  }
  return config
})

request.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
)

export function getErrorMessage(error, fallback = '请求失败') {
  const detail = error?.response?.data?.detail
  if (!detail) {
    return error?.message || fallback
  }
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join('；')
  }
  return String(detail)
}

export default request
