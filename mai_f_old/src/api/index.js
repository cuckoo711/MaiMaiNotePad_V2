import axios from 'axios'

export const DEFAULT_API_PORT = 8000

export const apiBase =
  import.meta.env.VITE_API_BASE_URL ||
  `${window.location.protocol}//${window.location.hostname}:${DEFAULT_API_PORT}/api`

const apiClient = axios.create({
  baseURL: apiBase,
  timeout: 10000,
})

// refreshClient 不挂响应拦截器，避免循环刷新
const refreshClient = axios.create({
  baseURL: apiBase,
  timeout: 10000,
})

let isRefreshing = false
let refreshSubscribers = []
let isRedirecting = false

const subscribeTokenRefresh = (callback) => {
  refreshSubscribers.push(callback)
}

const onRefreshed = (newToken) => {
  refreshSubscribers.forEach((callback) => callback(newToken))
  refreshSubscribers = []
}

const onRefreshFailed = (error) => {
  // refresh 失败时，拒绝所有排队的请求
  refreshSubscribers.forEach((callback) => callback(null, error))
  refreshSubscribers = []
}

const redirectToLogin = () => {
  // 防止多个并发 401 重复触发跳转
  if (isRedirecting) return
  isRedirecting = true
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  window.location.href = '/login'
}

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `JWT ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

apiClient.interceptors.response.use(
  (response) => {
    if (response.data && response.data.code === 2000) {
      response.data.success = true
      // 统一将 msg 映射为 message，方便前端使用
      if (response.data.msg !== undefined && response.data.message === undefined) {
        response.data.message = response.data.msg
      }
      return response.data
    }
    // 后端自定义异常处理器会把 401 包装成 HTTP 200，body 里 code=401
    // 需要在成功回调里检测并跳转登录页
    if (response.data && response.data.code === 401) {
      redirectToLogin()
      const msg = response.data.msg
      const errorMsg = typeof msg === 'string' ? msg : (msg ? JSON.stringify(msg) : '登录已过期，请重新登录')
      return Promise.reject(new Error(errorMsg))
    }
    // 如果返回的不是标准格式但状态码是200，也直接返回data（适配某些特殊接口）
    if (response.status === 200 && response.data.code === undefined) {
      response.data.success = true
      return response.data
    }
    // 确保错误消息是字符串，避免 [object Object]
    const msg = response.data.msg
    const errorMsg = typeof msg === 'string' ? msg : (msg ? JSON.stringify(msg) : '请求失败')
    return Promise.reject(new Error(errorMsg))
  },
  async (error) => {
    const { response, config } = error

    if (response && response.status === 401) {
      if (config && config.url && (config.url.includes('/login') || config.url.includes('/auth/token'))) {
        return Promise.reject(error)
      }
      const originalRequest = config
      const refreshToken = localStorage.getItem('refresh_token')

      if (!refreshToken) {
        redirectToLogin()
        return Promise.reject(error)
      }

      if (originalRequest._retry) {
        redirectToLogin()
        return Promise.reject(error)
      }

      originalRequest._retry = true

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((newToken, err) => {
            if (err || !newToken) {
              return reject(err || error)
            }
            originalRequest.headers.Authorization = `JWT ${newToken}`
            resolve(apiClient(originalRequest))
          })
        })
      }

      isRefreshing = true

      try {
        // 后端刷新 token 接口地址：/api/token/refresh/
        const refreshResponse = await refreshClient.post('/token/refresh/', { refresh: refreshToken })

        const data = refreshResponse.data
        if (data && data.code === 2000) {
           const { access } = data.data
           localStorage.setItem('access_token', access)
           apiClient.defaults.headers.common.Authorization = `JWT ${access}`
           originalRequest.headers.Authorization = `JWT ${access}`
           onRefreshed(access)
           return apiClient(originalRequest)
        } else if (data && data.access) {
           // 适配 simplejwt 原生返回
           const { access } = data
           localStorage.setItem('access_token', access)
           apiClient.defaults.headers.common.Authorization = `JWT ${access}`
           originalRequest.headers.Authorization = `JWT ${access}`
           onRefreshed(access)
           return apiClient(originalRequest)
        } else {
           onRefreshFailed(error)
           redirectToLogin()
           return Promise.reject(error)
        }
      } catch (refreshError) {
        onRefreshFailed(refreshError)
        redirectToLogin()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    if (error.response && error.response.data) {
      const data = error.response.data
      if (data.msg) {
        error.message = typeof data.msg === 'string' ? data.msg : JSON.stringify(data.msg)
      } else if (data.detail) {
        error.message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
