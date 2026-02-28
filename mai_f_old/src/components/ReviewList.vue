<template>
  <div v-loading="loading">
    <div
      v-for="item in items"
      :key="item.id"
      class="review-item"
    >
      <div class="review-main">
        <div class="review-title-row">
          <span class="review-name">{{ item.name }}</span>
          <span class="review-status pending">
            待审核
          </span>
        </div>
        <p v-if="item.description" class="review-description">
          {{ item.description }}
        </p>
        <div class="review-meta">
          <span class="review-author">
            上传者：{{ resolveAuthor(item) }}
          </span>
          <span class="review-time">
            上传时间：{{ formatDate(item.create_datetime) }}
          </span>
        </div>
      </div>
      <div class="review-actions">
        <div class="review-stats">
          <span class="review-stat">
            <el-icon>
              <Download />
            </el-icon>
            {{ item.downloads || 0 }}
          </span>
          <span class="review-stat">
            <el-icon>
              <Star />
            </el-icon>
            {{ item.star_count || 0 }}
          </span>
        </div>
        <div
          v-if="canReview"
          class="review-action-buttons"
        >
          <el-button
            size="small"
            plain
            @click="handleView(item)"
          >
            查看详情
          </el-button>
          <el-button
            size="small"
            type="primary"
            plain
            @click="handleApprove(item)"
          >
            通过
          </el-button>
          <el-button
            size="small"
            type="danger"
            plain
            @click="handleReject(item)"
          >
            拒绝
          </el-button>
        </div>
      </div>
    </div>

    <div
      v-if="!loading && (!items || !items.length)"
      class="empty-tip"
    >
      {{ emptyText }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Download, Star } from '@element-plus/icons-vue'
import { formatDate as formatDateUtil } from '@/utils/api'

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  canReview: {
    type: Boolean,
    default: false
  },
  emptyText: {
    type: String,
    default: '暂无待审核内容。'
  }
})

const emit = defineEmits(['approve', 'reject', 'view'])

const formatDate = (value) => {
  return formatDateUtil(value) || ''
}

const resolveAuthor = (item) => {
  return item.uploader_name || item.author || item.author_id || item.uploader_id || '未知'
}

const canReview = computed(() => props.canReview)

const handleView = (item) => {
  emit('view', item)
}

const handleApprove = (item) => {
  emit('approve', item)
}

const handleReject = (item) => {
  emit('reject', item)
}
</script>

<style scoped>
.review-item {
  display: flex;
  justify-content: space-between;
  padding: 14px 16px;
  margin-bottom: 12px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background-color: var(--card-background);
  position: relative;
  transition: background-color 0.15s ease, border-color 0.15s ease, transform 0.1s ease;
}

.review-item:hover {
  background-color: var(--hover-color);
  border-color: var(--secondary-color);
  transform: translateY(-1px);
}

.review-main {
  flex: 1;
  min-width: 0;
}

.review-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.review-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--secondary-color);
  word-break: break-all;
}

.review-status {
  font-size: 12px;
  padding: 0 6px;
  border-radius: 999px;
}

.review-status.pending {
  background-color: rgba(246, 196, 83, 0.12);
  color: var(--secondary-color);
}

.review-description {
  margin: 0 0 6px;
  color: var(--muted-text-color);
  font-size: 13px;
}

.review-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--muted-text-color);
}

.review-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  margin-left: 24px;
  font-size: 12px;
}

.review-stats {
  display: flex;
  gap: 12px;
}

.review-stat {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--muted-text-color);
}

.review-action-buttons {
  display: flex;
  gap: 8px;
}

.empty-tip {
  padding: 24px 0;
  text-align: center;
  color: #909399;
  font-size: 14px;
}
</style>
