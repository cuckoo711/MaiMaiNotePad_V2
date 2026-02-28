// src/api/user.js - 用户相关API
import apiClient from './index'

// 用户登录
export const login = (username, password, captcha, captchaKey) => {
  return apiClient.post('/login/', {
    username,
    password,
    captcha,
    captchaKey
  })
}

// 获取验证码
export const getCaptcha = () => {
  return apiClient.get('/captcha/')
}

// 用户注册 (第一步：提交信息，后端发送验证邮件)
export const register = (username, password, email) => {
  // 获取当前页面的 Origin，并拼接验证页面路径
  // 假设 VerifyEmail.vue 的路由是 /verify-email
  const verification_url = window.location.origin + '/verify-email'
  
  return apiClient.post('/register/', {
    username,
    password,
    email,
    verification_url
  })
}

// 验证邮箱 (点击邮件链接后调用)
export const verifyEmail = (token) => {
  return apiClient.get('/verify-email/', {
    params: { token }
  })
}

// 重发验证邮件
export const resendVerificationEmail = (email) => {
  const verification_url = window.location.origin + '/verify-email'
  return apiClient.post('/resend-verification/', { email, verification_url })
}

// 获取当前用户信息
export const getCurrentUser = () => {
  return apiClient.get('/system/user/user_info/')
}

// 更新用户信息（包括头像）
export const updateUserInfo = (formData) => {
  return apiClient.put('/system/user/update_user_info/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 上传头像 (复用 updateUserInfo)
export const uploadAvatar = (avatar) => {
  const formData = new FormData()
  formData.append('avatar', avatar)
  return updateUserInfo(formData)
}

// 删除头像
export const deleteAvatar = () => {
  return apiClient.put('/system/user/update_user_info/', { avatar: '' })
}

// 发送邮箱验证码
export const sendEmailCode = (email) => {
  return apiClient.post('/system/user/send_email_code/', { email })
}

// 修改密码
export const changePassword = (oldPassword, newPassword, newPassword2) => {
  return apiClient.put('/system/user/change_password/', {
    oldPassword,
    newPassword,
    newPassword2
  })
}

// 检查注册合法性 (后端暂无独立接口，前端可校验格式，唯一性由注册接口校验)
export const checkRegisterLegality = (username, email) => {
  // 暂时直接返回成功，由注册接口处理
  return Promise.resolve({ code: 2000, msg: 'ok', success: true })
}

// 发送验证码 (后端采用邮件链接验证，此接口映射到重发邮件)
export const sendVerificationCode = (email) => {
  return resendVerificationEmail(email)
}

// 发送重置密码验证码 (后端暂无此接口)
export const sendResetPasswordCode = (email) => {
  console.warn('Backend does not support sendResetPasswordCode yet.')
  return Promise.reject(new Error('暂不支持找回密码功能'))
}

// 重置密码 (后端暂无此接口)
export const resetPassword = (email, verification_code, new_password) => {
  console.warn('Backend does not support resetPassword yet.')
  return Promise.reject(new Error('暂不支持找回密码功能'))
}

export const getUserStars = (params = {}) => {
  // 调用后端收藏列表接口
  return apiClient.get('/content/users/stars/', {
    params
  })
}
