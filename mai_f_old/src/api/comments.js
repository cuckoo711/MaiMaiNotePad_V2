import apiClient from './index'

// 获取评论列表 (支持树形结构)
export const getComments = (params) => {
  return apiClient.get('/content/comments/', {
    params
  })
}

// 发表评论
export const createComment = (payload) => {
  return apiClient.post('/content/comments/', payload)
}

// 删除评论
export const deleteComment = (commentId) => {
  return apiClient.delete(`/content/comments/${commentId}/`)
}

// 评论反应（点赞/点踩/取消）
export const reactComment = (commentId, action) => {
  // action: 'like' | 'dislike' | 'clear'
  return apiClient.post(`/content/comments/${commentId}/react/`, { action })
}

// 恢复评论 (管理员)
export const restoreComment = (commentId) => {
  return apiClient.post(`/content/comments/${commentId}/restore/`)
}
