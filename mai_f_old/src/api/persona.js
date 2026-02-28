// src/api/persona.js - 人设卡相关API
import apiClient from './index'

// 上传人设卡
export const uploadPersonaCard = (formData) => {
  return apiClient.post('/content/persona/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取公开人设卡
export const getPublicPersonaCards = (params = {}) => {
  return apiClient.get('/content/persona/', { params })
}

// 获取人设卡详情
export const getPersonaCardDetail = (pc_id) => {
  return apiClient.get(`/content/persona/${pc_id}/`)
}

// 检查人设卡Star状态
export const checkPersonaCardStarred = (pc_id) => {
  // 临时方案：调用详情接口，假设返回 is_starred
  return apiClient.get(`/content/persona/${pc_id}/`).then(res => {
    return { data: { is_starred: res.data && res.data.is_starred } }
  })
}

// 获取用户人设卡
export const getUserPersonaCards = (user_id, params = {}) => {
  if (user_id === 'me') {
    return apiClient.get('/content/persona/my/', { params })
  }
  return apiClient.get('/content/persona/', { params: { ...params, uploader: user_id } })
}

// 更新人设卡
export const updatePersonaCard = (pc_id, payload) => {
  return apiClient.put(`/content/persona/${pc_id}/`, payload)
}

// Star人设卡
export const starPersonaCard = (pc_id) => {
  return apiClient.post(`/content/persona/${pc_id}/star/`)
}

// 取消Star人设卡
export const unstarPersonaCard = (pc_id) => {
  return apiClient.delete(`/content/persona/${pc_id}/unstar/`)
}

// 删除人设卡
export const deletePersonaCard = (pc_id) => {
  return apiClient.delete(`/content/persona/${pc_id}/`)
}

// 向人设卡添加文件
export const addFilesToPersonaCard = (pc_id, files) => {
  const formData = new FormData()
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i])
  }
  // 假设后端支持 files action (POST) 或使用 update
  return apiClient.post(`/content/persona/${pc_id}/files/`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 从人设卡删除文件
export const deleteFileFromPersonaCard = (pc_id, file_id) => {
  return apiClient.delete(`/content/persona/${pc_id}/files/${file_id}/`)
}

// 获取待审核人设卡列表
export const getPendingPersonaReview = (params = {}) => {
  return apiClient.get('/content/review/', { 
    params: { ...params, content_type: 'persona' } 
  })
}

// 审核通过人设卡
export const approvePersonaCardReview = (pc_id) => {
  return apiClient.post(`/content/review/${pc_id}/approve/`, {
    content_type: 'persona'
  })
}

// 审核拒绝人设卡
export const rejectPersonaCardReview = (pc_id, reason) => {
  return apiClient.post(`/content/review/${pc_id}/reject/`, { 
    content_type: 'persona',
    reason 
  })
}
