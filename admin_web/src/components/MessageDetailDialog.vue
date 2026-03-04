<template>
  <el-dialog
    v-model="visible"
    :title="message?.title"
    width="600px"
    @close="handleClose"
  >
    <div v-if="message" class="message-detail">
      <div class="detail-meta">
        <div class="meta-item">
          <span class="meta-label">发送者：</span>
          <span class="meta-value">{{ getMessageSender(message) }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">类型：</span>
          <el-tag :type="getMessageTypeTag(message.message_type)" size="small">
            {{ getMessageTypeLabel(message.message_type) }}
          </el-tag>
        </div>
        <div class="meta-item">
          <span class="meta-label">时间：</span>
          <span class="meta-value">{{ formatTime(message.create_datetime) }}</span>
        </div>
      </div>
      
      <el-divider />
      
      <!-- 富文本内容 -->
      <div class="detail-content" v-html="message.content"></div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { formatDate } from '/@/utils/formatTime';
import { request } from '/@/utils/service';

// Props
interface Props {
  modelValue: boolean;
  message: any;
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'read': [message: any];
}>();

// 本地状态
const visible = ref(props.modelValue);

// 监听外部变化
watch(() => props.modelValue, (newVal) => {
  visible.value = newVal;
  
  // 弹窗打开时，如果消息未读，标记为已读
  if (newVal && props.message && !props.message.is_read) {
    markAsRead(props.message);
  }
});

// 监听内部变化
watch(visible, (newVal) => {
  emit('update:modelValue', newVal);
});

// 消息类型映射
const MESSAGE_TYPE_MAP: Record<number, string> = {
  0: '系统通知',
  1: '评论',
  2: '回复',
  3: '点赞',
  4: '审核'
};

// 获取消息类型标签颜色
const getMessageTypeTag = (type: number) => {
  const tagMap: Record<number, string> = {
    0: '',
    1: 'success',
    2: 'primary',
    3: 'warning',
    4: 'info'
  };
  return tagMap[type] || '';
};

// 获取消息类型标签文本
const getMessageTypeLabel = (type: number) => {
  return MESSAGE_TYPE_MAP[type] || '未知';
};

// 获取消息发送者
const getMessageSender = (message: any) => {
  // 优先使用 extra_data 中的发送者信息
  if (message.extra_data?.sender_name) {
    return message.extra_data.sender_name;
  }
  // 如果是系统消息
  if (message.message_type === 0 || message.message_type === 4) {
    return '系统';
  }
  // 默认返回系统
  return '系统';
};

// 格式化时间
const formatTime = (datetime: string) => {
  if (!datetime) return '';
  return formatDate(new Date(datetime), 'YYYY-mm-dd HH:MM:SS');
};

// 标记为已读
const markAsRead = async (message: any) => {
  try {
    await request({
      url: `/api/system/message_center/${message.id}/`,
      method: 'get'
    });
    
    // 通知父组件消息已读
    emit('read', message);
  } catch (error) {
    console.error('标记已读失败:', error);
  }
};

// 关闭弹窗
const handleClose = () => {
  visible.value = false;
};
</script>

<style scoped lang="scss">
.message-detail {
  .detail-meta {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    background: var(--el-fill-color-light);
    border-radius: 4px;
    margin-bottom: 16px;
  }
  
  .meta-item {
    display: flex;
    align-items: center;
    font-size: 13px;
  }
  
  .meta-label {
    color: var(--el-text-color-secondary);
    min-width: 60px;
  }
  
  .meta-value {
    color: var(--el-text-color-primary);
  }
  
  .detail-content {
    font-size: 14px;
    line-height: 1.8;
    color: var(--el-text-color-regular);
    
    :deep(p) {
      margin: 8px 0;
    }
    
    :deep(img) {
      max-width: 100%;
      border-radius: 4px;
      margin: 8px 0;
    }
  }
}

:deep(.el-dialog__body) {
  padding: 20px;
}

:deep(.el-dialog__header) {
  padding: 16px 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  
  .el-dialog__title {
    font-size: 16px;
    font-weight: 500;
    color: var(--el-text-color-primary);
  }
}
</style>
