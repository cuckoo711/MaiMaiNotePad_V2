<template>
  <div class="admin-announcement-container">
    <div class="layout-container page-layout-inner">
      <el-card class="form-card" shadow="hover">
        <div class="card-header">
          <div class="card-title-group">
            <h2 class="page-title">发布公告</h2>
            <p class="page-subtitle">
              向所有用户、所有管理员或所有审核员发送一条站内公告
            </p>
          </div>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="80px"
          class="announcement-form"
        >
          <el-form-item label="发送范围" prop="scope">
            <el-radio-group v-model="form.scope">
              <el-radio-button label="all">
                所有人
              </el-radio-button>
              <el-radio-button label="admins">
                所有管理员
              </el-radio-button>
              <el-radio-button label="moderators">
                所有审核员
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="标题" prop="title">
            <el-input
              v-model="form.title"
              placeholder="请输入公告标题"
              maxlength="80"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="内容" prop="content">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="8"
              placeholder="请输入公告内容，将以站内信形式发送给指定用户"
              maxlength="2000"
              show-word-limit
            />
          </el-form-item>
        </el-form>

        <div class="form-footer">
          <el-button @click="handleReset">
            清空
          </el-button>
          <el-button
            type="primary"
            :loading="submitting"
            @click="handleSubmit"
          >
            发布公告
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { sendMessage } from '@/api/messages'
import { getAdminUsers } from '@/api/admin'
import { handleApiError, showApiErrorNotification, showErrorNotification, showSuccessNotification, showWarningNotification } from '@/utils/api'

const formRef = ref(null)

const form = reactive({
  scope: 'all',
  title: '',
  content: ''
})

const rules = {
  scope: [
    {
      required: true,
      message: '请选择发送范围',
      trigger: 'change'
    }
  ],
  title: [
    {
      required: true,
      message: '请输入公告标题',
      trigger: 'blur'
    }
  ],
  content: [
    {
      required: true,
      message: '请输入公告内容',
      trigger: 'blur'
    }
  ]
}

const submitting = ref(false)

const loadRecipientsByRole = async (role) => {
  const params = {
    page: 1,
    limit: 500,
    role
  }
  const response = await getAdminUsers(params)
  let list = []
  if (response && Array.isArray(response.data)) {
    list = response.data
  } else if (response && response.data && Array.isArray(response.data)) {
    list = response.data
  } else if (response && Array.isArray(response.items)) {
    list = response.items
  }
  return list.map((item) => item.id).filter(Boolean)
}

const handleSubmit = async () => {
  if (!formRef.value) {
    return
  }

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    const payload = {
      title: form.title,
      content: form.content,
    }

    if (form.scope === 'all') {
      // target_type=3 表示系统通知（全员），后端会自动查询所有用户
      payload.target_type = 3
    } else if (form.scope === 'admins') {
      const recipientIds = await loadRecipientsByRole('admin')
      if (!recipientIds.length) {
        showWarningNotification('当前没有管理员账号可发送')
        submitting.value = false
        return
      }
      // target_type=0 表示指定用户
      payload.target_type = 0
      payload.target_user = recipientIds
    } else if (form.scope === 'moderators') {
      const recipientIds = await loadRecipientsByRole('moderator')
      if (!recipientIds.length) {
        showWarningNotification('当前没有审核员账号可发送')
        submitting.value = false
        return
      }
      payload.target_type = 0
      payload.target_user = recipientIds
    }

    await sendMessage(payload)
    showSuccessNotification('公告已发布')
    handleReset()
  } catch (error) {
    showApiErrorNotification(error, '发布公告失败')
  } finally {
    submitting.value = false
  }
}

const handleReset = () => {
  form.scope = 'all'
  form.title = ''
  form.content = ''
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}
</script>

<style scoped>
.admin-announcement-container {
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

.form-card {
  border-radius: 12px;
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
  gap: 4px;
}

.page-title {
  margin: 0;
  font-size: 20px;
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--muted-text-color);
}

.announcement-form {
  max-width: 720px;
}

.form-footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
