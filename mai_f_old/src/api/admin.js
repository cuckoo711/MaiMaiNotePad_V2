import apiClient from './index'

// 获取管理员统计信息 (目前后端可能未提供聚合统计，暂时使用用户统计代替或 mock)
export const getAdminStats = () => {
  // 临时映射到用户统计，或者需要后端增加 dashboard 接口
  // 假设 /content/users/stats 返回的是当前用户的，如果是管理员可能返回全局？
  // 暂时保留原路径或指向 content/users/stats
  return apiClient.get('/content/users/stats/')
}

// 获取最近注册用户
export const getRecentUsers = (params = {}) => {
  return apiClient.get('/system/user/', { 
    params: { 
      ...params, 
      ordering: '-date_joined' 
    } 
  })
}

// 获取用户列表 (管理员管理用户)
export const getAdminUsers = (params = {}) => {
  return apiClient.get('/system/user/', { params })
}

// 更新用户角色
export const updateUserRole = (userId, role) => {
  return apiClient.put(`/content/admin/users/${userId}/role/`, { role })
}

// 删除用户
export const deleteUser = (userId) => {
  return apiClient.delete(`/system/user/${userId}/`)
}

// 封禁用户
export const banUser = (userId, duration, reason) => {
  return apiClient.post(`/content/admin/users/${userId}/ban/`, {
    duration,
    reason
  })
}

// 解封用户 (同时解除禁言)
export const unbanUser = (userId) => {
  return apiClient.post(`/content/admin/users/${userId}/unban/`)
}

// 禁言用户
export const muteUser = (userId, duration, reason) => {
  return apiClient.post(`/content/admin/users/${userId}/mute/`, {
    duration,
    reason
  })
}

// 解除禁言 (后端 unban 接口同时解除禁言和封禁)
export const unmuteUser = (userId) => {
  return apiClient.post(`/content/admin/users/${userId}/unban/`)
}

// 管理员创建用户 (后端 UserViewSet create)
export const createUserByAdmin = (payload) => {
  return apiClient.post('/system/user/', payload)
}

// 获取所有知识库 (管理员视图)
export const getAllKnowledgeForAdmin = (params = {}) => {
  // 知识库列表接口，管理员身份可能返回所有
  return apiClient.get('/content/knowledge/', { params })
}

// 获取所有人设卡 (管理员视图)
export const getAllPersonaForAdmin = (params = {}) => {
  return apiClient.get('/content/persona/', { params })
}

// 获取上传历史 (管理员查看所有?)
// 后端 UserExtensionViewSet.uploads 通常只返回自己的
// 如果需要管理员查看所有，可能需要 AdminExtensionViewSet 支持或 filters
// 暂时映射到 UserExtensionViewSet
export const getAdminUploadHistory = (params = {}) => {
  return apiClient.get('/content/users/uploads/', { params })
}

// 获取上传统计
export const getAdminUploadStats = () => {
  return apiClient.get('/content/users/stats/')
}

// 批量删除消息
export const adminBatchDeleteMessages = (messageIds) => {
  // 后端暂无批量删除接口，需循环调用或后端支持
  // 这里暂时抛出错误或循环调用
  // 为了保持接口签名，使用 Promise.all
  const promises = messageIds.map(id => apiClient.delete(`/system/message_center/${id}/`))
  return Promise.all(promises)
}

// 删除上传记录 (关联到 UserExtensionViewSet?)
// UserExtensionViewSet 没有 delete upload 接口
// 可能是删除 Knowledge 或 Persona
// 暂时映射到删除知识库/人设卡 (需区分类型)
// 这里假设 uploadId 是 knowledgeId 或 personaId
export const deleteUploadRecord = (uploadId) => {
  // 无法确定类型，暂时不实现或假设是 knowledge
  // 建议前端调用具体的 deleteKnowledgeBase 或 deletePersonaCard
  return Promise.reject(new Error("请使用具体的删除接口"))
}

// 重处理上传 (后端暂无)
export const reprocessUpload = (uploadId) => {
  return Promise.reject(new Error("后端暂不支持重处理"))
}
