<template>
  <div class="admin-mute-container">
    <div class="layout-container page-layout-inner">
      <el-card class="filter-card" shadow="hover">
        <div class="filter-bar">
          <el-input
            v-model="searchForm.search"
            placeholder="按用户名或邮箱搜索"
            class="filter-input"
            clearable
            @keyup.enter="handleSearch"
          />
          <el-select
            v-model="searchForm.role"
            class="filter-select"
            clearable
            placeholder="按角色筛选"
          >
            <el-option label="全部角色" :value="''" />
            <el-option label="管理员" value="admin" />
            <el-option label="审核员" value="moderator" />
            <el-option label="普通用户" value="user" />
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
            <h2 class="page-title">禁言管理</h2>
            <p class="page-subtitle">对用户进行禁言或解禁，禁言仅限制评论与回复</p>
          </div>
        </div>

        <el-table
          v-loading="loading"
          :data="userList"
          border
        >
          <el-table-column
            prop="username"
            label="用户名"
            show-overflow-tooltip
          />
          <el-table-column
            prop="email"
            label="邮箱"
            show-overflow-tooltip
          />
          <el-table-column
            prop="role"
            label="角色"
          />
          <el-table-column
            prop="isMuted"
            label="禁言状态"
            align="center"
            header-align="center"
          >
            <template #default="scope">
              <el-tag :type="scope.row.isMuted ? 'danger' : 'success'">
                {{ scope.row.isMuted ? '禁言中' : '正常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="mutedUntil"
            label="禁言截止时间"
            align="center"
            header-align="center"
          >
            <template #default="scope">
              <span v-if="scope.row.isMuted">
                {{ formatMutedUntil(scope.row.mutedUntil) }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            fixed="right"
            align="center"
            header-align="center"
          >
            <template #default="scope">
              <el-button
                v-if="scope.row.isMuted"
                type="primary"
                size="small"
                plain
                @click="handleUnmute(scope.row)"
              >
                解禁
              </el-button>
              <el-button
                v-else
                type="danger"
                size="small"
                plain
                @click="openMuteDialog(scope.row)"
              >
                禁言
              </el-button>
              <el-button
                v-if="scope.row.isMuted && scope.row.muteReason"
                type="info"
                size="small"
                text
                @click="handleViewMuteReason(scope.row)"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>

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

      <el-dialog
        v-model="muteDialogVisible"
        title="设置禁言"
        width="420px"
        destroy-on-close
      >
        <div class="mute-dialog-body">
          <div class="mute-dialog-text">
            确认要对用户「{{ muteTargetUser?.username || muteTargetUser?.email || '' }}」进行禁言吗？
          </div>
          <div class="mute-dialog-duration">
            <span class="mute-dialog-label">禁言时长</span>
            <el-radio-group v-model="muteDuration">
              <el-radio-button label="1d">
                1天
              </el-radio-button>
              <el-radio-button label="7d">
                7天
              </el-radio-button>
              <el-radio-button label="30d">
                30天
              </el-radio-button>
              <el-radio-button label="permanent">
                永久
              </el-radio-button>
            </el-radio-group>
          </div>
          <div class="mute-dialog-reason">
            <span class="mute-dialog-label">禁言原因</span>
            <el-select
              v-model="muteReason"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              placeholder="请选择或输入禁言原因"
              class="mute-reason-select"
            >
              <el-option
                v-for="item in commonMuteReasons"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </div>
        </div>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="closeMuteDialog">
              取消
            </el-button>
            <el-button type="primary" :loading="muteSubmitting" @click="handleConfirmMute">
              确认禁言
            </el-button>
          </span>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { getAdminUsers, muteUser, unmuteUser } from '@/api/admin'
import { handleApiError, showApiErrorNotification, showErrorNotification, showInfoNotification, showSuccessNotification, showWarningNotification } from '@/utils/api'

const loading = ref(false)
const userList = ref([])

const searchForm = reactive({
  search: '',
  role: ''
})

const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

const muteDialogVisible = ref(false)
const muteTargetUser = ref(null)
const muteDuration = ref('7d')
const muteSubmitting = ref(false)

const commonMuteReasons = [
  '发布垃圾广告或恶意推广',
  '频繁刷屏影响他人使用',
  '发布不适宜或违规内容',
  '恶意攻击或骚扰其他用户',
  '其他'
]

const muteReason = ref([])

const fetchUserList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize
    }
    if (searchForm.search) {
      params.search = searchForm.search
    }
    if (searchForm.role) {
      params.role = searchForm.role
    }
    const response = await getAdminUsers(params)
    let items = []
    let total = 0
    if (response && Array.isArray(response.data)) {
      items = response.data
      total = response.pagination ? response.pagination.total : items.length
    } else if (response && response.data && Array.isArray(response.data)) {
      items = response.data
      total = response.pagination ? response.pagination.total : items.length
    } else if (response && response.items) {
      items = response.items
      total = response.pagination ? response.pagination.total : (typeof response.total === 'number' ? response.total : items.length)
    }
    userList.value = items
    pagination.total = typeof total === 'number' ? total : 0
  } catch (error) {
    showApiErrorNotification(error, '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.currentPage = 1
  fetchUserList()
}

const resetSearch = () => {
  searchForm.search = ''
  searchForm.role = ''
  pagination.currentPage = 1
  fetchUserList()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchUserList()
}

const handleCurrentChange = (page) => {
  pagination.currentPage = page
  fetchUserList()
}

const formatMutedUntil = (value) => {
  if (!value) {
    return '永久禁言'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '-'
  }
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

const openMuteDialog = (row) => {
  muteTargetUser.value = row
  muteDuration.value = '7d'
  muteReason.value = []
  muteDialogVisible.value = true
}

const closeMuteDialog = () => {
  muteDialogVisible.value = false
  muteTargetUser.value = null
}

const handleConfirmMute = async () => {
  if (!muteTargetUser.value || !muteTargetUser.value.id) {
    return
  }
  muteSubmitting.value = true
  try {
    const reasons = Array.isArray(muteReason.value)
      ? muteReason.value.map((item) => String(item || '').trim()).filter(Boolean)
      : []
    if (!reasons.length) {
      showWarningNotification('请至少选择或输入一个禁言原因')
      muteSubmitting.value = false
      return
    }
    const reasonText = reasons.join('；')
    await muteUser(muteTargetUser.value.id, muteDuration.value, reasonText)
    showSuccessNotification('用户已禁言')
    muteDialogVisible.value = false
    fetchUserList()
  } catch (error) {
    showApiErrorNotification(error, '禁言用户失败')
  } finally {
    muteSubmitting.value = false
  }
}

const handleUnmute = async (row) => {
  if (!row || !row.id) {
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认要解除用户「${row.username || row.email || row.id}」的禁言吗？`,
      '确认解禁',
      {
        type: 'warning'
      }
    )
  } catch {
    return
  }
  try {
    await unmuteUser(row.id)
    showSuccessNotification('已解除禁言')
    fetchUserList()
  } catch (error) {
    showApiErrorNotification(error, '解除禁言失败')
  }
}

const handleViewMuteReason = (row) => {
  if (!row) {
    return
  }
  const reason = (row.muteReason || '').trim()
  if (!reason) {
    showInfoNotification('暂无禁言原因信息')
    return
  }
  ElMessageBox.alert(reason, '禁言原因', {
    confirmButtonText: '知道了'
  })
}

onMounted(() => {
  fetchUserList()
})
</script>

<style scoped>
.admin-mute-container {
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
  gap: 16px;
}

.filter-card {
  border-radius: 12px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-input {
  flex: 1;
}

.filter-select {
  width: 160px;
}

.list-card {
  border-radius: 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-title-group {
  display: flex;
  flex-direction: column;
}

.page-title {
  margin: 0;
  font-size: 20px;
}

.page-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--muted-text-color);
}

.pagination-section {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.mute-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mute-dialog-text {
  font-size: 14px;
}

.mute-dialog-duration {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mute-dialog-label {
  font-size: 13px;
  color: var(--muted-text-color);
}

.mute-dialog-reason {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mute-reason-select {
  width: 100%;
}
</style>
