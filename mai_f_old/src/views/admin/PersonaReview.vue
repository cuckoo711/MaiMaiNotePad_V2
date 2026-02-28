<template>
  <div class="persona-review-container">
    <div class="layout-container page-layout-inner">
      <el-card class="filter-card" shadow="hover">
        <div class="filter-bar">
          <el-input
            v-model="searchForm.name"
            placeholder="按名称搜索"
            class="filter-input"
            clearable
            @keyup.enter="handleSearch"
          />
          <el-input
            v-model="searchForm.uploader_id"
            placeholder="按上传者ID搜索"
            class="filter-input"
            clearable
            @keyup.enter="handleSearch"
          />
          <el-select
            v-model="searchForm.sort_by"
            class="filter-select"
          >
            <el-option label="创建时间" value="create_datetime" />
            <el-option label="更新时间" value="update_datetime" />
            <el-option label="收藏量" value="star_count" />
          </el-select>
          <el-select
            v-model="searchForm.sort_order"
            class="filter-select"
          >
            <el-option label="升序" value="asc" />
            <el-option label="降序" value="desc" />
          </el-select>
          <el-button type="primary" @click="handleSearch">
            搜索
          </el-button>
          <el-button @click="resetSearch">
            重置
          </el-button>
        </div>
      </el-card>

      <el-card class="list-card" shadow="hover">
        <div class="card-header">
          <div class="card-title-group">
            <h2 class="page-title">人设卡审核</h2>
            <p class="page-subtitle">查看并处理用户提交的人设卡公开申请</p>
          </div>
        </div>

        <ReviewList
          :items="reviewList"
          :loading="loading"
          :can-review="canReview"
          empty-text="暂无待审核的人设卡。"
          @view="showCardDetail"
          @approve="handleApprove"
          @reject="handleReject"
        />

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

      <el-drawer
        v-model="detailDialogVisible"
        direction="rtl"
        size="75%"
        :with-header="true"
        destroy-on-close
      >
        <template #header>
          <div class="drawer-title-with-version">
            <span class="drawer-title-text">
              {{ selectedCard?.name || '人设卡详情' }}
            </span>
            <el-tag
              v-if="selectedCard && selectedCard.version"
              size="small"
              type="info"
              effect="dark"
              class="drawer-version-tag"
            >
              v{{ selectedCard.version }}
            </el-tag>
          </div>
        </template>
        <div class="dialog-content">
          <div class="basic-info">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="名称">{{ selectedCard.name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="作者">{{ getAuthorName(selectedCard) }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDate(selectedCard.create_datetime) }}</el-descriptions-item>
              <el-descriptions-item label="更新时间">{{ formatDate(selectedCard.update_datetime) }}</el-descriptions-item>
              <el-descriptions-item label="下载量">{{ selectedCard.downloads || 0 }}</el-descriptions-item>
              <el-descriptions-item label="收藏量">{{ selectedCard.star_count || 0 }}</el-descriptions-item>
              <el-descriptions-item label="版本号">
                {{ selectedCard.version || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="标签" :span="2">
                <span v-if="selectedCard.tags && selectedCard.tags.length > 0">
                  <el-tag
                    v-for="(tag, index) in selectedCard.tags"
                    :key="index"
                    size="small"
                    style="margin-right: 5px;"
                  >
                    {{ tag }}
                  </el-tag>
                </span>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">{{ selectedCard.description || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="files-list-section">
            <h4>
              文件列表
              <span
                v-if="selectedCard && selectedCard.version"
                class="pc-version-inline"
              >
                （版本号 {{ selectedCard.version }}）
              </span>
            </h4>
            <el-table :data="selectedCard.files || []" style="width: 100%">
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
                label="修改时间"
                width="180"
                align="center"
                header-align="center"
              >
                <template #default="scope">
                  {{ formatDate(scope.row.update_datetime || scope.row.create_datetime) }}
                </template>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessageBox } from 'element-plus'
import { Download, View } from '@element-plus/icons-vue'
import ReviewList from '@/components/ReviewList.vue'
import FileViewerDialog from '@/components/FileViewerDialog.vue'
import { useFileViewer } from '@/composables/useFileViewer'
import { getAuthorName } from '@/utils/author'
import { getPendingPersonaReview, approvePersonaCardReview, rejectPersonaCardReview, getPersonaCardDetail } from '@/api/persona'
import { showApiErrorNotification, showErrorNotification, showSuccessNotification, formatFileSize as sharedFormatFileSize, formatDate as sharedFormatDate, normalizeTags } from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { usePersonaStore } from '@/stores/persona'

const apiBase = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:9278/api`

const loading = ref(false)
const reviewList = ref([])
const canReview = ref(false)
const userStore = useUserStore()
const { user } = storeToRefs(userStore)
const personaStore = usePersonaStore()
const { currentPersona: selectedCard } = storeToRefs(personaStore)

const detailDialogVisible = ref(false)

const formatDate = sharedFormatDate
const formatFileSize = sharedFormatFileSize

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
  resourceLabel: '人设卡',
  getResourceId: () => (selectedCard.value && selectedCard.value.id) || null,
  buildPreviewPath: (id, file) => `/content/persona/${id}/files/${file.id}/`,
  buildDownloadPath: (id, file) => `/content/persona/${id}/files/${file.id}/`
})

const searchForm = reactive({
  name: '',
  uploader_id: '',
  sort_by: 'create_datetime',
  sort_order: 'desc'
})

const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

const fetchCurrentUserRole = async () => {
  try {
    if (!user.value || !user.value.role) {
      await userStore.fetchCurrentUser()
    }
    const current = user.value || {}
    const role = current.role
    const flagAdmin = !!current.is_admin
    const flagModerator = !!current.is_moderator
    canReview.value = flagAdmin || flagModerator || role === 'admin' || role === 'super_admin' || role === 'moderator'
  } catch (error) {
    showApiErrorNotification(error, '获取用户信息失败')
  }
}

const fetchReviewList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize
    }
    if (searchForm.name) {
      params.name = searchForm.name
    }
    if (searchForm.uploader_id) {
      params.uploader_id = searchForm.uploader_id
    }
    if (searchForm.sort_by) {
      params.sort_by = searchForm.sort_by
    }
    if (searchForm.sort_order) {
      params.sort_order = searchForm.sort_order
    }
    const response = await getPendingPersonaReview(params)
    if (response && response.success) {
      const payload = response.data || {}
      const items = Array.isArray(payload.items) ? payload.items : []
      const mapped = items.map((pc) => ({
        ...pc,
        tags: normalizeTags(pc.tags)
      }))
      reviewList.value = mapped
      pagination.total = typeof payload.total === 'number' ? payload.total : mapped.length
    } else {
      showErrorNotification((response && response.message) || '获取待审核人设卡失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '获取待审核人设卡失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.currentPage = 1
  fetchReviewList()
}

const resetSearch = () => {
  searchForm.name = ''
  searchForm.uploader_id = ''
  searchForm.sort_by = 'create_datetime'
  searchForm.sort_order = 'desc'
  pagination.currentPage = 1
  fetchReviewList()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  fetchReviewList()
}

const handleCurrentChange = (page) => {
  pagination.currentPage = page
  fetchReviewList()
}

const showCardDetail = async (pc) => {
  if (!pc || !pc.id) {
    return
  }
  try {
    const response = await getPersonaCardDetail(pc.id)
    if (response && response.success) {
      const data = response.data || {}
      data.tags = normalizeTags(data.tags)
      selectedCard.value = data
      detailDialogVisible.value = true
    } else {
      showErrorNotification((response && response.message) || '获取人设卡详情失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '获取人设卡详情失败')
  }
}

const handleApprove = async (pc) => {
  if (!pc || !pc.id) {
    return
  }
  try {
    const response = await approvePersonaCardReview(pc.id)
    if (response && response.success) {
      showSuccessNotification(response.message || '审核通过成功')
      fetchReviewList()
    } else {
      showErrorNotification((response && response.message) || '审核通过失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '审核通过失败')
  }
}

const handleReject = async (pc) => {
  if (!pc || !pc.id) {
    return
  }
  try {
    const { value } = await ElMessageBox.prompt(
      `请输入拒绝人设卡「${pc.name}」的原因：`,
      '拒绝原因',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPlaceholder: '请输入拒绝原因',
        inputValidator: (val) => {
          if (!val) {
            return '请输入拒绝原因'
          }
          return true
        }
      }
    )
    const response = await rejectPersonaCardReview(pc.id, value)
    if (response && response.success) {
      showSuccessNotification(response.message || '审核拒绝成功')
      fetchReviewList()
    } else {
      showErrorNotification((response && response.message) || '审核拒绝失败')
    }
  } catch (error) {
    if (error === 'cancel') {
      return
    }
    showApiErrorNotification(error, '审核拒绝失败')
  }
}

onMounted(async () => {
  await fetchCurrentUserRole()
  await fetchReviewList()
})

</script>

<style scoped>
.persona-review-container {
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

.filter-card {
  border-radius: 12px;
}

.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-input {
  width: 220px;
}

.filter-select {
  width: 160px;
}

.pagination-section {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

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

.files-list-section {
  margin-top: 20px;
}

.files-list-section h4 {
  margin-bottom: 10px;
  color: var(--secondary-color);
}

.drawer-title-with-version {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drawer-title-text {
  font-size: 18px;
  font-weight: 600;
}

.drawer-version-tag {
  padding: 0 6px;
  background-color: var(--secondary-color);
  color: #303133;
  border-color: transparent;
}

.pc-version-inline {
  margin-left: 8px;
  font-size: 12px;
  color: var(--muted-text-color);
}
</style>
