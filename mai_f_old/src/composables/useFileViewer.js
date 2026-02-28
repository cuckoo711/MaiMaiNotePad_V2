import { ref } from 'vue'
import { showErrorNotification, showSuccessNotification } from '@/utils/api'

export const useFileViewer = (options) => {
  const {
    apiBase,
    resourceLabel,
    getResourceId,
    buildPreviewPath,
    buildDownloadPath
  } = options || {}

  const fileViewerVisible = ref(false)
  const fileViewerTitle = ref('')
  const fileViewerFileName = ref('')
  const fileViewerContent = ref('')
  const fileViewerLanguage = ref('')
  const fileViewerLoading = ref(false)
  const fileViewerFile = ref(null)

  const resolveFileLanguage = (fileName) => {
    const lower = (fileName || '').toLowerCase()
    if (lower.endsWith('.toml')) {
      return 'toml'
    }
    if (lower.endsWith('.json')) {
      return 'json'
    }
    return 'txt'
  }

  const isPreviewableFile = (file) => {
    const name = (file && file.original_name) || ''
    const lower = name.toLowerCase()
    return lower.endsWith('.toml') || lower.endsWith('.json') || lower.endsWith('.txt')
  }

  const resolveBaseUrl = () => {
    const base = apiBase || ''
    return base.endsWith('/') ? base.slice(0, -1) : base
  }

  const previewFile = async (file) => {
    const id = getResourceId ? getResourceId() : null
    if (!id) {
      showErrorNotification(`未找到要预览的${resourceLabel || '资源'}`)
      return
    }
    if (!isPreviewableFile(file)) {
      showErrorNotification('当前文件类型暂不支持在线预览，请使用下载功能查看')
      return
    }
    const name = file.original_name || ''
    fileViewerTitle.value = name || '文件预览'
    fileViewerFileName.value = name
    fileViewerLanguage.value = resolveFileLanguage(name)
    fileViewerContent.value = ''
    fileViewerVisible.value = true
    fileViewerLoading.value = true
    fileViewerFile.value = file
    try {
      const baseUrl = resolveBaseUrl()
      const path = buildPreviewPath ? buildPreviewPath(id, file) : ''
      const previewUrl = `${baseUrl}${path}`
      const response = await fetch(previewUrl, {
        method: 'GET',
        credentials: 'include',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`
        }
      })
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`预览失败，HTTP状态码: ${response.status}, 错误信息: ${errorText}`)
      }
      const text = await response.text()
      fileViewerContent.value = text
    } catch (error) {
      console.error('预览文件错误:', error)
      showErrorNotification('预览失败: ' + error.message)
      fileViewerVisible.value = false
    } finally {
      fileViewerLoading.value = false
    }
  }

  const downloadFile = async (file) => {
    const id = getResourceId ? getResourceId() : null
    if (!id) {
      showErrorNotification(`未找到要下载的${resourceLabel || '资源'}`)
      return
    }
    try {
      const baseUrl = resolveBaseUrl()
      const path = buildDownloadPath ? buildDownloadPath(id, file) : ''
      const downloadUrl = `${baseUrl}${path}`
      const response = await fetch(downloadUrl, {
        method: 'GET',
        credentials: 'include',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`
        }
      })
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`下载失败，HTTP状态码: ${response.status}, 错误信息: ${errorText}`)
      }
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = file.original_name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      showSuccessNotification(`开始下载文件: ${file.original_name}`)
    } catch (error) {
      console.error('下载单个文件错误:', error)
      showErrorNotification('下载失败: ' + error.message)
    }
  }

  const downloadFromViewer = async () => {
    if (!fileViewerFile.value) {
      return
    }
    await downloadFile(fileViewerFile.value)
  }

  return {
    fileViewerVisible,
    fileViewerTitle,
    fileViewerFileName,
    fileViewerContent,
    fileViewerLanguage,
    fileViewerLoading,
    previewFile,
    downloadFile,
    downloadFromViewer
  }
}

