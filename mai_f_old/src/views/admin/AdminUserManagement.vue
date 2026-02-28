<template>
  <div class="admin-user-container">
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
            <h2 class="page-title">用户管理与统计</h2>
            <p class="page-subtitle">查看平台用户信息，调整角色或禁用用户</p>
          </div>
          <div class="card-actions">
            <el-button type="primary" @click="handleOpenCreateDialog">
              创建新用户
            </el-button>
          </div>
        </div>

        <div class="user-table-wrapper">
          <el-table
            v-loading="loading"
            :data="userList"
            border
            style="width: 100%"
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
            >
              <template #default="scope">
                <template v-if="scope.row.role === 'super_admin'">
                  <el-tag type="danger">
                    超级管理员
                  </el-tag>
                </template>
                <template v-else>
                  <el-select
                    v-model="scope.row.role"
                    size="small"
                    @change="(value) => handleChangeRole(scope.row, value)"
                  >
                    <el-option label="普通用户" value="user" />
                    <el-option label="审核员" value="moderator" />
                    <el-option label="管理员" value="admin" />
                  </el-select>
                </template>
              </template>
            </el-table-column>
            <el-table-column
              prop="status"
              label="状态"
              Width="150"
              align="center"
              header-align="center"
            >
              <template #default="scope">
                <template v-if="!scope.row.is_active">
                  <el-tag type="info">
                    已删除
                  </el-tag>
                </template>
                <template v-else-if="isUserBanned(scope.row)">
                  <div class="status-cell">
                    <el-tag type="danger">
                      封禁中
                    </el-tag>
                    <div v-if="scope.row.lockedUntil" class="status-extra">
                      至 {{ formatDate(scope.row.lockedUntil) }}
                    </div>
                  </div>
                </template>
                <template v-else>
                  <el-tag type="success">
                    正常
                  </el-tag>
                </template>
              </template>
            </el-table-column>
            <el-table-column
              prop="lastLoginAt"
              label="登录时间"
            >
              <template #default="scope">
                {{ formatDate(scope.row.lastLoginAt) || '-' }}
              </template>
            </el-table-column>
            <el-table-column
              prop="createdAt"
              label="注册时间"
            >
              <template #default="scope">
                {{ formatDate(scope.row.createdAt) }}
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
                v-if="isUserBanned(scope.row)"
                type="primary"
                size="small"
                plain
                @click="handleUnbanUser(scope.row)"
              >
                解封
              </el-button>
              <el-button
                v-else
                type="danger"
                size="small"
                plain
                @click="handleOpenBanDialog(scope.row)"
              >
                封禁
              </el-button>
              <el-button
                v-if="isUserBanned(scope.row) && scope.row.banReason"
                type="info"
                size="small"
                text
                @click="handleViewBanReason(scope.row)"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
          </el-table>
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

      <el-dialog
        v-model="createDialogVisible"
        title="创建新用户"
        width="420px"
        destroy-on-close
      >
        <el-form
          :model="createForm"
          :rules="createRules"
          ref="createFormRef"
          label-width="80px"
        >
          <el-form-item label="用户名" prop="username">
            <el-input v-model="createForm.username" autocomplete="off" />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="createForm.email" autocomplete="off" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="createForm.password"
              type="password"
              autocomplete="new-password"
              show-password
            />
          </el-form-item>
          <el-form-item label="角色" prop="role">
            <el-select v-model="createForm.role" placeholder="请选择角色">
              <el-option label="普通用户" value="user" />
              <el-option label="审核员" value="moderator" />
              <el-option label="管理员" value="admin" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="handleCloseCreateDialog">
              取消
            </el-button>
            <el-button type="primary" :loading="createSubmitting" @click="handleSubmitCreate">
              确认创建
            </el-button>
          </span>
        </template>
      </el-dialog>
      <el-dialog
        v-model="banDialogVisible"
        title="封禁用户"
        width="420px"
        destroy-on-close
      >
        <div class="ban-dialog-body">
          <div class="ban-dialog-text">
            确认要封禁用户「{{ banTargetUser?.username || banTargetUser?.email || '' }}」吗？
          </div>
          <div class="ban-dialog-duration">
            <span class="ban-dialog-label">封禁时长</span>
            <el-radio-group v-model="banDuration">
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
          <div class="ban-dialog-reason">
            <span class="ban-dialog-label">封禁原因</span>
            <el-select
              v-model="banReason"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              placeholder="请选择或输入封禁原因"
              class="ban-reason-select"
            >
              <el-option
                v-for="item in commonBanReasons"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </div>
        </div>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="handleCloseBanDialog">
              取消
            </el-button>
            <el-button type="primary" @click="handleConfirmBan">
              确认封禁
            </el-button>
          </span>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { getAdminUsers, updateUserRole, deleteUser, createUserByAdmin, banUser, unbanUser } from '@/api/admin'
import { handleApiError, showApiErrorNotification, showErrorNotification, showSuccessNotification, showWarningNotification } from '@/utils/api'

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

const createDialogVisible = ref(false)
const createSubmitting = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  username: '',
  email: '',
  password: '',
  role: 'user'
})

const banDialogVisible = ref(false)
const banTargetUser = ref(null)
const banDuration = ref('7d')

const commonBanReasons = [
  '发布垃圾广告或恶意推广',
  '频繁刷屏影响他人使用',
  '发布不适宜或违规内容',
  '恶意攻击或骚扰其他用户',
  '多次违规或恶意行为',
  '其他'
]

const banReason = ref([])

const createRules = {
  username: [
    {
      required: true,
      message: '请输入用户名',
      trigger: 'blur'
    }
  ],
  email: [
    {
      required: true,
      message: '请输入邮箱',
      trigger: 'blur'
    },
    {
      type: 'email',
      message: '邮箱格式不正确',
      trigger: ['blur', 'change']
    }
  ],
  password: [
    {
      required: true,
      message: '请输入密码',
      trigger: 'blur'
    },
    {
      min: 8,
      message: '密码长度至少8位',
      trigger: 'blur'
    }
  ],
  role: [
    {
      required: true,
      message: '请选择角色',
      trigger: 'change'
    }
  ]
}

const formatDate = (value) => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

const isUserBanned = (row) => {
  if (!row || !row.lockedUntil) {
    return false
  }
  const date = new Date(row.lockedUntil)
  if (Number.isNaN(date.getTime())) {
    return false
  }
  return date.getTime() > Date.now()
}

const fetchUserList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      limit: pagination.pageSize
    }
    if (searchForm.search) {
      params.search = searchForm.search
    }
    if (searchForm.role) {
      params.role = searchForm.role
    }
    const response = await getAdminUsers(params)
    const items = (response && Array.isArray(response.data)) ? response.data : []
    userList.value = items
    pagination.total = typeof response.total === 'number' ? response.total : items.length
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

const handleChangeRole = async (row, newRole) => {
  if (!row || !row.id || !newRole) {
    return
  }
  try {
    await updateUserRole(row.id, newRole)
    showSuccessNotification('角色更新成功')
    fetchUserList()
  } catch (error) {
    showApiErrorNotification(error, '更新用户角色失败')
    fetchUserList()
  }
}

const handleOpenBanDialog = (row) => {
  if (!row || !row.id) {
    return
  }
  banTargetUser.value = row
  banDuration.value = '7d'
  banReason.value = []
  banDialogVisible.value = true
}

const handleCloseBanDialog = () => {
  banDialogVisible.value = false
  banTargetUser.value = null
}

const handleConfirmBan = async () => {
  if (!banTargetUser.value || !banTargetUser.value.id) {
    return
  }
  try {
    const reasons = Array.isArray(banReason.value)
      ? banReason.value.map((item) => String(item || '').trim()).filter(Boolean)
      : []
    if (!reasons.length) {
      showWarningNotification('请至少选择或输入一个封禁原因')
      return
    }
    const reasonText = reasons.join('；')
    await banUser(banTargetUser.value.id, banDuration.value, reasonText)
    showSuccessNotification('用户已封禁')
    handleCloseBanDialog()
    fetchUserList()
  } catch (error) {
    showApiErrorNotification(error, '封禁用户失败')
  }
}

const handleViewBanReason = (row) => {
  if (!row) {
    return
  }
  const reason = (row.banReason || '').trim()
  if (!reason) {
    showInfoNotification('暂无封禁原因信息')
    return
  }
  ElMessageBox.alert(reason, '封禁原因', {
    confirmButtonText: '知道了'
  })
}

const handleUnbanUser = async (row) => {
  if (!row || !row.id) {
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认要解封用户「${row.username || row.email || row.id}」吗？`,
      '确认解封',
      {
        type: 'warning'
      }
    )
  } catch {
    return
  }
  try {
    await unbanUser(row.id)
    showSuccessNotification('用户已解封')
    fetchUserList()
  } catch (error) {
    showApiErrorNotification(error, '解封用户失败')
    fetchUserList()
  }
}

const handleDeleteUser = async (row) => {
  if (!row || !row.id) {
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认要删除用户「${row.username || row.email || row.id}」吗？删除后将无法恢复，该用户将无法再次登录。`,
      '确认删除账号',
      {
        type: 'warning'
      }
    )
  } catch {
    return
  }
  try {
    await deleteUser(row.id)
    showSuccessNotification('用户账号已删除')
    fetchUserList()
  } catch (error) {
    showApiErrorNotification(error, '删除用户失败')
    fetchUserList()
  }
}

const handleOpenCreateDialog = () => {
  createForm.username = ''
  createForm.email = ''
  createForm.password = ''
  createForm.role = 'user'
  createDialogVisible.value = true
}

const handleCloseCreateDialog = () => {
  createDialogVisible.value = false
}

const handleSubmitCreate = () => {
  if (!createFormRef.value) {
    return
  }
  createFormRef.value.validate(async (valid) => {
    if (!valid) {
      return
    }
    if (createSubmitting.value) {
      return
    }
    createSubmitting.value = true
    try {
      const payload = {
        username: createForm.username,
        email: createForm.email,
        password: createForm.password,
        role: createForm.role
      }
      await createUserByAdmin(payload)
      showSuccessNotification('创建用户成功')
      createDialogVisible.value = false
      fetchUserList()
    } catch (error) {
      const message = handleApiError(error, '创建用户失败')
      showErrorNotification(message)
    } finally {
      createSubmitting.value = false
    }
  })
}

onMounted(() => {
  fetchUserList()
})
</script>

<style scoped>
.admin-user-container {
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
  width: 260px;
}

.filter-select {
  width: 180px;
}

.list-card {
  margin-top: 16px;
  border-radius: 12px;
  width: 100%;
  box-sizing: border-box;
}

.card-header {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  margin-bottom: 16px;
}

.card-title-group {
  display: flex;
  flex-direction: column;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
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

.stats-summary {
  display: flex;
  gap: 16px;
}

.stats-item {
  min-width: 100px;
  text-align: right;
}

.stats-label {
  font-size: 12px;
  color: var(--muted-text-color);
}

.user-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.stats-value {
  margin-top: 4px;
  font-size: 16px;
  font-weight: 600;
}

.status-cell {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
}

.status-extra {
  margin-left: 6px;
  font-size: 12px;
  color: var(--muted-text-color);
}

.ban-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ban-dialog-text {
  font-size: 14px;
}

.ban-dialog-duration {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ban-dialog-label {
  font-size: 13px;
  color: var(--muted-text-color);
}

.ban-dialog-reason {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ban-reason-select {
  width: 100%;
}

.pagination-section {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
