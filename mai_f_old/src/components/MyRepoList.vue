<template>
  <div>
    <div
      v-for="item in items"
      :key="item.id"
      class="repo-item"
      @click="handleItemClick(item)"
    >
      <div class="repo-main">
        <div class="repo-title-row">
          <span class="repo-name">{{ item.name }}</span>
          <el-tag
            v-if="showVersionTag && item.version"
            size="small"
            type="info"
            effect="dark"
            class="repo-version-tag"
          >
            v{{ item.version }}
          </el-tag>
          <span
            v-if="item.is_public && !item.is_pending"
            class="repo-visibility"
          >
            公开
          </span>
          <span
            v-else-if="!item.is_public && item.is_pending"
            class="repo-status pending"
          >
            公开审核中
          </span>
          <span
            v-else
            class="repo-visibility"
          >
            私有
          </span>
        </div>
        <p v-if="item.description" class="repo-description">
          {{ item.description }}
        </p>
        <div class="repo-meta">
          <span v-if="item.tags && item.tags.length" class="repo-tags">
            <el-tag
              v-for="(tag, index) in item.tags"
              :key="index"
              size="small"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
          </span>
          <span class="repo-updated">
            最近更新于 {{ formatDate(item.update_datetime || item.create_datetime) }}
          </span>
        </div>
      </div>
      <div class="repo-actions">
        <div class="repo-stats">
          <span class="repo-stat">
            <el-icon>
              <Download />
            </el-icon>
            {{ item.downloads || 0 }}
          </span>
          <span class="repo-stat">
            <el-icon>
              <Star />
            </el-icon>
            {{ item.star_count || 0 }}
          </span>
        </div>
        <div class="repo-action-buttons">
          <el-tooltip
            v-if="!item.is_public && !item.is_pending"
            content="编辑内容和文件"
            placement="top"
          >
            <el-button
              circle
              text
              @click.stop="handleEditClick(item)"
            >
              <el-icon>
                <Edit />
              </el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip
            v-if="!item.is_public && !item.is_pending"
            :content="publishTooltip"
            placement="top"
          >
            <el-button
              circle
              text
              @click.stop="handlePublishClick(item)"
            >
              <el-icon>
                <UploadFilled />
              </el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="删除" placement="top">
            <el-button
              circle
              text
              type="danger"
              @click.stop="handleDeleteClick(item)"
            >
              <el-icon>
                <Delete />
              </el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Download, Star, Delete, UploadFilled, Edit } from '@element-plus/icons-vue'
import { formatDate } from '@/utils/api'

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  publishTooltip: {
    type: String,
    default: ''
  },
  showVersionTag: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['item-click', 'edit-click', 'publish-click', 'delete-click'])

const { showVersionTag } = props

const handleItemClick = (item) => {
  emit('item-click', item)
}

const handleEditClick = (item) => {
  emit('edit-click', item)
}

const handlePublishClick = (item) => {
  emit('publish-click', item)
}

const handleDeleteClick = (item) => {
  emit('delete-click', item)
}
</script>

<style scoped>
.repo-item {
  display: flex;
  justify-content: space-between;
  padding: 14px 16px;
  margin-bottom: 12px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background-color: var(--card-background);
  position: relative;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, transform 0.1s ease;
}

.repo-item:hover {
  background-color: var(--hover-color);
  border-color: var(--secondary-color);
  transform: translateY(-1px);
}

.repo-main {
  flex: 1;
  min-width: 0;
}

.repo-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.repo-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--secondary-color);
  word-break: break-all;
}

.repo-version-tag {
  padding: 0 6px;
  background-color: var(--secondary-color);
  color: #303133;
  border-color: transparent;
}

.repo-visibility {
  font-size: 12px;
  padding: 0 6px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  color: var(--muted-text-color);
}

.repo-status {
  font-size: 12px;
  padding: 0 6px;
  border-radius: 999px;
}

.repo-status.pending {
  background-color: rgba(246, 196, 83, 0.12);
  color: var(--secondary-color);
}

.repo-status.rejected {
  background-color: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}

.repo-description {
  margin: 0 0 6px;
  color: var(--muted-text-color);
  font-size: 13px;
}

.repo-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  font-size: 12px;
  color: var(--muted-text-color);
}

.repo-tags :deep(.el-tag) {
  margin-right: 4px;
}

.repo-updated {
  white-space: nowrap;
}

.repo-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  margin-left: 24px;
  font-size: 12px;
}

.repo-stats {
  display: flex;
  gap: 12px;
}

.repo-stat {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--muted-text-color);
}

.repo-action-buttons {
  position: absolute;
  right: 16px;
  bottom: 10px;
  display: flex;
  gap: 4px;
}
</style>
