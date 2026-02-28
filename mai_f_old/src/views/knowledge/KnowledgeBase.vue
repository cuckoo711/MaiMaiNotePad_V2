<template>
  <div class="knowledge-base-container">
    <div class="layout-container">
      <!-- 搜索栏 -->
      <div class="search-section">
        <el-card shadow="hover" class="search-card">
          <div class="search-toolbar">
            <el-input
              v-model="searchForm.keyword"
              placeholder="搜索名称或描述"
              clearable
              class="search-input"
              @keyup.enter="handleSearch"
            />
            <el-input
              v-model="searchForm.uploader"
              placeholder="作者ID"
              clearable
              class="filter-input"
              @keyup.enter="handleSearch"
            />
            <el-input
              v-model="searchForm.tags"
              placeholder="标签"
              clearable
              class="filter-input"
              @keyup.enter="handleSearch"
            />
            <el-select
              v-model="searchForm.sort_by"
              class="sort-select"
              @change="handleSearch"
            >
              <el-option label="创建时间" value="create_datetime" />
              <el-option label="更新时间" value="update_datetime" />
              <el-option label="名称" value="name" />
              <el-option label="下载量" value="downloads" />
              <el-option label="收藏量" value="star_count" />
            </el-select>
            <el-select
              v-model="searchForm.sort_order"
              class="sort-order-select"
              @change="handleSearch"
            >
              <el-option label="降序" value="desc" />
              <el-option label="升序" value="asc" />
            </el-select>
            <el-button-group class="search-btn-group">
              <el-button
                type="primary"
                @click="handleSearch"
                class="search-btn"
              >
                搜索
              </el-button>
              <el-button @click="resetSearch">
                重置
              </el-button>
            </el-button-group>
          </div>
        </el-card>
      </div>

      <!-- 知识库列表 -->
      <div class="knowledge-base-list-container">
        <div class="knowledge-base-list">
          <el-card
            v-for="kb in knowledgeBases"
            :key="kb.id"
            shadow="hover"
            class="knowledge-base-item"
            @click="showKBDetail(kb)"
          >
            <div class="card-header">
              <div class="card-title">
                <el-avatar
                  :size="32"
                  :src="resolveAuthorAvatar(kb)"
                  class="kb-avatar"
                >
                  <template #default>
                    {{ getKBInitial(kb.author || kb.name) }}
                  </template>
                </el-avatar>
                <h3 class="card-name">{{ kb.name }}</h3>
              </div>
              <div class="card-stats">
                <span class="stat-item">
                  <el-icon>
                    <Download />
                  </el-icon>
                  {{ kb.downloads }}
                </span>
                <span
                  class="stat-item stat-star"
                  @click.stop="toggleStar(kb)"
                >
                  <el-icon>
                    <StarFilled v-if="kb.isStarred" />
                    <Star v-else />
                  </el-icon>
                  {{ kb.star_count }}
                </span>
              </div>
            </div>
            <div class="card-author">
              {{ getAuthorDisplay(kb) }}
            </div>
            <div class="card-description">
              {{ kb.description }}
            </div>
            <div
              v-if="kb.tags && kb.tags.length"
              class="card-tags"
            >
              <el-tag
                v-for="(tag, index) in kb.tags"
                :key="index"
                size="small"
                effect="plain"
              >
                {{ tag }}
              </el-tag>
            </div>
            <div class="card-meta">
              <span class="card-date">
                {{ formatDateOnly(kb.update_datetime || kb.create_datetime) }}
              </span>
              <span
                v-if="kb.files && kb.files.length"
                class="card-file-stat"
              >
                · {{ kb.files.length }} 个文件
              </span>
              <span
                v-if="typeof kb.size === 'number'"
                class="card-file-stat"
              >
                · 共 {{ formatFileSize(kb.size) }}
              </span>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-section">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[12, 24, 36, 48]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="pagination.total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        ></el-pagination>
      </div>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="dialogVisible"
      :title="safeSelectedKB.name || '知识库详情'"
      direction="rtl"
      size="75%"
      :with-header="true"
      destroy-on-close
    >
      <div class="dialog-content">
        <!-- 基本信息 -->
        <div class="basic-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="名称">{{ safeSelectedKB.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="作者">{{ getAuthorName(safeSelectedKB) }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(safeSelectedKB.create_datetime) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatDate(safeSelectedKB.update_datetime) }}</el-descriptions-item>
            <el-descriptions-item label="下载量">{{ safeSelectedKB.downloads || 0 }}</el-descriptions-item>
            <el-descriptions-item label="收藏量">{{ safeSelectedKB.star_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="标签" :span="2">
              <span v-if="safeSelectedKB.tags && safeSelectedKB.tags.length > 0">
                <el-tag v-for="(tag, index) in safeSelectedKB.tags" :key="index" size="small" style="margin-right: 5px;">{{ tag }}</el-tag>
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ safeSelectedKB.description || '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 下载全部按钮 -->
        <div class="download-all-section">
          <el-button type="primary" @click="downloadAllFiles">
            <el-icon><Download /></el-icon>
            下载全部文件
          </el-button>
        </div>

        <!-- 文件列表 -->
        <div class="files-list-section">
          <h4>文件列表</h4>
          <el-table :data="safeSelectedKB.files || []" style="width: 100%">
            <el-table-column label="文件名" width="auto">
              <template #default="scope">{{ scope.row.original_name || '-' }}</template>
            </el-table-column>
            <el-table-column
              label="大小"
              width="120"
              align="center"
              header-align="center"
            >
              <template #default="scope">{{ formatFileSize(scope.row.file_size) }}</template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="140"
              fixed="right"
              align="center"
              header-align="center"
            >
              <template #default="scope">
                <el-tooltip content="浏览文件" placement="top">
                  <el-button
                    type="primary"
                    text
                    circle
                    size="small"
                    @click="previewFile(scope.row)"
                  >
                    <el-icon>
                      <View />
                    </el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="下载文件" placement="top">
                  <el-button
                    type="primary"
                    text
                    circle
                    size="small"
                    @click="downloadFile(scope.row)"
                  >
                    <el-icon><Download /></el-icon>
                  </el-button>
                </el-tooltip>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <CommentSection
          v-if="safeSelectedKB && safeSelectedKB.id"
          target-type="knowledge"
          :target-id="safeSelectedKB.id"
          :owner-id="safeSelectedKB.uploader_id || safeSelectedKB.author_id || ''"
        />
      </div>
    </el-drawer>
    <FileViewerDialog
      v-model:visible="fileViewerVisible"
      :title="fileViewerTitle"
      :file-name="fileViewerFileName"
      :content="fileViewerContent"
      :language="fileViewerLanguage"
      :loading="fileViewerLoading"
      @download="downloadFromViewer"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { Star, StarFilled, Download, View } from '@element-plus/icons-vue'
import { ElIcon, ElAvatar } from 'element-plus'
import FileViewerDialog from '@/components/FileViewerDialog.vue'
import CommentSection from '@/components/CommentSection.vue'
import { getPublicKnowledgeBase, starKnowledgeBase, unstarKnowledgeBase, getKnowledgeBaseDetail, checkKnowledgeBaseStarred } from '@/api/knowledge'
import { handleApiError, showApiErrorNotification, showErrorNotification, showSuccessNotification, showInfoNotification, formatFileSize as sharedFormatFileSize, formatDate as sharedFormatDate, normalizeTags } from '@/utils/api'
import { getAuthorName as sharedGetAuthorName, getAuthorDisplay as sharedGetAuthorDisplay } from '@/utils/author'
import { useKnowledgeStore } from '@/stores/knowledge'

const apiBase = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:9278/api`

// 搜索输入（GitHub 风格语法）
// 搜索表单
const searchForm = reactive({
  keyword: '',
  uploader: '',
  tags: '',
  sort_by: 'create_datetime',
  sort_order: 'desc'
})

// 分页
const pagination = reactive({
  currentPage: 1,
  pageSize: 12,
  total: 0
})

// 知识库列表
const knowledgeBases = ref([])

// 详情弹窗
const dialogVisible = ref(false)
const knowledgeStore = useKnowledgeStore()
const { currentKB: selectedKB } = storeToRefs(knowledgeStore)
const safeSelectedKB = computed(() => selectedKB.value || {})

const fileViewerVisible = ref(false)
const fileViewerTitle = ref('')
const fileViewerFileName = ref('')
const fileViewerContent = ref('')
const fileViewerLanguage = ref('')
const fileViewerLoading = ref(false)
const fileViewerFile = ref(null)

const formatFileSize = sharedFormatFileSize
const formatDate = sharedFormatDate
const getAuthorName = sharedGetAuthorName
const getAuthorDisplay = sharedGetAuthorDisplay

// 获取知识库列表
const getKnowledgeBases = async () => {
  try {
    const params = {
      page: pagination.currentPage,
      limit: pagination.pageSize,
      keyword: searchForm.keyword || undefined,
      uploader: searchForm.uploader || undefined,
      tags: searchForm.tags || undefined,
      // 将 sort_by + sort_order 转换为 DRF OrderingFilter 的 ordering 参数
      ordering: searchForm.sort_order === 'asc' ? searchForm.sort_by : `-${searchForm.sort_by}`
    }
    
    const response = await getPublicKnowledgeBase(params)
    if (response.success) {
      // interceptor 解包后 response 就是后端的完整响应体
      // 分页数据在 response.data（数组），总数在 response.total
      const list = Array.isArray(response.data) ? response.data : []
      knowledgeBases.value = list.map((kb) => ({
        ...kb,
        tags: normalizeTags(kb.tags),
        isStarred: false
      }))
      pagination.total = typeof response.total === 'number' ? response.total : list.length
      await checkAllStarStatus()
    } else {
      showErrorNotification(response.message || '获取知识库列表失败')
    }
  } catch (error) {
    console.error('获取知识库列表错误:', error)
    showApiErrorNotification(error, '获取知识库列表失败，请检查网络连接')
  }
}

// 检查所有知识库的收藏状态
const checkAllStarStatus = async () => {
  for (const kb of knowledgeBases.value) {
    try {
      const response = await checkKnowledgeBaseStarred(kb.id)
      if (response.success) {
        kb.isStarred = response.data.starred
      }
    } catch (error) {
      console.error(`检查知识库收藏状态失败: ${kb.id}`, error)
      // 忽略检查失败的情况，继续检查其他知识库
    }
  }
}

// 搜索方法
const handleSearch = () => {
  pagination.currentPage = 1
  getKnowledgeBases()
}

// 重置搜索
const resetSearch = () => {
  Object.assign(searchForm, {
    keyword: '',
    uploader: '',
    tags: '',
    sort_by: 'create_datetime',
    sort_order: 'desc'
  })
  pagination.currentPage = 1
  getKnowledgeBases()
}

// 分页方法
const handleSizeChange = (size) => {
  pagination.pageSize = size
  getKnowledgeBases()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  getKnowledgeBases()
}

// 切换收藏状态
const toggleStar = async (kb) => {
  try {
    let response
    if (kb.isStarred) {
      // 取消Star
      response = await unstarKnowledgeBase(kb.id)
    } else {
      // Star
      response = await starKnowledgeBase(kb.id)
    }
    
    if (response.success) {
      kb.isStarred = !kb.isStarred
      // 更新收藏数
      if (kb.isStarred) {
        kb.star_count++
      } else {
        kb.star_count--
      }
      showSuccessNotification(kb.isStarred ? '收藏成功' : '取消收藏成功')
    } else {
      showErrorNotification(response.message || (kb.isStarred ? '取消收藏失败' : '收藏失败'))
    }
  } catch (error) {
    console.error('Star操作错误:', error)
    showApiErrorNotification(error, '操作失败，请检查网络连接')
  }
}

// 显示详情弹窗
const showKBDetail = async (kb) => {
  try {
    const response = await getKnowledgeBaseDetail(kb.id)
    if (response.success) {
      const data = response.data || {}
      data.tags = normalizeTags(data.tags)
      selectedKB.value = data
      dialogVisible.value = true
    } else {
      showErrorNotification(response.message || '获取知识库详情失败')
    }
  } catch (error) {
    console.error('获取知识库详情错误:', error)
    showApiErrorNotification(error, '获取知识库详情失败，请检查网络连接')
  }
}

// 下载单个文件
const downloadFile = async (file) => {
  try {
    if (!selectedKB.value || !selectedKB.value.id) {
      showErrorNotification('未找到要下载的知识库')
      return
    }
    const downloadUrl = `${apiBase}/content/knowledge/${selectedKB.value.id}/files/${file.id}/`
    
    // 使用fetch API获取文件
    const response = await fetch(downloadUrl, {
      method: 'GET',
      credentials: 'include', // 包含认证信息
      headers: {
        'Authorization': `JWT ${localStorage.getItem('access_token')}` // 添加token
      }
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`下载失败，HTTP状态码: ${response.status}, 错误信息: ${errorText}`)
    }
    
    // 将响应转换为blob对象
    const blob = await response.blob()
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.original_name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // 释放URL对象
    window.URL.revokeObjectURL(url)
    
    showSuccessNotification(`开始下载文件: ${file.original_name}`)
  } catch (error) {
    console.error('下载单个文件错误:', error)
    showErrorNotification('下载失败: ' + error.message)
  }
}

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

const previewFile = async (file) => {
  if (!selectedKB.value || !selectedKB.value.id) {
    showErrorNotification('未找到要预览的知识库')
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
    const previewUrl = `${apiBase}/content/knowledge/${selectedKB.value.id}/files/${file.id}/`
    const response = await fetch(previewUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        Authorization: `JWT ${localStorage.getItem('access_token')}`
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

const downloadFromViewer = async () => {
  if (!fileViewerFile.value) {
    return
  }
  await downloadFile(fileViewerFile.value)
}

const downloadAllFiles = async () => {
  try {
    if (!selectedKB.value || !selectedKB.value.id) {
      showErrorNotification('未找到要下载的知识库')
      return
    }
    const downloadUrl = `${apiBase}/knowledge/${selectedKB.value.id}/download`
    
    // 显示加载状态
    const loading = showInfoNotification('正在准备下载文件...', { duration: 0 })
    
    console.log('开始下载，URL:', downloadUrl)
    const response = await fetch(downloadUrl, {
      method: 'GET',
      credentials: 'include', // 包含认证信息
      headers: {
        'Authorization': `JWT ${localStorage.getItem('access_token')}`, // 添加token
        'Accept': 'application/zip' // 明确请求zip格式
      }
    })
    
    console.log('下载响应状态:', response.status)
    console.log('响应头:', response.headers)
    
    if (!response.ok) {
      // 获取错误响应的详细信息
      const errorText = await response.text()
      console.error('下载失败，响应文本:', errorText)
      throw new Error(`下载失败，HTTP状态码: ${response.status}, 错误信息: ${errorText}`)
    }
    
    const blob = await response.blob()
    console.log('下载成功，blob大小:', blob.size)
    console.log('blob类型:', blob.type)
    
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const kb = selectedKB.value || {}
    const kbName = kb.name || '未命名知识库'
    const author = getAuthorName(kb) || '未知作者'
    const updatedAt = kb.update_datetime || kb.create_datetime
    const date = updatedAt ? new Date(updatedAt) : new Date()
    const pad = (n) => String(n).padStart(2, '0')
    const ts = `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
    const sanitize = (value) => String(value).replace(/[\\/:*?"<>|]/g, '_').trim()
    const finalName = `知识库_${sanitize(kbName)}_${sanitize(author)}_${ts}`
    link.download = `${finalName}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // 释放URL对象
    window.URL.revokeObjectURL(url)
    
    // 关闭加载提示
    loading.close()
    showSuccessNotification('开始下载知识库文件压缩包')
  } catch (error) {
    console.error('下载知识库文件压缩包错误:', error)
    showErrorNotification('下载失败: ' + error.message)
  }
}

// 仅格式化日期（不含时分秒）
const formatDateOnly = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleDateString()
}

const getKBInitial = (name) => {
  if (!name) {
    return ''
  }
  const trimmed = String(name).trim()
  if (!trimmed) {
    return ''
  }
  return trimmed[0].toUpperCase()
}

const resolveAuthorAvatar = (kb) => {
  if (!kb || !kb.author_id) {
    return ''
  }
  const base = apiBase || ''
  const trimmedBase = base.endsWith('/') ? base.slice(0, -1) : base
  let url = `${trimmedBase}/users/${kb.author_id}/avatar?size=64`
  if (kb.avatar_updated_at) {
    url += `&t=${encodeURIComponent(kb.avatar_updated_at)}`
  }
  return url
}

onMounted(() => {
  getKnowledgeBases()
})
</script>

<style scoped>
.knowledge-base-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.layout-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
}

.search-section {
  margin-bottom: 20px;
}

.search-card {
  background-color: var(--card-background);
  border-color: var(--border-color);
}

.search-form {
  margin-bottom: 0;
}

.search-buttons {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.search-btn {
  background-color: var(--secondary-color);
  border-color: var(--secondary-color);
}

.search-btn-group {
  margin-left: 4px;
}

.sort-select {
  width: 100%;
}

.search-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.search-input {
  flex: 1;
  min-width: 220px;
}

.filter-input {
  width: 180px;
}

.sort-select {
  width: 140px;
}

.sort-order-select {
  width: 120px;
}

.knowledge-base-list-container {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 20px;
}

.knowledge-base-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.knowledge-base-item {
  cursor: pointer;
  height: 200px;
  display: flex;
  flex-direction: column;
  background-color: var(--card-background);
  border-color: var(--border-color);
  position: relative;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-avatar {
  flex-shrink: 0;
}

.card-name {
  font-size: 16px;
  font-weight: bold;
  margin: 0;
  color: var(--secondary-color);
}

.card-author {
  color: var(--muted-text-color);
  font-size: 14px;
  margin-bottom: 10px;
}

.card-description {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  line-clamp: 3;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  color: var(--muted-text-color);
  font-size: 14px;
  margin-bottom: 8px;
}

.card-tags {
  margin-bottom: 6px;
}

.card-tags :deep(.el-tag) {
  margin-right: 4px;
}

.card-meta {
  font-size: 12px;
  color: var(--muted-text-color);
}

.card-file-stat {
  margin-left: 4px;
}

.card-stats {
  display: flex;
  gap: 15px;
  align-items: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--muted-text-color);
  font-size: 14px;
}

.stat-star {
  cursor: pointer;
}

.stat-star :deep(.el-icon) {
  color: var(--muted-text-color);
}

.stat-star-active :deep(.el-icon) {
  color: #f90;
}

.pagination-section {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

/* 抽屉样式 */
:deep(.el-drawer) {
  background-color: var(--card-background);
  border-left: 1px solid var(--border-color);
}

:deep(.el-drawer__header) {
  border-bottom: 1px solid var(--border-color);
  padding: 20px;
}

:deep(.el-drawer__body) {
  overflow-y: auto;
  padding: 20px;
}

:deep(.el-drawer__headerbtn) {
  top: 20px;
  right: 20px;
}

.dialog-content {
  padding: 0;
}

.basic-info {
  margin-bottom: 20px;
}

.download-all-section {
  margin: 20px 0;
  text-align: center;
}

.files-list-section {
  margin-top: 20px;
}

.files-list-section h4 {
  margin-bottom: 10px;
  color: var(--secondary-color);
}
</style>
