// src/api/messages.js - 消息中心相关API
import apiClient from './index'

// 获取消息列表 (默认获取我接收到的消息)
export const getMessages = (page = 1, pageSize = 20, otherUserId) => {
  const params = {
    page,
    limit: pageSize
  }
  // otherUserId 参数在获取“我接收的消息”时通常不需要，除非是管理员查看某人消息
  // 但后端接口 get_self_receive 只返回当前登录用户的消息
  // 如果需要查看别人的，可能需要用 list 接口并加 filter
  return apiClient.get('/system/message_center/get_self_receive/', { params })
}

// 根据类型获取消息 (后端 get_self_receive 返回所有，这里尝试传参过滤，或者由前端过滤)
export const getMessagesByType = (messageType, page = 1, pageSize = 20) => {
  // messageType 可能需要映射到后端的 target_type (1:角色, 2:部门, 3:系统, 0:个人?)
  // 或者 messageType 是 contentType (TEXT, SYSTEM...)?
  // 假设前端传的是 'SYSTEM' 等字符串，而后端可能需要数字或字符串
  // 暂时透传
  return apiClient.get('/system/message_center/get_self_receive/', {
    params: {
      page,
      limit: pageSize,
      msg_type: messageType // 尝试传参，需后端支持
    }
  })
}

// 标记消息已读
// 后端没有独立 mark read 接口，读取详情时自动标记
// 这里调用详情接口来实现
export const markMessageRead = (messageId) => {
  return apiClient.get(`/system/message_center/${messageId}/`)
}

// 获取消息详情
export const getMessageDetail = (messageId) => {
  return apiClient.get(`/system/message_center/${messageId}/`)
}

// 删除消息
export const deleteMessage = (messageId) => {
  return apiClient.delete(`/system/message_center/${messageId}/`)
}

// 更新消息 (通常不允许，但保留接口映射)
export const updateMessage = (messageId, payload) => {
  return apiClient.put(`/system/message_center/${messageId}/`, payload)
}

// 发送消息 (管理员或系统调用)
export const sendMessage = (payload) => {
  return apiClient.post('/system/message_center/', payload)
}

// 获取广播消息 (系统通知)
export const getBroadcastMessages = (params = {}) => {
  // 映射到 get_self_receive 并过滤类型为系统通知
  return apiClient.get('/system/message_center/get_self_receive/', { 
    params: { ...params, target_type: 3 } 
  })
}
