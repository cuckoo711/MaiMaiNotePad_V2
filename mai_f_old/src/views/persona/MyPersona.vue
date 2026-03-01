<template>
  <div class="my-persona-container">
    <div class="layout-container">
      <el-card class="list-card" shadow="hover">
        <div class="card-header">
          <div class="card-title-group">
            <h2 class="page-title">我的人设卡</h2>
            <p class="page-subtitle">管理自己上传的人设卡，支持查看、编辑、公开申请和删除</p>
          </div>
          <div class="card-actions">
            <el-button type="primary" @click="goToUpload">
              创建新的人设卡
            </el-button>
          </div>
        </div>

        <div class="toolbar">
          <el-input
            v-model="searchForm.name"
            placeholder="按名称搜索我的人设卡"
            clearable
            class="toolbar-input"
            @keyup.enter="handleSearch"
          />
          <el-select
            v-model="sortOption"
            class="toolbar-sort"
          >
            <el-option label="最近更新" value="updated_desc" />
            <el-option label="最早更新" value="updated_asc" />
            <el-option label="下载量最多" value="downloads_desc" />
            <el-option label="收藏数最多" value="stars_desc" />
          </el-select>
          <el-button @click="resetSearch">重置</el-button>
        </div>

        <div v-loading="loading">
          <MyRepoList
            :items="sortedPersonaList"
            publish-tooltip="申请公开到人设卡广场（需审核）"
            @item-click="openDetail"
            @edit-click="openEdit"
            @publish-click="requestPublish"
            @delete-click="confirmDelete"
          />
          <div
            v-if="!loading && sortedPersonaList.length === 0"
            class="empty-tip"
          >
            暂无人设卡，点击右上角「创建新的人设卡」开始创建。
          </div>
        </div>

        <div class="pagination-section">
          <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="pagination.total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </div>

    <el-dialog
      v-model="editDialogVisible"
      :title="editingPersona ? `编辑人设卡 - ${editingPersona.name}` : '编辑人设卡'"
      width="720px"
      destroy-on-close
    >
      <el-form label-width="100px" class="edit-form">
        <el-form-item label="人设卡描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
          />
        </el-form-item>
        <el-form-item label="标签">
          <div class="tags-editor">
            <el-tag
              v-for="tag in editForm.tags"
              :key="tag"
              closable
              size="small"
              @close="removeEditTag(tag)"
            >
              {{ tag }}
            </el-tag>
            <el-input
              v-model="editTagInput"
              class="tag-input"
              size="small"
              placeholder="输入标签，按逗号分隔"
              @keydown.enter.stop.prevent
              @keyup="handleEditTagInputKeyup"
              @blur="commitEditTagInput"
            />
          </div>
        </el-form-item>
      </el-form>

      <div class="files-header">
        <div class="kb-name">
          文件列表
          <span
            v-if="editingPersona && editingPersona.version"
            class="kb-version-inline"
          >
            版本号 {{ editingPersona.version }}
          </span>
        </div>
        <div class="files-actions">
          <input
            ref="fileInput"
            type="file"
            accept=".toml"
            style="display: none"
            @change="handleFileChange"
          />
        </div>
      </div>

      <FileListTable
        v-if="fileList.length"
        :items="fileList"
        :delete-text="'替换配置'"
        @preview="previewEditFile"
        @download="downloadEditFile"
        @delete="confirmDeleteEditFile"
      />
      <div
        v-else
        class="empty-tip"
      >
        暂无文件。
      </div>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveBasicInfo">保存信息</el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="detailDrawerVisible"
      :title="currentPersona ? currentPersona.name : '人设卡详情'"
      direction="rtl"
      size="75%"
      :with-header="true"
      destroy-on-close
    >
      <div v-if="currentPersona" class="dialog-content">
        <div class="basic-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="名称">
              {{ currentPersona.name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="版本号">
              {{ currentPersona.version || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <span v-if="currentPersona.is_public && !currentPersona.is_pending">公开</span>
              <span v-else-if="!currentPersona.is_public && currentPersona.is_pending">公开审核中</span>
              <span v-else>私有</span>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(currentPersona.create_datetime) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ formatDate(currentPersona.update_datetime) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="下载量">
              {{ currentPersona.downloads || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="收藏量">
              {{ currentPersona.star_count || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="标签" :span="2">
              <span v-if="currentPersona.tags && currentPersona.tags.length">
                <el-tag
                  v-for="(tag, index) in currentPersona.tags"
                  :key="index"
                  size="small"
                  style="margin-right: 5px"
                >
                  {{ tag }}
                </el-tag>
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">
              {{ currentPersona.description || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="drawer-remark-section">
          <div class="drawer-remark-header">
            <h4>补充说明</h4>
            <el-button
              text
              circle
              size="small"
              @click="startEditRemark"
            >
              <el-icon>
                <Edit />
              </el-icon>
            </el-button>
          </div>
          <div v-if="!editingRemark" class="drawer-remark-content">
            {{ currentPersona.content || '-' }}
          </div>
          <div v-else>
            <el-input
              v-model="remarkContent"
              type="textarea"
              :rows="4"
            />
            <div class="form-tip">
              补充说明仅自己可见，不会在人设卡广场等公共页面展示
            </div>
            <div class="drawer-remark-actions">
              <el-button
                type="primary"
                size="small"
                @click="saveRemark"
              >
                保存
              </el-button>
              <el-button
                size="small"
                @click="cancelRemarkEdit"
              >
                取消
              </el-button>
            </div>
          </div>
        </div>

        <div class="files-list-section">
          <h4>
            文件列表
            <span
              v-if="currentPersona && currentPersona.version"
              class="kb-version-inline"
            >
              （版本号 {{ currentPersona.version }}）
            </span>
          </h4>
          <FileListTable
            :items="currentPersona.files || []"
            :show-delete="false"
            @preview="previewFile"
            @download="downloadFile"
          />
        </div>

        <CommentSection
          v-if="currentPersona && currentPersona.id"
          target-type="persona"
          :target-id="currentPersona.id"
          :owner-id="currentPersona.uploader_id || currentPersona.author_id || ''"
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
import { Star, Download, Delete, UploadFilled, Edit } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import MyRepoList from '@/components/MyRepoList.vue'
import FileListTable from '@/components/FileListTable.vue'
import FileViewerDialog from '@/components/FileViewerDialog.vue'
import CommentSection from '@/components/CommentSection.vue'
import {
  getUserPersonaCards,
  getPersonaCardDetail,
  deletePersonaCard,
  updatePersonaCard,
  addFilesToPersonaCard,
  submitPersonaCard
} from '@/api/persona'
import { handleApiError, formatFileSize, formatDate, showApiErrorNotification, showErrorNotification, showSuccessNotification, showWarningNotification, normalizeTags } from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { usePersonaStore } from '@/stores/persona'

const router = useRouter()
const userStore = useUserStore()
const { user } = storeToRefs(userStore)
const personaStore = usePersonaStore()
const { currentPersona } = storeToRefs(personaStore)

const apiBase = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:9278/api`

const loading = ref(false)
const personaList = ref([])
const sortOption = ref('updated_desc')

const editDialogVisible = ref(false)
const editingPersona = ref(null)
const editForm = reactive({
  description: '',
  tags: []
})
const editTagInput = ref('')
const fileList = ref([])
const fileInput = ref(null)

const detailDrawerVisible = ref(false)
const remarkContent = ref('')
const editingRemark = ref(false)

const fileViewerVisible = ref(false)
const fileViewerTitle = ref('')
const fileViewerFileName = ref('')
const fileViewerContent = ref('')
const fileViewerLanguage = ref('')
const fileViewerLoading = ref(false)
const fileViewerPersonaId = ref(null)
const fileViewerFile = ref(null)

const searchForm = reactive({
  name: ''
})

const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

const addTagsFromInput = (source, inputValue) => {
  if (!inputValue) {
    return
  }
  const normalized = inputValue.replace(/，/g, ',')
  const parts = normalized.split(',').map((item) => item.trim()).filter((item) => item)
  if (!parts.length) {
    return
  }
  parts.forEach((tag) => {
    if (!source.includes(tag)) {
      source.push(tag)
    }
  })
}

const handleEditTagInputKeyup = (event) => {
  if (event.key === ',' || event.key === '，') {
    event.preventDefault()
    addTagsFromInput(editForm.tags, editTagInput.value)
    editTagInput.value = ''
  }
}

const commitEditTagInput = () => {
  if (!editTagInput.value) {
    return
  }
  addTagsFromInput(editForm.tags, editTagInput.value)
  editTagInput.value = ''
}

const removeEditTag = (tag) => {
  const index = editForm.tags.indexOf(tag)
  if (index !== -1) {
    editForm.tags.splice(index, 1)
  }
}

const fetchPersona = async () => {
  if (!user.value || !user.value.id) {
    try {
      await userStore.fetchCurrentUser()
    } catch (error) {
      showApiErrorNotification(error, '获取用户信息失败')
      return
    }
  }
  if (!user.value || !user.value.id) {
    return
  }
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      limit: pagination.pageSize
    }
    if (searchForm.name) {
      params.name = searchForm.name
    }
    // 使用 'me' 调用 /content/persona/my/ 端点，避免 list 的公开过滤
    const response = await getUserPersonaCards('me', params)
    if (response.success) {
      // 分页响应：data 直接是数组，total 在顶层
      const items = (response.data || []).map((card) => ({
        ...card,
        tags: normalizeTags(card.tags)
      }))
      personaList.value = items
      pagination.total = response.total || personaList.value.length
    } else {
      showErrorNotification(response.message || '获取我的人设卡失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '获取我的人设卡失败')
  } finally {
    loading.value = false
  }
}

const sortedPersonaList = computed(() => {
  const list = [...personaList.value]
  switch (sortOption.value) {
    case 'updated_asc':
      return list.sort((a, b) => new Date(a.update_datetime || a.create_datetime || 0) - new Date(b.update_datetime || b.create_datetime || 0))
    case 'downloads_desc':
      return list.sort((a, b) => (b.downloads || 0) - (a.downloads || 0))
    case 'stars_desc':
      return list.sort((a, b) => (b.star_count || 0) - (a.star_count || 0))
    case 'updated_desc':
    default:
      return list.sort((a, b) => new Date(b.update_datetime || b.create_datetime || 0) - new Date(a.update_datetime || a.create_datetime || 0))
  }
})

const handleSearch = () => {
  pagination.currentPage = 1
  fetchPersona()
}

const resetSearch = () => {
  searchForm.name = ''
  pagination.currentPage = 1
  fetchPersona()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchPersona()
}

const handleCurrentChange = (page) => {
  pagination.currentPage = page
  fetchPersona()
}

const requestPublish = async (pc) => {
  try {
    const message =
      '申请公开后，人设卡将在审核通过后公开展示。<br/><br/>' +
      '一旦审核通过：<br/>' +
      '- 无法将人设卡再改回私有；<br/>' +
      '- 无法继续编辑人设卡的基本信息和文件（补充说明仍可编辑）。<br/><br/>' +
      '确定要申请公开吗？'
    await ElMessageBox.confirm(
      message,
      '确认申请公开',
      {
        confirmButtonText: '确认申请公开',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: true
      }
    )
  } catch {
    return
  }
  try {
    const response = await submitPersonaCard(pc.id)
    if (response && response.success) {
      showSuccessNotification(response.message || '已提交公开申请，等待审核')
      fetchPersona()
    } else {
      showErrorNotification((response && response.message) || '提交公开申请失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '提交公开申请失败')
  }
}

const confirmDelete = (row) => {
  ElMessageBox.prompt(
    `此操作将永久删除人设卡「${row.name}」，请输入人设卡名称以确认：`,
    '删除确认',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
      inputPlaceholder: `请输入：${row.name}`,
      inputValidator: (value) => {
        if (!value) {
          return '请输入人设卡名称'
        }
        if (value !== row.name) {
          return '输入的名称与人设卡名称不一致'
        }
        return true
      }
    }
  )
    .then(() => deletePersona(row))
    .catch(() => {})
}

const deletePersona = async (row) => {
  try {
    const response = await deletePersonaCard(row.id)
    if (response.success) {
      showSuccessNotification(response.message || '删除成功')
      fetchPersona()
    } else {
      showErrorNotification(response.message || '删除失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '删除人设卡失败')
  }
}

const openEdit = async (pc) => {
  if (pc.is_public || pc.is_pending) {
    showErrorNotification('公开或审核中的人设卡不允许修改基本信息和文件（补充说明仍可编辑）')
    return
  }
  try {
    const response = await getPersonaCardDetail(pc.id)
    if (response && response.success) {
      const data = response.data || {}
      data.tags = normalizeTags(data.tags)
      editingPersona.value = data
      editForm.description = data.description || ''
      editForm.tags = normalizeTags(data.tags)
      editTagInput.value = ''
      fileList.value = data.files || []
      editDialogVisible.value = true
    } else {
      showErrorNotification((response && response.message) || '获取人设卡详情失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '获取人设卡详情失败')
  }
}

const openDetail = async (pc) => {
  try {
    const response = await getPersonaCardDetail(pc.id)
    if (response && response.success) {
      const data = response.data || {}
      data.tags = normalizeTags(data.tags)
      personaStore.setCurrentPersona(data)
      remarkContent.value = data.content || ''
      editingRemark.value = false
      detailDrawerVisible.value = true
    } else {
      showErrorNotification((response && response.message) || '获取人设卡详情失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '获取人设卡详情失败')
  }
}

const downloadPersonaFile = async (personaId, file) => {
  if (!personaId || !file) {
    return
  }
  try {
    const downloadUrl = `${apiBase}/content/persona/${personaId}/files/${file.id}/`
    const response = await fetch(downloadUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        Authorization: `JWT ${localStorage.getItem('access_token')}`
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

const downloadFile = async (file) => {
  if (!currentPersona.value) {
    return
  }
  await downloadPersonaFile(currentPersona.value.id, file)
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

const openPersonaFileViewer = async (personaId, file) => {
  if (!personaId || !file) {
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
  fileViewerPersonaId.value = personaId
  fileViewerFile.value = file
  try {
    const previewUrl = `${apiBase}/content/persona/${personaId}/files/${file.id}/`
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
    showApiErrorNotification(error, '预览文件失败')
    fileViewerVisible.value = false
  } finally {
    fileViewerLoading.value = false
  }
}

const previewEditFile = (file) => {
  if (!editingPersona.value) {
    return
  }
  openPersonaFileViewer(editingPersona.value.id, file)
}

const previewFile = (file) => {
  if (!currentPersona.value) {
    return
  }
  openPersonaFileViewer(currentPersona.value.id, file)
}

const downloadFromViewer = async () => {
  if (!fileViewerPersonaId.value || !fileViewerFile.value) {
    return
  }
  await downloadPersonaFile(fileViewerPersonaId.value, fileViewerFile.value)
}

const MAX_PERSONA_FILES = 1
const MAX_PERSONA_FILE_SIZE_MB = 100
const MAX_PERSONA_FILE_SIZE_BYTES = MAX_PERSONA_FILE_SIZE_MB * 1024 * 1024

const saveBasicInfo = async () => {
  if (!editingPersona.value) {
    return
  }
  try {
    const payload = {
      description: editForm.description,
      tags: Array.isArray(editForm.tags) ? editForm.tags.join(',') : ''
    }
    const response = await updatePersonaCard(editingPersona.value.id, payload)
    if (response && response.success) {
      showSuccessNotification(response.message || '修改人设卡成功')
      editDialogVisible.value = false
      fetchPersona()
    } else {
      showErrorNotification((response && response.message) || '修改人设卡失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '修改人设卡失败')
  }
}

const triggerFileSelect = () => {
  if (!editingPersona.value) {
    return
  }
  if (fileInput.value) {
    fileInput.value.click()
  }
}

const handleFileChange = async (event) => {
  if (!editingPersona.value) {
    return
  }
  const files = event.target.files
  if (!files || !files.length) {
    return
  }
  try {
    const selectedFiles = Array.from(files)
    const validFiles = []
    for (const file of selectedFiles) {
      const lowerName = file.name.toLowerCase()
      if (!lowerName.endsWith('.toml')) {
        showErrorNotification(`不支持的文件类型: ${file.name}，仅支持 .toml 文件`)
        continue
      }
      if (typeof file.size === 'number' && file.size > MAX_PERSONA_FILE_SIZE_BYTES) {
        showErrorNotification(`文件过大: ${file.name}，单个文件不超过 ${MAX_PERSONA_FILE_SIZE_MB}MB`)
        continue
      }
      validFiles.push(file)
    }
    if (!validFiles.length) {
      showErrorNotification('请选择符合要求的 .toml 文件')
      return
    }
    const file = validFiles[0]
    const response = await addFilesToPersonaCard(editingPersona.value.id, [file])
    if (response && response.success) {
      showSuccessNotification(response.message || '文件添加成功')
      const detail = await getPersonaCardDetail(editingPersona.value.id)
      if (detail && detail.success) {
        const data = detail.data || {}
        fileList.value = data.files || []
      }
    } else {
      showErrorNotification((response && response.message) || '添加文件失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '添加文件失败')
  } finally {
    if (event.target) {
      event.target.value = ''
    }
  }
}

const confirmDeleteEditFile = () => {
  triggerFileSelect()
}

const downloadEditFile = async (file) => {
  if (!editingPersona.value) {
    return
  }
  try {
    const downloadUrl = `${apiBase}/content/persona/${editingPersona.value.id}/files/${file.id}/`
    const response = await fetch(downloadUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        Authorization: `JWT ${localStorage.getItem('access_token')}`
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
    console.error('下载编辑文件错误:', error)
    showErrorNotification('下载失败: ' + error.message)
  }
}

const goToUpload = () => {
  router.push('/persona-upload')
}

const saveRemark = async () => {
  if (!currentPersona.value) {
    return
  }
  try {
    const payload = {
      content: remarkContent.value
    }
    const response = await updatePersonaCard(currentPersona.value.id, payload)
    if (response && response.success) {
      showSuccessNotification(response.message || '备注已保存')
      currentPersona.value.content = remarkContent.value
      const target = personaList.value.find((item) => item.id === currentPersona.value.id)
      if (target) {
        target.content = remarkContent.value
      }
      editingRemark.value = false
    } else {
      showErrorNotification((response && response.message) || '保存备注失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '保存备注失败')
  }
}

const startEditRemark = () => {
  if (!currentPersona.value) {
    return
  }
  remarkContent.value = currentPersona.value.content || ''
  editingRemark.value = true
}

const cancelRemarkEdit = () => {
  if (!currentPersona.value) {
    return
  }
  remarkContent.value = currentPersona.value.content || ''
  editingRemark.value = false
}

onMounted(async () => {
  await fetchPersona()
})
</script>

<style scoped>
.my-persona-container {
  padding: 24px;
}

.list-card {
  border-radius: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar-input {
  flex: 1;
  min-width: 220px;
}

.toolbar-sort {
  width: 160px;
}

.empty-tip {
  padding: 24px 0;
  text-align: center;
  color: #909399;
  font-size: 14px;
}

.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted-text-color);
}

.pagination-section {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.dialog-content {
  padding: 0;
}

.basic-info {
  margin-bottom: 20px;
}

.drawer-remark-section {
  margin-top: 16px;
}

.drawer-remark-section h4 {
  margin-bottom: 8px;
  color: var(--secondary-color);
}

.drawer-remark-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.drawer-remark-content {
  min-height: 60px;
  padding: 8px 10px;
  border-radius: 6px;
  background-color: var(--hover-color);
  font-size: 13px;
  color: var(--muted-text-color);
  white-space: pre-wrap;
}

.drawer-remark-actions {
  margin-top: 8px;
}

.download-all-section {
  margin: 20px 0;
  text-align: center;
}

.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.kb-name {
  font-weight: 600;
}

.files-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-version-inline {
  margin-left: 8px;
  font-size: 12px;
  color: var(--muted-text-color);
}

.files-list-section {
  margin-top: 20px;
}

.files-list-section h4 {
  margin-bottom: 10px;
  color: var(--secondary-color);
}
</style>
