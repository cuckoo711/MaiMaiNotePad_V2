<template>
  <div class="persona-upload-container">
    <div class="layout-container">
      <el-card class="upload-card" shadow="hover">
        <div class="card-header">
          <div class="card-title-group">
            <h2 class="page-title">创建人设卡</h2>
            <p class="page-subtitle">上传人设文件以创建可复用的人设卡</p>
          </div>
          <div class="card-actions">
            <el-button type="default" @click="goBackToList">
              返回我的人设卡
            </el-button>
          </div>
        </div>
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="120px"
          class="upload-form"
        >
          <el-form-item label="人设卡名称" prop="name">
            <el-input
              v-model="form.name"
              placeholder="请输入人设卡名称"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="人设卡描述" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              placeholder="请输入人设卡的用途或简介"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="版权所有者">
            <el-input
              v-model="form.copyright_owner"
              placeholder="默认使用当前用户名，可选填"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="公开范围">
            <el-radio-group v-model="form.visibility">
              <el-radio label="private">仅自己可见</el-radio>
              <el-radio label="public">申请公开到人设卡广场（需审核）</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="标签">
            <div class="tags-editor">
              <el-tag
                v-for="tag in form.tags"
                :key="tag"
                closable
                size="small"
                @close="removeUploadTag(tag)"
              >
                {{ tag }}
              </el-tag>
              <el-input
                v-model="uploadTagInput"
                class="tag-input"
                size="small"
                placeholder="输入标签，按逗号分隔"
                @keydown.enter.stop.prevent
                @keyup="handleUploadTagInputKeyup"
                @blur="commitUploadTagInput"
              />
            </div>
          </el-form-item>
          <el-form-item label="补充说明">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="3"
              placeholder="可填写人设卡整体说明或备注"
              maxlength="1000"
              show-word-limit
            />
            <div class="form-tip">
              补充说明仅自己可见，不会在人设卡广场等公共页面展示
            </div>
          </el-form-item>
          <el-form-item label="人设卡文件" required>
            <el-upload
              class="upload-area"
              drag
              multiple
              :auto-upload="false"
              :file-list="fileList"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :limit="2"
              accept=".toml"
            >
              <el-icon class="upload-icon">
                <UploadFilled />
              </el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或
                <em>点击选择文件</em>
              </div>
              <div class="el-upload__tip">
                仅支持 .toml 文件，人设卡必须包含 1-2 个文件，单个文件不超过 100MB
              </div>
            </el-upload>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="submitting"
              @click="handleSubmit"
            >
              提交创建
            </el-button>
            <el-button @click="resetForm" :disabled="submitting">
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadPersonaCard } from '@/api/persona'
import { handleApiError, showApiErrorNotification, showErrorNotification, showSuccessNotification } from '@/utils/api'

const router = useRouter()

const formRef = ref()

const form = reactive({
  name: '',
  description: '',
  copyright_owner: '',
  visibility: 'private',
  tags: [],
  content: ''
})

const rules = {
  name: [
    { required: true, message: '请输入人设卡名称', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入人设卡描述', trigger: 'blur' }
  ]
}

const MAX_PERSONA_FILES = 1
const MAX_PERSONA_FILE_SIZE_MB = 100
const MAX_PERSONA_FILE_SIZE_BYTES = MAX_PERSONA_FILE_SIZE_MB * 1024 * 1024

const fileList = ref([])
const submitting = ref(false)
const uploadTagInput = ref('')

const handleFileChange = (file, files) => {
  const validFiles = []
  for (const item of files) {
    const raw = item.raw || item
    if (!raw || !raw.name) {
      continue
    }
    const lowerName = raw.name.toLowerCase()
    if (!lowerName.endsWith('.toml')) {
      showErrorNotification(`不支持的文件类型: ${raw.name}，仅支持 .toml 文件`)
      continue
    }
    if (typeof raw.size === 'number' && raw.size > MAX_PERSONA_FILE_SIZE_BYTES) {
      showErrorNotification(`文件过大: ${raw.name}，单个文件不超过 ${MAX_PERSONA_FILE_SIZE_MB}MB`)
      continue
    }
    validFiles.push(item)
    if (validFiles.length >= MAX_PERSONA_FILES) {
      break
    }
  }
  if (!validFiles.length && files.length) {
    showErrorNotification('请选择 1 个符合要求的 .toml 文件，文件名必须为 bot_config.toml')
  }
  fileList.value = validFiles
}

const handleFileRemove = (file, files) => {
  fileList.value = files
}

const buildFormData = () => {
  const formData = new FormData()
  fileList.value.forEach((item) => {
    const raw = item.raw || item
    if (raw) {
      formData.append('files', raw)
    }
  })
  formData.append('name', form.name)
  formData.append('description', form.description)
  if (form.visibility === 'public') {
    formData.append('is_public', 'true')
  }
  if (form.copyright_owner) {
    formData.append('copyright_owner', form.copyright_owner)
  }
  if (form.content) {
    formData.append('content', form.content)
  }
  if (form.tags) {
    const cleanedTags = Array.isArray(form.tags)
      ? form.tags.filter((item) => item && String(item).trim())
      : []
    const tagsValue = cleanedTags.join(',')
    if (tagsValue) {
      formData.append('tags', tagsValue)
    }
  }
  return formData
}

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

const handleUploadTagInputKeyup = (event) => {
  if (event.key === ',' || event.key === '，') {
    event.preventDefault()
    addTagsFromInput(form.tags, uploadTagInput.value)
    uploadTagInput.value = ''
  }
}

const commitUploadTagInput = () => {
  if (!uploadTagInput.value) {
    return
  }
  addTagsFromInput(form.tags, uploadTagInput.value)
  uploadTagInput.value = ''
}

const removeUploadTag = (tag) => {
  const index = form.tags.indexOf(tag)
  if (index !== -1) {
    form.tags.splice(index, 1)
  }
}

const handleSubmit = () => {
  if (!formRef.value) {
    return
  }
  formRef.value.validate(async (valid) => {
    if (!valid) {
      return
    }
    if (!fileList.value.length) {
      showErrorNotification('请先选择一个 bot_config.toml 配置文件')
      return
    }
    submitting.value = true
    try {
      const formData = buildFormData()
      const response = await uploadPersonaCard(formData)
      if (response.success) {
        showSuccessNotification(response.message || '人设卡创建成功')
        resetForm()
        router.push('/my-persona')
      } else {
        showErrorNotification(response.message || '人设卡创建失败')
      }
    } catch (error) {
      showApiErrorNotification(error, '人设卡创建失败')
    } finally {
      submitting.value = false
    }
  })
}

const resetForm = () => {
  form.name = ''
  form.description = ''
  form.copyright_owner = ''
  form.tags = []
  form.content = ''
  uploadTagInput.value = ''
  fileList.value = []
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

const goBackToList = () => {
  router.push('/my-persona')
}
</script>

<style scoped>
.persona-upload-container {
  padding: 24px;
}

.layout-container {
  max-width: 960px;
  margin: 0 auto;
}

.upload-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
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

.tags-editor {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-input {
  width: 260px;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-form {
  margin-top: 8px;
}

.upload-area {
  width: 100%;
}

.upload-icon {
  font-size: 40px;
  color: var(--secondary-color);
}

.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted-text-color);
}
</style>
