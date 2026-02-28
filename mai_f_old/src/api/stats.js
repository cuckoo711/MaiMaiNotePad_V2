import apiClient from './index'

// 获取我的上传统计
export const getMyUploadStats = () => {
  return apiClient.get('/content/users/stats/')
}

// 获取我的上传历史
export const getMyUploadHistory = (params = {}) => {
  return apiClient.get('/content/users/uploads/', { params })
}

// 获取我的仪表盘概览
export const getMyDashboardStats = () => {
  return apiClient.get('/content/users/overview/')
}

// 获取管理端上传统计 (目前复用用户统计接口)
export const getAdminUploadStats = () => {
  return apiClient.get('/content/users/stats/')
}

// 获取我的仪表盘趋势
export const getMyDashboardTrends = (params = {}) => {
  return apiClient.get('/content/users/trend/', { params })
}
