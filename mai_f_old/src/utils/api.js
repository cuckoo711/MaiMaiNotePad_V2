import { h } from 'vue'
import { ElNotification, ElIcon, ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'

const createNotificationContent = (message) => {
  const text = typeof message === 'string' ? message : String(message ?? '')

  const handleCopy = async (event) => {
    if (event && typeof event.stopPropagation === 'function') {
      event.stopPropagation()
    }
    try {
      if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      ElMessage.success('已复制到剪贴板')
    } catch (e) {
      ElMessage.error('复制失败，请手动复制')
    }
  }

  return h(
    'div',
    { class: 'mnp-notification-content' },
    [
      h('div', { class: 'mnp-notification-text' }, text),
      h(
        'button',
        {
          type: 'button',
          class: 'mnp-notification-copy-btn',
          onClick: handleCopy
        },
        [
          h(
            ElIcon,
            { size: 16 },
            () => h(DocumentCopy)
          )
        ]
      )
    ]
  )
}

const baseNotification = (type, message, options = {}) => {
  const content = createNotificationContent(message)
  return ElNotification({
    type,
    message: content,
    position: 'bottom-left',
    duration: 4000,
    showClose: true,
    ...options
  })
}

export const handleApiResponse = (response, successCallback, errorCallback) => {
  if (response && response.code === 2000) {
    if (successCallback) {
      // 后端数据通常在 data 字段中
      successCallback(response.data, response.msg || '操作成功')
    }
  } else {
    const errorMessage = (response && response.msg) || '操作失败'
    if (errorCallback) {
      errorCallback(errorMessage)
    } else {
      console.error('API Error:', errorMessage)
    }
  }
}

export const handleApiError = (error, defaultMessage = '请求失败') => {
  console.error('API Error:', error)
  const response = error && error.response
  const data = response && response.data

  let message =
    (data && data.msg) || // 后端通常返回 msg
    (data && data.detail) || // DRF 默认错误
    (data && data.error && data.error.message) ||
    (data && data.message) ||
    error.message ||
    defaultMessage

  // 处理可能的嵌套错误信息 (如 serializer 验证错误)
  if (data && typeof data === 'object' && !data.msg && !data.detail && !data.error && !data.message) {
    // 尝试获取第一个值的第一个错误
    const keys = Object.keys(data)
    if (keys.length > 0) {
      const key = keys[0]
      const firstVal = data[key]
      if (Array.isArray(firstVal) && firstVal.length > 0) {
        message = `${key}: ${firstVal[0]}`
      } else if (typeof firstVal === 'string') {
        message = `${key}: ${firstVal}`
      }
    }
  }

  const status = response && response.status
  const errorInfo = data && data.error
  const details = errorInfo && errorInfo.details
  const code = (errorInfo && errorInfo.code) || (details && details.code)
  const requestId = data && data.error && data.error.request_id

  const extra = []
  if (status) {
    extra.push(`状态码 ${status}`)
  }
  if (code) {
    extra.push(`错误码 ${code}`)
  }
  if (requestId) {
    extra.push(`请求ID ${requestId}`)
  }
  if (extra.length && status >= 500) {
    message = `${message}\n${extra.join('\n')}`
  }

  return message
}

export const showApiErrorNotification = (error, defaultMessage = '请求失败') => {
  const message = handleApiError(error, defaultMessage)
  return baseNotification('error', message)
}

export const showErrorNotification = (message, options = {}) => {
  return baseNotification('error', message, options)
}

export const showSuccessNotification = (message, options = {}) => {
  return baseNotification('success', message, options)
}

export const showWarningNotification = (message, options = {}) => {
  return baseNotification('warning', message, options)
}

export const showInfoNotification = (message, options = {}) => {
  return baseNotification('info', message, options)
}

export const normalizeTags = (tags) => {
  if (!tags) {
    return []
  }
  if (Array.isArray(tags)) {
    return tags
      .map((item) => (item == null ? '' : String(item).trim()))
      .filter((item) => item)
  }
  if (typeof tags === 'string') {
    const normalized = tags.replace(/，/g, ',')
    return normalized
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item)
  }
  return []
}

export const formatFileSize = (size) => {
  if (!size || Number.isNaN(size) || size <= 0) {
    return '0 B'
  }
  if (size < 1024) {
    return `${size} B`
  }
  const kb = size / 1024
  if (kb < 1024) {
    return `${kb.toFixed(2)} KB`
  }
  const mb = kb / 1024
  if (mb < 1024) {
    return `${mb.toFixed(2)} MB`
  }
  const gb = mb / 1024
  return `${gb.toFixed(2)} GB`
}

export const formatDate = (value) => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleString()
}
