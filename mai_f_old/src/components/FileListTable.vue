<template>
  <el-table v-if="items && items.length" :data="items" size="small" border>
    <el-table-column
      prop="original_name"
      label="文件名"
      min-width="260"
    >
      <template #default="scope">
        <div class="file-name-cell">
          <span class="file-name-main">
            {{ scope.row.original_name || scope.row.file_name }}
          </span>
          <span
            v-if="scope.row.file_type"
            class="file-name-ext"
          >
            ({{ scope.row.file_type }})
          </span>
        </div>
      </template>
    </el-table-column>
    <el-table-column
      prop="file_size"
      label="大小"
      width="120"
      align="center"
      header-align="center"
    >
      <template #default="scope">
        {{ formatFileSize(scope.row.file_size) }}
      </template>
    </el-table-column>
    <el-table-column
      prop="update_datetime"
      label="修改时间"
      min-width="180"
      align="center"
      header-align="center"
    >
      <template #default="scope">
        {{ formatDate(scope.row.update_datetime || scope.row.create_datetime) }}
      </template>
    </el-table-column>
    <el-table-column
      label="操作"
      :width="actionColumnWidth"
      align="center"
      header-align="center"
    >
      <template #default="scope">
        <el-tooltip
          v-if="showPreview"
          content="浏览文件"
          placement="top"
        >
          <el-button
            type="primary"
            text
            circle
            size="small"
            @click="handlePreview(scope.row)"
          >
            <el-icon>
              <View />
            </el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip
          content="下载文件"
          placement="top"
        >
          <el-button
            type="primary"
            text
            circle
            size="small"
            @click="handleDownload(scope.row)"
          >
            <el-icon>
              <Download />
            </el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip
          v-if="showDelete"
          :content="deleteText"
          placement="top"
        >
          <el-button
            type="danger"
            text
            circle
            size="small"
            @click="handleDelete(scope.row)"
          >
            <el-icon>
              <component :is="deleteIconComponent" />
            </el-icon>
          </el-button>
        </el-tooltip>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { computed } from 'vue'
import { View, Download, Delete, Switch } from '@element-plus/icons-vue'
import { formatFileSize, formatDate } from '@/utils/api'

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  showPreview: {
    type: Boolean,
    default: true
  },
  showDelete: {
    type: Boolean,
    default: true
  },
  downloadText: {
    type: String,
    default: '下载'
  },
  deleteText: {
    type: String,
    default: '删除'
  }
})

const emit = defineEmits(['preview', 'download', 'delete'])

const actionColumnWidth = computed(() => 140)

const deleteIconComponent = computed(() => {
  if (props.deleteText === '替换配置') {
    return Switch
  }
  return Delete
})

const handlePreview = (row) => {
  emit('preview', row)
}

const handleDownload = (row) => {
  emit('download', row)
}

const handleDelete = (row) => {
  emit('delete', row)
}
</script>

<style scoped>
.file-name-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.file-name-main {
  word-break: break-all;
}

.file-name-ext {
  font-size: 12px;
  color: #909399;
}
</style>
