<template>
  <div class="user-center-container">
    <div class="layout-container">
      <el-card class="user-info-card">
        <div class="card-header">
          <div class="card-title-group">
            <h2 class="page-title">个人中心</h2>
            <p class="page-subtitle">管理账号信息与安全设置</p>
          </div>
        </div>
        <el-tabs v-model="activeTab" class="user-center-tabs">
          <!-- 基本信息 Tab -->
          <el-tab-pane label="基本信息" name="profile">
            <div class="user-info-content">
              <div class="avatar-section">
                <el-avatar :size="80" :src="avatarUrl" class="user-avatar">
                  <template #default>
                    <span class="avatar-placeholder">
                      {{ userInfo && userInfo.username ? userInfo.username.charAt(0).toUpperCase() : 'U' }}
                    </span>
                  </template>
                </el-avatar>
                <div class="avatar-actions">
                  <el-button size="small" type="primary" @click="triggerAvatarSelect" :loading="isAvatarUploading">
                    更换头像
                  </el-button>
                  <el-button size="small" type="danger" plain @click="handleDeleteAvatar"
                    :disabled="!avatarUrl || isAvatarDeleting" :loading="isAvatarDeleting">
                    删除头像
                  </el-button>
                  <input ref="fileInputRef" type="file" accept="image/*" class="hidden-file-input"
                    @change="handleAvatarChange" />
                </div>
              </div>
              <div class="basic-info-section">
                <div class="info-row">
                  <span class="info-label">用户名</span>
                  <span class="info-value">{{ userInfo?.username || '未登录用户' }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">用户ID</span>
                  <span class="info-value">{{ userInfo?.id || '-' }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">当前角色</span>
                  <span class="info-value">{{ roleLabel }}</span>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 修改资料 Tab -->
          <el-tab-pane label="修改资料" name="edit">
            <div class="edit-card-inner">
              <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-position="left"
                label-width="120px" class="edit-form">
                <el-form-item label="用户名" prop="username">
                  <el-input v-model="editForm.username" placeholder="请输入用户名" maxlength="150" />
                </el-form-item>
                <el-form-item label="性别" prop="gender">
                  <el-select v-model="editForm.gender" placeholder="请选择性别">
                    <el-option label="未知" :value="0" />
                    <el-option label="男" :value="1" />
                    <el-option label="女" :value="2" />
                  </el-select>
                </el-form-item>
                <el-form-item label="手机号" prop="mobile">
                  <el-input v-model="editForm.mobile" placeholder="请输入手机号" maxlength="20" />
                </el-form-item>

                <!-- 邮箱修改区域 -->
                <el-form-item label="当前邮箱">
                  <span class="current-email">{{ userInfo?.email || '未设置' }}</span>
                </el-form-item>
                <el-form-item label="新邮箱" prop="email">
                  <el-input v-model="editForm.email" placeholder="不修改请留空" />
                </el-form-item>
                <el-form-item v-if="isEmailChanged" label="邮箱验证码" prop="email_code">
                  <div class="code-input-group">
                    <el-input v-model="editForm.email_code" placeholder="请输入验证码" maxlength="6" />
                    <el-button type="primary" :disabled="codeCooldown > 0 || isSendingCode"
                      :loading="isSendingCode" @click="handleSendCode">
                      {{ codeCooldown > 0 ? `${codeCooldown}s` : '获取验证码' }}
                    </el-button>
                  </div>
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" @click="handleSaveProfile" :loading="isSaving">保存修改</el-button>
                  <el-button @click="resetEditForm">重置</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- 修改密码 Tab -->
          <el-tab-pane label="修改密码" name="password">
            <div class="security-card-inner">
              <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-position="left"
                label-width="120px" class="password-form">
                <el-form-item label="当前密码" prop="current_password">
                  <el-input v-model="passwordForm.current_password" type="password" placeholder="请输入当前密码"
                    show-password />
                </el-form-item>
                <el-form-item label="新密码" prop="new_password">
                  <el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码"
                    show-password />
                </el-form-item>
                <el-form-item label="确认新密码" prop="confirm_password">
                  <el-input v-model="passwordForm.confirm_password" type="password" placeholder="请再次输入新密码"
                    show-password />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="handleChangePassword">修改密码</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>

    <!-- 裁剪头像对话框 -->
    <el-dialog v-model="cropDialogVisible" title="裁剪头像" width="400px" :close-on-click-modal="false"
      @opened="initCropper" @closed="destroyCropper">
      <div class="avatar-cropper-container">
        <img v-if="cropperImageUrl" :src="cropperImageUrl" ref="cropperImgRef" class="avatar-cropper-image" />
      </div>
      <template #footer>
        <el-button @click="handleCropCancel" :disabled="isAvatarUploading">取消</el-button>
        <el-button type="primary" @click="handleCropConfirm" :loading="isAvatarUploading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'
import { storeToRefs } from 'pinia'
import { ElMessageBox } from 'element-plus'
import { changePassword, uploadAvatar, deleteAvatar, updateUserInfo, sendEmailCode } from '@/api/user'
import { handleApiError, showApiErrorNotification, showErrorNotification, showSuccessNotification } from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { apiBase } from '@/api/index'

const activeTab = ref('profile')
const userStore = useUserStore()
const { user } = storeToRefs(userStore)
const userInfo = user

// ========== 头像相关 ==========
const isAvatarUploading = ref(false)
const isAvatarDeleting = ref(false)
const fileInputRef = ref(null)
const cropDialogVisible = ref(false)
const cropperImageUrl = ref('')
const cropperImgRef = ref(null)
const selectedAvatarFile = ref(null)
let cropperInstance = null
const MAX_AVATAR_SIZE = 2 * 1024 * 1024
const MAX_AVATAR_DIMENSION = 1024

const avatarUrl = computed(() => {
  if (!userInfo.value || !userInfo.value.id) return ''
  const base = apiBase || ''
  const trimmedBase = base.endsWith('/') ? base.slice(0, -1) : base
  let url = `${trimmedBase}/users/${userInfo.value.id}/avatar?size=200`
  if (userInfo.value.avatar_updated_at) {
    url += `&t=${encodeURIComponent(userInfo.value.avatar_updated_at)}`
  }
  return url
})

const roleLabel = computed(() => {
  if (!userInfo.value) return '普通用户'
  const r = userInfo.value.role
  if (r === 'super_admin') return '超级管理员'
  if (r === 'admin') return '管理员'
  if (r === 'moderator') return '审核员'
  return '普通用户'
})

// ========== 编辑资料相关 ==========
const editFormRef = ref(null)
const isSaving = ref(false)
const isSendingCode = ref(false)
const codeCooldown = ref(0)
let cooldownTimer = null

const editForm = reactive({
  username: '',
  gender: 0,
  mobile: '',
  email: '',
  email_code: ''
})

const isEmailChanged = computed(() => {
  return editForm.email && editForm.email !== (userInfo.value?.email || '')
})

const editRules = {
  username: [
    { required: true, message: '用户名不能为空', trigger: 'blur' },
    { min: 3, max: 150, message: '用户名长度在 3 到 150 个字符', trigger: 'blur' }
  ],
  mobile: [
    { max: 20, message: '手机号不能超过 20 个字符', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  email_code: [
    {
      validator: (rule, value, callback) => {
        if (isEmailChanged.value && !value) {
          callback(new Error('修改邮箱需要输入验证码'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const resetEditForm = () => {
  if (userInfo.value) {
    editForm.username = userInfo.value.username || ''
    editForm.gender = userInfo.value.gender ?? 0
    editForm.mobile = userInfo.value.mobile || ''
    editForm.email = userInfo.value.email || ''
    editForm.email_code = ''
  }
}

// 监听用户信息变化，同步到编辑表单
watch(userInfo, () => { resetEditForm() }, { immediate: true, deep: true })

const startCooldown = () => {
  codeCooldown.value = 60
  cooldownTimer = setInterval(() => {
    codeCooldown.value--
    if (codeCooldown.value <= 0) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

const handleSendCode = async () => {
  if (!editForm.email) {
    showErrorNotification('请先输入新邮箱地址')
    return
  }
  if (!isEmailChanged.value) {
    showErrorNotification('新邮箱与当前邮箱相同')
    return
  }
  isSendingCode.value = true
  try {
    const res = await sendEmailCode(editForm.email)
    if (res.success) {
      showSuccessNotification(res.msg || '验证码已发送，请查收邮箱')
      startCooldown()
    } else {
      showErrorNotification(res.msg || '验证码发送失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '验证码发送失败')
  } finally {
    isSendingCode.value = false
  }
}

const handleSaveProfile = async () => {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    isSaving.value = true
    try {
      // 构建提交数据，只提交有变化的字段
      const payload = {}
      const u = userInfo.value || {}
      if (editForm.username !== (u.username || '')) payload.username = editForm.username
      if (editForm.gender !== (u.gender ?? 0)) payload.gender = editForm.gender
      if (editForm.mobile !== (u.mobile || '')) payload.mobile = editForm.mobile
      if (isEmailChanged.value) {
        payload.email = editForm.email
        payload.email_code = editForm.email_code
      }

      if (Object.keys(payload).length === 0) {
        showErrorNotification('没有需要修改的内容')
        isSaving.value = false
        return
      }

      const res = await updateUserInfo(payload)
      if (res.success) {
        showSuccessNotification(res.msg || '修改成功')
        editForm.email_code = ''
        await fetchUserInfo()
      } else {
        showErrorNotification(res.msg || '修改失败')
      }
    } catch (error) {
      showApiErrorNotification(error, '修改失败')
    } finally {
      isSaving.value = false
    }
  })
}

// ========== 密码修改相关 ==========
const passwordFormRef = ref(null)
const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

const passwordRules = {
  current_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 30, message: '密码长度在 6 到 30 个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: ['blur', 'change']
    }
  ]
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      const res = await changePassword(
        passwordForm.current_password,
        passwordForm.new_password,
        passwordForm.confirm_password
      )
      if (res.success) {
        showSuccessNotification(res.msg || '密码修改成功，请重新登录')
        ElMessageBox.alert('密码已修改，请使用新密码重新登录。', '提示', {
          confirmButtonText: '确定',
          callback: () => {
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            window.location.href = '/login'
          }
        })
      } else {
        showErrorNotification(res.msg || '密码修改失败')
      }
    } catch (error) {
      showApiErrorNotification(error, '密码修改失败')
    }
  })
}

// ========== 头像操作 ==========
const fetchUserInfo = async () => {
  try {
    await userStore.fetchCurrentUser(true)
  } catch (error) {
    showApiErrorNotification(error, '获取用户信息失败')
  }
}

const triggerAvatarSelect = () => { fileInputRef.value?.click() }

const initCropper = () => {
  if (!cropperImgRef.value) return
  if (cropperInstance) { cropperInstance.destroy(); cropperInstance = null }
  cropperInstance = new Cropper(cropperImgRef.value, {
    aspectRatio: 1, viewMode: 1, dragMode: 'move', autoCropArea: 1, responsive: true, background: false
  })
}

const destroyCropper = () => {
  if (cropperInstance) { cropperInstance.destroy(); cropperInstance = null }
  cropperImageUrl.value = ''
  selectedAvatarFile.value = null
}

const readFileAsDataURL = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(reader.result)
  reader.onerror = () => reject(new Error('读取头像文件失败'))
  reader.readAsDataURL(file)
})

const loadImage = (src) => new Promise((resolve, reject) => {
  const img = new Image()
  img.onload = () => resolve(img)
  img.onerror = () => reject(new Error('头像图片加载失败'))
  img.src = src
})

const compressAvatarFile = async (file) => {
  const dataUrl = await readFileAsDataURL(file)
  const img = await loadImage(dataUrl)
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  const side = Math.min(img.width, img.height, MAX_AVATAR_DIMENSION)
  const sx = (img.width - side) / 2
  const sy = (img.height - side) / 2
  canvas.width = side; canvas.height = side
  ctx.clearRect(0, 0, side, side)
  ctx.drawImage(img, sx, sy, side, side, 0, 0, side, side)
  const toBlob = (quality) => new Promise((resolve, reject) => {
    canvas.toBlob((blob) => { blob ? resolve(blob) : reject(new Error('头像压缩失败')) }, 'image/jpeg', quality)
  })
  let quality = 0.9
  let blob = await toBlob(quality)
  while (blob.size > MAX_AVATAR_SIZE && quality > 0.4) { quality -= 0.1; blob = await toBlob(quality) }
  const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '')
  return new File([blob], `${nameWithoutExt || 'avatar'}.jpg`, { type: 'image/jpeg' })
}

const handleAvatarChange = async (event) => {
  const files = event.target.files
  if (!files || !files.length) return
  const file = files[0]
  if (!file.type.startsWith('image/')) { showErrorNotification('请选择图片文件'); event.target.value = ''; return }
  selectedAvatarFile.value = file
  cropperImageUrl.value = await readFileAsDataURL(file)
  cropDialogVisible.value = true
  event.target.value = ''
}

const handleCropCancel = () => { cropDialogVisible.value = false }

const handleCropConfirm = async () => {
  if (!cropperInstance) return
  isAvatarUploading.value = true
  try {
    const canvas = cropperInstance.getCroppedCanvas({ width: MAX_AVATAR_DIMENSION, height: MAX_AVATAR_DIMENSION })
    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob((b) => { b ? resolve(b) : reject(new Error('头像裁剪失败')) }, 'image/jpeg')
    })
    const baseName = selectedAvatarFile.value ? selectedAvatarFile.value.name.replace(/\.[^/.]+$/, '') : 'avatar'
    const croppedFile = new File([blob], `${baseName || 'avatar'}.jpg`, { type: 'image/jpeg' })
    const processedFile = await compressAvatarFile(croppedFile)
    const res = await uploadAvatar(processedFile)
    if (res.success) {
      showSuccessNotification(res.msg || '头像上传成功')
      await fetchUserInfo()
      cropDialogVisible.value = false
    } else {
      showErrorNotification(res.msg || '头像上传失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '头像上传失败')
  } finally {
    isAvatarUploading.value = false
  }
}

const handleDeleteAvatar = () => {
  if (!avatarUrl.value) return
  ElMessageBox.confirm('确定要删除当前头像吗？', '提示', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  }).then(async () => {
    isAvatarDeleting.value = true
    try {
      const res = await deleteAvatar()
      if (res.success) { showSuccessNotification(res.msg || '头像已删除'); await fetchUserInfo() }
      else { showErrorNotification(res.msg || '删除头像失败') }
    } catch (error) { showApiErrorNotification(error, '删除头像失败') }
    finally { isAvatarDeleting.value = false }
  }).catch(() => {})
}

onMounted(() => { fetchUserInfo() })
</script>

<style scoped>
.user-center-container {
  width: 100%;
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
  color: var(--text-color);
  display: flex;
  justify-content: center;
}
.layout-container {
  width: 100%;
  max-width: 900px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.user-info-card {
  background-color: var(--card-background);
  border-color: var(--border-color);
}
.user-center-tabs { margin-top: 8px; }
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 20px;
}
.card-title-group { display: flex; flex-direction: column; gap: 4px; }
.page-title { margin: 0; font-size: 20px; }
.page-subtitle { margin: 0; font-size: 13px; color: var(--muted-text-color); }
.user-info-content { display: flex; gap: 24px; align-items: center; }
.avatar-section { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.user-avatar { border: 2px solid var(--secondary-color); }
.avatar-placeholder {
  display: inline-flex; align-items: center; justify-content: center;
  width: 100%; height: 100%; font-size: 32px;
  background-color: var(--hover-color); color: var(--secondary-color);
}
.avatar-actions { display: flex; gap: 8px; }
.avatar-cropper-container {
  width: 100%; height: 320px; display: flex;
  align-items: center; justify-content: center; overflow: hidden;
}
.avatar-cropper-image { max-width: 100%; max-height: 100%; display: block; }
.hidden-file-input { display: none; }
.basic-info-section { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.info-row { display: flex; justify-content: space-between; align-items: center; }
.info-label { font-size: 14px; color: var(--muted-text-color); }
.info-value { font-size: 14px; color: var(--text-color); }
.edit-card-inner { padding-top: 8px; }
.edit-form { max-width: 500px; }
.security-card-inner { padding-top: 8px; }
.password-form { max-width: 500px; }
.current-email { font-size: 14px; color: var(--muted-text-color); }
.code-input-group { display: flex; gap: 8px; width: 100%; }
.code-input-group .el-input { flex: 1; }
@media (max-width: 768px) {
  .user-info-content { flex-direction: column; align-items: flex-start; }
  .avatar-section { align-items: flex-start; }
}
</style>
