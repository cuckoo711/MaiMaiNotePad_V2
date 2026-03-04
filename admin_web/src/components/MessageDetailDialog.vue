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
      
      <!-- 快捷回复 - 仅评论和回复类型显示 -->
      <div v-if="message.message_type === 1 || message.message_type === 2" class="quick-reply">
        <el-divider />
        <div class="reply-title">快捷回复</div>
        <el-input
          v-model="replyContent"
          type="textarea"
          :rows="3"
          placeholder="输入回复内容..."
          maxlength="500"
          show-word-limit
          :disabled="replying"
        />
        <div class="reply-actions">
          <el-button 
            type="primary" 
            @click="handleReply"
            :loading="replying"
            :disabled="!replyContent.trim()"
          >
            发送回复
          </el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { formatDate } from '/@/utils/formatTime';
import { request } from '/@/utils/service';
import { ElMessage } from 'element-plus';

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
const replyContent = ref('');
const replying = ref(false);

// 监听外部变化
watch(() => props.modelValue, (newVal) => {
  visible.value = newVal;
  
  // 弹窗打开时，如果消息未读，标记为已读
  if (newVal && props.message && !props.message.is_read) {
    markAsRead(props.message);
  }
  
  // 弹窗打开时，清空回复内容
  if (newVal) {
    replyContent.value = '';
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

// 发送回复
const handleReply = async () => {
  if (!replyContent.value.trim()) {
    ElMessage.warning('请输入回复内容');
    return;
  }
  
  const extraData = props.message?.extra_data;
  if (!extraData?.target_id || !extraData?.target_type) {
    ElMessage.error('无法获取评论信息');
    return;
  }
  
  // 确定 parent 和 reply_to：
  // - parent: 用于维护两层树形结构，始终指向根评论
  // - reply_to: 用于记录真正回复的是哪条评论（显示"回复 @xxx"）
  let parentId = null;
  let replyToId = null;
  
  if (props.message?.message_type === 2 && extraData.reply_id) {
    // 回复通知：有人回复了你的评论
    // parent: 使用 root_comment_id（如果有）或 comment_id（你的评论）
    // reply_to: 使用 reply_id（回复你的那条评论）
    parentId = extraData.root_comment_id || extraData.comment_id;
    replyToId = extraData.reply_id;
  } else if (props.message?.message_type === 1 && extraData.comment_id) {
    // 评论通知：有人评论了你的内容
    // parent: 使用 comment_id（那条一级评论）
    // reply_to: 也使用 comment_id（回复那条评论）
    parentId = extraData.comment_id;
    replyToId = extraData.comment_id;
  }
  
  if (!parentId) {
    ElMessage.error('无法确定回复目标');
    return;
  }
  
  replying.value = true;
  try {
    const response = await request({
      url: '/api/content/comments/',
      method: 'post',
      data: {
        target_id: extraData.target_id,
        target_type: extraData.target_type,
        content: replyContent.value.trim(),
        parent: parentId,
        reply_to: replyToId
      }
    });
    
    if (response && response.code === 2000) {
      // 检查是否审核失败
      if (response.data?.moderation_failed || response.data?.success === false) {
        // 审核失败，显示具体的错误消息
        const errorMsg = response.data?.error_message || '评论未通过审核';
        
        // 使用 nextTick 确保在下一个事件循环中显示消息，避免与对话框状态冲突
        await new Promise(resolve => setTimeout(resolve, 0));
        ElMessage.error(errorMsg);
        return; // 不关闭弹窗，让用户可以修改内容重新提交
      }
      
      // 真正的成功
      ElMessage.success('回复成功');
      replyContent.value = '';
      // 关闭弹窗
      visible.value = false;
    } else {
      // 处理非成功响应
      const errorMsg = response?.msg || response?.message || '回复失败';
      ElMessage.error(errorMsg);
    }
  } catch (error: any) {
    // 处理异常情况
    
    // 优先使用后端返回的错误消息
    let errorMsg = '回复失败';
    
    if (error?.msg) {
      // 后端返回的标准错误格式
      errorMsg = error.msg;
    } else if (error?.response?.data?.msg) {
      // axios 错误响应中的消息
      errorMsg = error.response.data.msg;
    } else if (error?.response?.data?.message) {
      // 另一种可能的错误格式
      errorMsg = error.response.data.message;
    } else if (error?.message) {
      // JavaScript 错误对象
      errorMsg = error.message;
    }
    
    ElMessage.error(errorMsg);
  } finally {
    replying.value = false;
  }
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
  
  .quick-reply {
    margin-top: 16px;
    
    .reply-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--el-text-color-primary);
      margin-bottom: 12px;
    }
    
    .reply-actions {
      margin-top: 12px;
      display: flex;
      justify-content: flex-end;
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
