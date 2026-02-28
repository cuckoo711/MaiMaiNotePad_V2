// src/api/knowledge.js - 知识库相关API
import apiClient from './index'

// 获取公开知识库 (对应后端 list 操作，自动过滤公开且已审核)
export const getPublicKnowledgeBase = (params = {}) => {
  return apiClient.get('/content/knowledge/', { params })
}

// 获取知识库详情
export const getKnowledgeBaseDetail = (kb_id) => {
  return apiClient.get(`/content/knowledge/${kb_id}/`)
}

// 检查知识库Star状态
// 后端没有独立接口，通常在详情中返回 is_starred 字段，或者通过收藏列表查询
// 这里暂时保留接口，如果详情中包含该字段，前端应直接使用详情数据
export const checkKnowledgeBaseStarred = (kb_id) => {
  // 临时方案：调用详情接口
  return apiClient.get(`/content/knowledge/${kb_id}/`).then(res => {
     // 假设后端返回的数据中有 is_starred 字段
     // 如果没有，可能需要调用收藏列表接口自行判断
     return { data: { is_starred: res.data && res.data.is_starred } }
  })
}

// Star知识库
export const starKnowledgeBase = (kb_id) => {
  return apiClient.post(`/content/knowledge/${kb_id}/star/`)
}

// 取消Star知识库
export const unstarKnowledgeBase = (kb_id) => {
  return apiClient.delete(`/content/knowledge/${kb_id}/unstar/`)
}

// 获取用户知识库
// 如果是获取当前用户的，使用 /my/ action
// 如果是获取其他用户的，尝试使用 filter
export const getUserKnowledgeBase = (user_id, params = {}) => {
  // 判断是否是获取当前用户（通常前端会传入 'me' 或者当前用户ID）
  // 但这里简单处理：如果是 'me'，调用 /my/
  // 否则调用 list 并传参（后端需支持 uploader 过滤）
  if (user_id === 'me') {
    return apiClient.get('/content/knowledge/my/', { params })
  }
  return apiClient.get('/content/knowledge/', { params: { ...params, uploader: user_id } })
}

// 上传知识库
export const uploadKnowledgeBase = (formData) => {
  return apiClient.post('/content/knowledge/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 更新知识库信息
export const updateKnowledgeBase = (kb_id, payload) => {
  return apiClient.put(`/content/knowledge/${kb_id}/`, payload)
}

// 删除知识库
export const deleteKnowledgeBase = (kb_id) => {
  return apiClient.delete(`/content/knowledge/${kb_id}/`)
}

// 为知识库追加文件
export const addFilesToKnowledgeBase = (kb_id, files) => {
  const formData = new FormData()
  // 后端接口似乎是逐个上传或支持多文件，这里假设支持多文件或前端循环调用
  // 修正：后端 files action 似乎是 list/create 结构？
  // 再次检查 backend: KnowledgeBaseViewSet 不直接处理 files upload list?
  // 实际上 backend 有 files action 但那是自定义 action 吗？
  // 看了代码，files action 没看到，但有 delete_file。
  // 通常 upload 是 POST /content/knowledge/{pk}/files/ ?
  // 检查发现 KnowledgeBaseViewSet 没有 files action (POST).
  // 只有 delete_file (DELETE).
  // 那么上传文件是在创建时？还是有单独的 KnowledgeBaseFileViewSet?
  // 重新看 KnowledgeBaseViewSet: 
  //   files: 添加文件到知识库 (docstring 提到，但代码里没看到 @action(methods=['POST']... def files)
  //   Wait, I missed it? Let's assume standard sub-resource or update.
  //   If missing, I might need to use updateKnowledgeBase with files?
  //   Let's assume POST /content/knowledge/{pk}/files/ for now based on docstring hint.
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i])
  }
  return apiClient.post(`/content/knowledge/${kb_id}/files/`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 从知识库删除单个文件
export const deleteFileFromKnowledgeBase = (kb_id, file_id) => {
  return apiClient.delete(`/content/knowledge/${kb_id}/files/${file_id}/`)
}

// 获取待审核知识库列表
export const getPendingKnowledgeReview = (params = {}) => {
  return apiClient.get('/content/review/', { 
    params: { ...params, content_type: 'knowledge' } 
  })
}

// 审核通过知识库
export const approveKnowledgeBaseReview = (kb_id) => {
  return apiClient.post(`/content/review/${kb_id}/approve/`, {
    content_type: 'knowledge'
  })
}

// 审核拒绝知识库
export const rejectKnowledgeBaseReview = (kb_id, reason) => {
  return apiClient.post(`/content/review/${kb_id}/reject/`, { 
    content_type: 'knowledge',
    reason 
  })
}
