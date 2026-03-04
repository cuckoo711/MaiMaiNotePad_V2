<template>
  <div class="comment-item" :class="{ 'is-reply': isReply }">
    <div class="comment-avatar">
      <el-avatar :size="isReply ? 36 : 44" :src="comment.user_avatar">
        {{ comment.user_name?.[0] || '?' }}
      </el-avatar>
    </div>
    
    <div class="comment-content-wrapper">
      <div class="comment-header">
        <span class="comment-author">{{ comment.user_name || '匿名用户' }}</span>
        <span class="comment-time">{{ formatTime(comment.create_datetime) }}</span>
      </div>
      
      <div class="comment-content">
        <span v-if="comment.reply_to_name" class="reply-to">
          回复 @{{ comment.reply_to_name }}:
        </span>
        {{ comment.content }}
      </div>
      
      <div class="comment-actions">
        <button class="action-btn" :class="{ active: comment.my_reaction === 'like' }" @click="handleReact('like')">
          <i class="fa" :class="comment.my_reaction === 'like' ? 'fa-thumbs-up' : 'fa-thumbs-o-up'"></i>
          <span v-if="comment.like_count > 0">{{ comment.like_count }}</span>
        </button>
        
        <button class="action-btn" :class="{ active: comment.my_reaction === 'dislike' }" @click="handleReact('dislike')">
          <i class="fa" :class="comment.my_reaction === 'dislike' ? 'fa-thumbs-down' : 'fa-thumbs-o-down'"></i>
          <span v-if="comment.dislike_count > 0">{{ comment.dislike_count }}</span>
        </button>
        
        <button v-if="isAuthenticated" class="action-btn" @click="toggleReplyInput">
          <i class="fa fa-reply"></i>
          回复
        </button>
        
        <button v-if="canDelete" class="action-btn delete-btn" @click="confirmDelete">
          <i class="fa fa-trash-o"></i>
          删除
        </button>
      </div>
      
      <!-- 回复输入框 -->
      <div v-if="showReplyInput" class="reply-input-area">
        <el-input
          v-model="replyContent"
          type="textarea"
          :rows="2"
          :placeholder="`回复 @${comment.user_name}...`"
          maxlength="500"
          show-word-limit
        />
        <div class="reply-actions">
          <el-button size="small" @click="cancelReply">取消</el-button>
          <el-button type="primary" size="small" :loading="replying" @click="submitReply">
            {{ replying ? '审核中...' : '发送' }}
          </el-button>
        </div>
      </div>
      
      <!-- 子评论列表 -->
      <div v-if="comment.replies && comment.replies.length > 0" class="replies-list">
        <CommentItem
          v-for="reply in comment.replies"
          :key="reply.id"
          :comment="reply"
          :target-id="targetId"
          :target-type="targetType"
          :is-reply="true"
          @reply="$emit('reply', $event)"
          @delete="$emit('delete', $event)"
          @react="$emit('react', $event)"
        />
        
        <!-- 展开更多回复按钮 -->
        <div v-if="hasMoreReplies && !isReply" class="load-more-replies">
          <el-button 
            text 
            :loading="loadingMoreReplies" 
            @click="loadMoreReplies"
            class="load-more-replies-btn"
          >
            <i v-if="!loadingMoreReplies" class="fa fa-angle-down"></i>
            {{ loadingMoreReplies ? '加载中...' : `展开更多回复 (还有 ${replyTotal - comment.replies.length} 条)` }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { ElMessageBox } from 'element-plus';
import { useUserInfo } from '/@/stores/userInfo';

// ==================== Props & Emits ====================
const props = defineProps({
  comment: {
    type: Object,
    required: true
  },
  targetId: {
    type: String,
    required: true
  },
  targetType: {
    type: String,
    required: true
  },
  isReply: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['reply', 'delete', 'react', 'refresh']);

// ==================== 响应式数据 ====================
const userStore = useUserInfo();
const showReplyInput = ref(false);
const replyContent = ref('');
const replying = ref(false);

// 回复分页状态
const replyPage = ref(1);
const replyPageSize = ref(10);
const replyTotal = ref(0);
const hasMoreReplies = ref(false);
const loadingMoreReplies = ref(false);

// 监听评论变化，更新回复分页状态
watch(() => props.comment, () => {
  // 更新回复分页状态
  if (props.comment.reply_total !== undefined) {
    replyTotal.value = props.comment.reply_total;
    const currentRepliesCount = props.comment.replies?.length || 0;
    hasMoreReplies.value = currentRepliesCount < props.comment.reply_total;
  }
}, { deep: true, immediate: true });

// ==================== 计算属性 ====================
const isAuthenticated = computed(() => userStore.userInfos && userStore.userInfos.id);

const canDelete = computed(() => {
  if (!isAuthenticated.value) return false;
  const currentUserId = userStore.userInfos?.id;
  return currentUserId === props.comment.user;
});

// ==================== 方法 ====================
/**
 * 格式化时间
 */
const formatTime = (datetime: string): string => {
  if (!datetime) return '';
  
  const date = new Date(datetime);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  
  if (diff < minute) {
    return '刚刚';
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)} 分钟前`;
  } else if (diff < day) {
    return `${Math.floor(diff / hour)} 小时前`;
  } else if (diff < 7 * day) {
    return `${Math.floor(diff / day)} 天前`;
  } else {
    return date.toLocaleDateString('zh-CN');
  }
};

/**
 * 切换回复输入框
 */
const toggleReplyInput = () => {
  showReplyInput.value = !showReplyInput.value;
  if (!showReplyInput.value) {
    replyContent.value = '';
  }
};

/**
 * 取消回复
 */
const cancelReply = () => {
  showReplyInput.value = false;
  replyContent.value = '';
};

/**
 * 提交回复
 */
const submitReply = async () => {
  if (!replyContent.value.trim()) {
    return;
  }
  
  replying.value = true;
  
  // 找到根评论 ID（parent 为 null 的评论）
  const parentId = props.comment.parent || props.comment.id;
  
  // 发送回复事件
  emit('reply', {
    parentId: parentId,
    replyToId: props.comment.id,
    content: replyContent.value.trim()
  });
  
  // 等待一小段时间让父组件处理完成，然后重置状态
  await new Promise(resolve => setTimeout(resolve, 100));
  
  // 重置回复状态
  replying.value = false;
  showReplyInput.value = false;
  replyContent.value = '';
};

/**
 * 处理点赞/点踩
 */
const handleReact = (action: string) => {
  if (!isAuthenticated.value) {
    ElMessageBox.alert('请先登录后再操作', '提示', {
      confirmButtonText: '确定'
    });
    return;
  }
  
  // 如果已经是当前操作，则取消
  const finalAction = props.comment.my_reaction === action ? 'clear' : action;
  
  emit('react', {
    commentId: props.comment.id,
    action: finalAction
  });
};

/**
 * 加载更多回复
 */
const loadMoreReplies = async () => {
  if (loadingMoreReplies.value || !hasMoreReplies.value) return;
  
  loadingMoreReplies.value = true;
  replyPage.value += 1;
  
  try {
    const { getReplies } = await import('/@/api/comment');
    const response = await getReplies(props.comment.id, replyPage.value, replyPageSize.value);
    
    if (response.code === 2000) {
      const newReplies = response.data || [];
      
      // 将新回复添加到现有回复列表
      if (props.comment.replies) {
        props.comment.replies.push(...newReplies);
      } else {
        props.comment.replies = newReplies;
      }
      
      // 更新分页状态
      hasMoreReplies.value = response.has_more || false;
    }
  } catch (error: any) {
    ElMessage.error(error.msg || '加载回复失败');
  } finally {
    loadingMoreReplies.value = false;
  }
};

/**
 * 确认删除
 */
const confirmDelete = () => {
  ElMessageBox.confirm(
    '删除后将无法恢复，确定要删除这条评论吗？',
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    emit('delete', props.comment.id);
  }).catch(() => {
    // 用户取消
  });
};
</script>

<script lang="ts">
export default {
  name: 'CommentItem'
};
</script>

<style scoped lang="scss">
.comment-item {
  display: flex;
  gap: 16px;
  padding: 20px 0;
  border-bottom: 1px solid #f5f5f5;
  
  &.is-reply {
    padding: 16px 0;
    
    .comment-avatar {
      flex-shrink: 0;
    }
  }
  
  &:last-child {
    border-bottom: none;
  }
}

.comment-avatar {
  flex-shrink: 0;
  
  :deep(.el-avatar) {
    background: linear-gradient(135deg, #d4a574 0%, #a0522d 100%);
    color: white;
    font-weight: 600;
  }
}

.comment-content-wrapper {
  flex: 1;
  min-width: 0;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  
  .comment-author {
    font-weight: 600;
    color: #333;
    font-size: 14px;
  }
  
  .comment-time {
    font-size: 12px;
    color: #999;
  }
}

.comment-content {
  color: #555;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
  word-break: break-word;
  
  .reply-to {
    color: #a0522d;
    font-weight: 500;
    margin-right: 4px;
  }
}

.comment-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  
  .action-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: none;
    border: none;
    color: #999;
    font-size: 13px;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s;
    
    &:hover {
      color: #a0522d;
      background: rgba(160, 82, 45, 0.05);
    }
    
    &.active {
      color: #a0522d;
      font-weight: 600;
    }
    
    &.delete-btn:hover {
      color: #f56c6c;
      background: rgba(245, 108, 108, 0.05);
    }
    
    i {
      font-size: 14px;
    }
  }
}

.reply-input-area {
  margin-top: 16px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  
  :deep(.el-textarea__inner) {
    border-radius: 6px;
    border: 1px solid #e0e0e0;
    
    &:focus {
      border-color: #a0522d;
    }
  }
  
  .reply-actions {
    margin-top: 12px;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    
    .el-button {
      padding: 6px 16px;
    }
  }
}

.replies-list {
  margin-top: 16px;
  padding-left: 20px;
  border-left: 2px solid #f0f0f0;
}

.load-more-replies {
  margin-top: 12px;
  text-align: center;
  
  .load-more-replies-btn {
    color: #a0522d;
    font-size: 13px;
    padding: 6px 16px;
    
    &:hover {
      background: rgba(160, 82, 45, 0.05);
    }
    
    i {
      margin-right: 4px;
      font-size: 14px;
    }
  }
}
</style>
