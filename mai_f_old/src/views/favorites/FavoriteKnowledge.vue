<template>
  <div class="favorite-knowledge-container">
    <div class="layout-container">
      <el-card class="list-card" shadow="hover">
        <div class="card-header">
          <div class="card-title-group">
            <h2 class="page-title">收藏知识库</h2>
            <p class="page-subtitle">查看自己收藏的知识库列表，支持按收藏时间排序</p>
          </div>
          <div class="card-actions">
            <el-select
              v-model="searchForm.sort_by"
              class="toolbar-sort"
              @change="handleSortChange"
            >
              <el-option label="收藏时间" value="create_datetime" />
              <el-option label="收藏数" value="star_count" />
            </el-select>
            <el-select
              v-model="searchForm.sort_order"
              class="toolbar-sort"
              @change="handleSortChange"
            >
              <el-option label="从新到旧" value="desc" />
              <el-option label="从旧到新" value="asc" />
            </el-select>
            <el-button @click="resetSort">重置排序</el-button>
          </div>
        </div>

        <div v-loading="loading">
          <div class="knowledge-base-list-container">
            <div class="knowledge-base-list">
              <el-card
                v-for="kb in favoriteList"
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
                    <span class="stat-item stat-star">
                      <el-icon>
                        <StarFilled />
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
          <div
            v-if="!loading && favoriteList.length === 0"
            class="empty-tip"
          >
            暂无收藏的知识库，可前往知识库广场进行收藏。
          </div>
        </div>

        <div class="pagination-section">
          <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[12, 24, 36, 48]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="pagination.total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </div>

    <el-drawer
      v-model="detailVisible"
      :title="safeSelectedKB.name || '知识库详情'"
      direction="rtl"
      size="75%"
      :with-header="true"
      destroy-on-close
    >
      <div class="dialog-content">
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

        <div class="download-all-section">
          <el-button type="primary" @click="downloadAllFiles">
            <el-icon>
              <Download />
            </el-icon>
            下载全部文件
          </el-button>
        </div>

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
                    <el-icon>
                      <Download />
                    </el-icon>
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
      <template #footer>
        <div class="drawer-footer">
          <div class="drawer-footer-left">
            <el-button
              type="danger"
              text
              @click="handleUnstarFromDetail"
            >
              取消收藏
            </el-button>
          </div>
        </div>
      </template>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElAvatar, ElIcon } from 'element-plus'
import { StarFilled, Download, View } from '@element-plus/icons-vue'
import FileViewerDialog from '@/components/FileViewerDialog.vue'
import CommentSection from '@/components/CommentSection.vue'
import { useFileViewer } from '@/composables/useFileViewer'
import { getAuthorName, getAuthorDisplay } from '@/utils/author'
import { getUserStars } from '@/api/user'
import { unstarKnowledgeBase } from '@/api/knowledge'
import { showApiErrorNotification, showErrorNotification, showSuccessNotification, showInfoNotification, formatFileSize as sharedFormatFileSize, formatDate as sharedFormatDate, normalizeTags } from '@/utils/api'

const apiBase = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:9278/api`

const searchForm = reactive({
  sort_by: 'create_datetime',
  sort_order: 'desc'
})

const pagination = reactive({
  currentPage: 1,
  pageSize: 12,
  total: 0
})

const favoriteList = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const selectedKB = ref(null)

const safeSelectedKB = computed(() => selectedKB.value || {})

const formatFileSize = sharedFormatFileSize
const formatDate = sharedFormatDate

const {
  fileViewerVisible,
  fileViewerTitle,
  fileViewerFileName,
  fileViewerContent,
  fileViewerLanguage,
  fileViewerLoading,
  previewFile,
  downloadFile,
  downloadFromViewer
} = useFileViewer({
  apiBase,
  resourceLabel: '知识库',
  getResourceId: () => (selectedKB.value && selectedKB.value.id) || null,
  buildPreviewPath: (id, file) => `/content/knowledge/${id}/files/${file.id}/`,
  buildDownloadPath: (id, file) => `/content/knowledge/${id}/files/${file.id}/`
})

const fetchFavorites = async () => {
  loading.value = true
  try {
    const params = {
      target_type: 'knowledge',
      // 后端暂不支持分页和排序参数，前端自行处理
    }
    const response = await getUserStars(params)
    if (response && (response.success || response.code === 2000)) {
      // 后端返回的是 StarRecord 列表，包含 target_detail
      const records = response.data || []
      
      // 1. 映射数据结构
      let items = records.map((record) => {
        const detail = record.target_detail || {}
        return {
          ...detail,
          id: detail.id, // 确保使用知识库ID作为主键
          star_id: record.id, // 保留收藏记录ID
          collected_at: record.create_datetime, // 收藏时间
          tags: normalizeTags(detail.tags)
        }
      })

      // 2. 前端排序
      items.sort((a, b) => {
        let valA, valB
        if (searchForm.sort_by === 'create_datetime') {
          // 这里的 create_datetime 对应前端选择的"收藏时间"
          valA = new Date(a.collected_at || 0).getTime()
          valB = new Date(b.collected_at || 0).getTime()
        } else if (searchForm.sort_by === 'star_count') {
          valA = a.star_count || 0
          valB = b.star_count || 0
        } else {
          // 默认按收藏时间
          valA = new Date(a.collected_at || 0).getTime()
          valB = new Date(b.collected_at || 0).getTime()
        }
        
        if (searchForm.sort_order === 'asc') {
          return valA - valB
        } else {
          return valB - valA
        }
      })

      // 3. 更新总数
      pagination.total = items.length

      // 4. 前端分页
      const start = (pagination.currentPage - 1) * pagination.pageSize
      const end = start + pagination.pageSize
      favoriteList.value = items.slice(start, end)
      
    } else {
      showErrorNotification((response && response.message) || '获取收藏知识库失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '获取收藏知识库失败')
  } finally {
    loading.value = false
  }
}

const handleSortChange = () => {
  pagination.currentPage = 1
  fetchFavorites()
}

const resetSort = () => {
  searchForm.sort_by = 'create_datetime'
  searchForm.sort_order = 'desc'
  pagination.currentPage = 1
  fetchFavorites()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchFavorites()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  fetchFavorites()
}

const showKBDetail = (kb) => {
  if (!kb) {
    return
  }
  selectedKB.value = kb
  detailVisible.value = true
}

const handleUnstarFromDetail = async () => {
  if (!selectedKB.value || !selectedKB.value.id) {
    return
  }
  try {
    const response = await unstarKnowledgeBase(selectedKB.value.id)
    if (response && response.success) {
      showSuccessNotification(response.message || '取消收藏成功')
      favoriteList.value = favoriteList.value.filter((item) => item.id !== selectedKB.value.id)
      if (pagination.total > 0) {
        pagination.total -= 1
      }
      detailVisible.value = false
    } else {
      showErrorNotification((response && response.message) || '取消收藏失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '取消收藏失败')
  }
}

const formatDateOnly = (value) => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleDateString()
}

const downloadAllFiles = async () => {
  try {
    if (!selectedKB.value || !selectedKB.value.id) {
      showErrorNotification('未找到要下载的知识库')
      return
    }
    const downloadUrl = `${apiBase}/knowledge/${selectedKB.value.id}/download`
    const loading = showInfoNotification('正在准备下载文件...', { duration: 0 })
    const response = await fetch(downloadUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        Authorization: `JWT ${localStorage.getItem('access_token')}`,
        Accept: 'application/zip'
      }
    })
    if (!response.ok) {
      const errorText = await response.text()
      console.error('下载失败，响应文本:', errorText)
      throw new Error(`下载失败，HTTP状态码: ${response.status}, 错误信息: ${errorText}`)
    }
    const blob = await response.blob()
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
    window.URL.revokeObjectURL(url)
    loading.close()
    showSuccessNotification('开始下载知识库文件压缩包')
  } catch (error) {
    console.error('下载知识库文件压缩包错误:', error)
    showErrorNotification('下载失败: ' + error.message)
  }
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
  fetchFavorites()
})
</script>

<style scoped>
.favorite-knowledge-container {
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

.list-card {
  width: 100%;
  box-sizing: border-box;
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 22px;
  margin: 0;
}

.page-subtitle {
  margin: 0;
  color: #909399;
  font-size: 13px;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-sort {
  width: 160px;
}

.knowledge-base-list-container {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 20px;
}

.knowledge-base-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 360px));
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
  margin-bottom: 10px;
}

.card-tags {
  margin-bottom: 6px;
}

.card-meta {
  font-size: 12px;
  color: var(--muted-text-color);
}

.card-file-stat {
  margin-left: 4px;
}

.empty-tip {
  padding: 24px 0;
  text-align: center;
  color: #909399;
  font-size: 14px;
}

.pagination-section {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.drawer-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.drawer-footer-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drawer-footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
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
