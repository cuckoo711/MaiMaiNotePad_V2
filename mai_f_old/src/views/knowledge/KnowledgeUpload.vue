<template>
  <div class="knowledge-upload-container">
    <div class="layout-container">
      <el-card class="upload-card" shadow="hover">
        <div class="card-header">
          <div class="card-title-group">
            <h2 class="page-title">上传知识库</h2>
            <p class="page-subtitle">支持上传多个文本文件组成一个知识库</p>
          </div>
          <div class="card-actions">
            <el-button type="default" @click="goBackToList">
              返回我的知识库
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
          <el-form-item label="知识库名称" prop="name">
            <el-input
              v-model="form.name"
              placeholder="请输入知识库名称"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="知识库描述" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              placeholder="请输入知识库的用途或简介"
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
              <el-radio label="public">申请公开到知识库广场（需审核）</el-radio>
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
              placeholder="可填写知识库整体说明或备注"
              maxlength="1000"
              show-word-limit
            />
            <div class="form-tip">
              补充说明仅自己可见，不会在知识库广场等公共页面展示
            </div>
          </el-form-item>
          <el-form-item label="知识库文件" required>
            <el-upload
              class="upload-area"
              drag
              multiple
              :auto-upload="false"
              :file-list="fileList"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :limit="100"
              accept=".txt,.json"
            >
              <el-icon class="upload-icon">
                <UploadFilled />
              </el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或
                <em>点击选择文件</em>
              </div>
              <div class="el-upload__tip">
                仅支持 .txt/.json 文件，最多 100 个，单个文件不超过 100MB
              </div>
            </el-upload>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="submitting"
              @click="handleSubmit"
            >
              提交上传
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
import { uploadKnowledgeBase } from '@/api/knowledge'
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
    { required: true, message: '请输入知识库名称', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入知识库描述', trigger: 'blur' }
  ]
}

const fileList = ref([])
const submitting = ref(false)
const uploadTagInput = ref('')

const readFileAsText = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      resolve(reader.result || '')
    }
    reader.onerror = () => {
      reject(new Error('文件读取失败'))
    }
    reader.readAsText(file)
  })
}

const validateKnowledgeJsonStructure = (data) => {
  if (!data || typeof data !== 'object') {
    return 'JSON 根节点必须是对象'
  }
  if (!Array.isArray(data.docs)) {
    return '缺少 docs 数组字段或类型不正确'
  }
  if (typeof data.avg_ent_chars !== 'number') {
    return '缺少 avg_ent_chars 数值字段或类型不正确'
  }
  if (typeof data.avg_ent_words !== 'number') {
    return '缺少 avg_ent_words 数值字段或类型不正确'
  }
  for (let i = 0; i < data.docs.length; i += 1) {
    const doc = data.docs[i]
    if (!doc || typeof doc !== 'object') {
      return `docs[${i}] 必须是对象`
    }
    if (typeof doc.idx !== 'string') {
      return `docs[${i}].idx 必须是字符串`
    }
    if (typeof doc.passage !== 'string') {
      return `docs[${i}].passage 必须是字符串`
    }
    if (!Array.isArray(doc.extracted_entities)) {
      return `docs[${i}].extracted_entities 必须是数组`
    }
    for (let j = 0; j < doc.extracted_entities.length; j += 1) {
      if (typeof doc.extracted_entities[j] !== 'string') {
        return `docs[${i}].extracted_entities[${j}] 必须是字符串`
      }
    }
    if (!Array.isArray(doc.extracted_triples)) {
      return `docs[${i}].extracted_triples 必须是数组`
    }
    for (let k = 0; k < doc.extracted_triples.length; k += 1) {
      const triple = doc.extracted_triples[k]
      if (!Array.isArray(triple) || triple.length !== 3) {
        return `docs[${i}].extracted_triples[${k}] 必须是长度为 3 的数组`
      }
      if (typeof triple[0] !== 'string' || typeof triple[1] !== 'string' || typeof triple[2] !== 'string') {
        return `docs[${i}].extracted_triples[${k}] 的每个元素必须是字符串`
      }
    }
  }
  return ''
}

const handleFileChange = async (file, files) => {
  const validFiles = []
  for (const item of files) {
    const raw = item.raw || item
    if (!raw || !raw.name) {
      continue
    }
    const lowerName = raw.name.toLowerCase()
    if (lowerName.endsWith('.json')) {
      try {
        const text = await readFileAsText(raw)
        let parsed
        try {
          parsed = JSON.parse(text)
        } catch (e) {
          showErrorNotification(`JSON 文件解析失败: ${raw.name}`)
          continue
        }
        const errorMessage = validateKnowledgeJsonStructure(parsed)
        if (errorMessage) {
          showErrorNotification(`JSON 文件结构不符合要求: ${raw.name}，${errorMessage}`)
          continue
        }
      } catch (e) {
        showErrorNotification(`读取文件失败: ${raw.name}`)
        continue
      }
    }
    validFiles.push(item)
  }
  if (validFiles.length === 0 && files.length > 0) {
    showErrorNotification('所有选择的 JSON 文件均未通过结构校验，请检查后重新上传')
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
      showErrorNotification('请至少选择一个文件')
      return
    }
    submitting.value = true
    try {
      const formData = buildFormData()
      const response = await uploadKnowledgeBase(formData)
      if (response.success) {
        showSuccessNotification(response.message || '知识库上传成功')
        resetForm()
        router.push('/my-knowledge')
      } else {
        showErrorNotification(response.message || '知识库上传失败')
      }
    } catch (error) {
      showApiErrorNotification(error, '知识库上传失败')
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
  router.push('/my-knowledge')
}
</script>

<style scoped>
.knowledge-upload-container {
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
