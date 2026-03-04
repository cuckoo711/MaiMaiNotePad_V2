<template>
  <div class="comment-section">
    <div class="comment-header">
      <h3>
        <i class="fa fa-comments"></i>
        评论 <span class="comment-count">({{ totalComments }})</span>
      </h3>
    </div>

    <!-- 发表评论 -->
    <div v-if="isAuthenticated" class="comment-input-area">
      <el-input
        v-model="newCommentContent"
        type="textarea"
        :rows="3"
        placeholder="发表你的看法...（评论将经过 AI 内容审核）"
        maxlength="500"
        show-word-limit
        class="comment-textarea"
      />
      <div class="comment-actions">
        <el-button type="primary" :loading="submitting" @click="submitComment">
          <i v-if="!submitting" class="fa fa-paper-plane"></i>
          {{ submitting ? '审核中...' : '发表评论' }}
        </el-button>
      </div>
      <div class="comment-tips">
        <i class="fa fa-info-circle"></i>
        <span>评论将经过 AI 内容审核，请文明发言</span>
      </div>
    </div>
    <div v-else class="login-prompt">
      <i class="fa fa-info-circle"></i>
      请先登录后再发表评论
    </div>

    <!-- 评论列表 -->
    <div v-loading="loading" class="comment-list">
      <div v-if="comments.length === 0 && !loading" class="empty-comments">
        <i class="fa fa-comment-o"></i>
        <p>暂无评论，快来发表第一条评论吧！</p>
      </div>

      <CommentItem
        v-for="comment in comments"
        :key="comment.id"
        :comment="comment"
        :target-id="targetId"
        :target-type="targetType"
        @reply="handleReply"
        @delete="handleDelete"
        @react="handleReact"
        @refresh="loadComments"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { useUserInfo } from '/@/stores/userInfo';
import CommentItem from './CommentItem.vue';

// ==================== Props ====================
const props = defineProps({
  targetId: {
    type: String,
    required: true
  },
  targetType: {
    type: String,
    required: true,
    validator: (value: string) => ['knowledge', 'persona'].includes(value)
  }
});

// ==================== 响应式数据 ====================
const userStore = useUserInfo();
const loading = ref(false);
const submitting = ref(false);
const comments = ref<any[]>([]);
const newCommentContent = ref('');

// ==================== 计算属性 ====================
const isAuthenticated = computed(() => userStore.userInfos && userStore.userInfos.id);

const totalComments = computed(() => {
  const countReplies = (comment: any): number => {
    let count = 1;
    if (comment.replies && comment.replies.length > 0) {
      comment.replies.forEach((reply: any) => {
        count += countReplies(reply);
      });
    }
    return count;
  };
  
  return comments.value.reduce((total, comment) => total + countReplies(comment), 0);
});

// ==================== 方法 ====================
/**
 * 加载评论列表
 */
const loadComments = async () => {
  if (!props.targetId || !props.targetType) return;
  
  loading.value = true;
  try {
    const { getComments } = await import('/@/api/comment');
    const response = await getComments(props.targetId, props.targetType);
    
    if (response.code === 2000) {
      comments.value = response.data || [];
    }
  } catch (error) {
    console.error('加载评论失败:', error);
    ElMessage.error('加载评论失败');
  } finally {
    loading.value = false;
  }
};

/**
 * 提交评论
 */
const submitComment = async () => {
  if (!newCommentContent.value.trim()) {
    ElMessage.warning('请输入评论内容');
    return;
  }
  
  submitting.value = true;
  try {
    const { createComment } = await import('/@/api/comment');
    const response = await createComment({
      target_id: props.targetId,
      target_type: props.targetType,
      content: newCommentContent.value.trim()
    });
    
    if (response.code === 2000) {
      // 检查是否审核失败
      if (response.data?.success === false && response.data?.moderation_failed) {
        // 审核失败
        ElMessage({
          message: response.data.error_message,
          type: 'warning',
          duration: 5000,
          showClose: true
        });
      } else {
        // 成功
        ElMessage.success('评论发表成功');
        newCommentContent.value = '';
        await loadComments();
      }
    } else {
      // 其他错误
      ElMessage.error(response.msg || '发表评论失败');
    }
  } catch (error: any) {
    // 网络错误或其他异常
    const errorMsg = error.response?.data?.msg || error.msg || '发表评论失败';
    ElMessage.error(errorMsg);
  } finally {
    submitting.value = false;
  }
};

/**
 * 处理回复
 */
const handleReply = async (data: { parentId: string; replyToId?: string; content: string }) => {
  try {
    const { createComment } = await import('/@/api/comment');
    const response = await createComment({
      target_id: props.targetId,
      target_type: props.targetType,
      content: data.content,
      parent: data.parentId,
      reply_to: data.replyToId
    });
    
    if (response.code === 2000) {
      // 检查是否审核失败
      if (response.data?.success === false && response.data?.moderation_failed) {
        // 审核失败
        ElMessage({
          message: response.data.error_message,
          type: 'warning',
          duration: 5000,
          showClose: true
        });
        // 刷新评论列表以重置子组件状态
        await loadComments();
      } else {
        // 成功
        ElMessage.success('回复成功');
        await loadComments();
      }
    } else {
      // 其他错误
      ElMessage.error(response.msg || '回复失败');
      // 刷新评论列表以重置子组件状态
      await loadComments();
    }
  } catch (error: any) {
    // 网络错误或其他异常
    const errorMsg = error.response?.data?.msg || error.msg || '回复失败';
    ElMessage.error(errorMsg);
    // 刷新评论列表以重置子组件状态
    await loadComments();
  }
};

/**
 * 处理删除
 */
const handleDelete = async (commentId: string) => {
  try {
    const { deleteComment } = await import('/@/api/comment');
    const response = await deleteComment(commentId);
    
    if (response.code === 2000) {
      ElMessage.success('删除成功');
      await loadComments();
    }
  } catch (error: any) {
    console.error('删除失败:', error);
    ElMessage.error(error.msg || '删除失败');
  }
};

/**
 * 处理点赞/点踩
 */
const handleReact = async (data: { commentId: string; action: string }) => {
  try {
    const { reactComment } = await import('/@/api/comment');
    const response = await reactComment(data.commentId, data.action);
    
    if (response.code === 2000) {
      await loadComments();
    }
  } catch (error: any) {
    console.error('操作失败:', error);
    ElMessage.error(error.msg || '操作失败');
  }
};

// ==================== 生命周期 ====================
onMounted(() => {
  loadComments();
});

watch(() => [props.targetId, props.targetType], () => {
  loadComments();
});
</script>

<script lang="ts">
export default {
  name: 'CommentSection'
};
</script>

<style scoped lang="scss">
.comment-section {
  margin-top: 40px;
  padding: 32px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.comment-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
  
  h3 {
    font-size: 20px;
    font-weight: 600;
    color: #333;
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0;
    
    i {
      color: #a0522d;
      font-size: 22px;
    }
    
    .comment-count {
      font-size: 16px;
      color: #999;
      font-weight: 400;
    }
  }
}

.comment-input-area {
  margin-bottom: 32px;
  
  .comment-textarea {
    :deep(.el-textarea__inner) {
      border-radius: 12px;
      border: 2px solid #f0f0f0;
      padding: 16px;
      font-size: 14px;
      line-height: 1.6;
      transition: all 0.3s;
      
      &:focus {
        border-color: #a0522d;
        box-shadow: 0 0 0 3px rgba(160, 82, 45, 0.1);
      }
    }
  }
  
  .comment-actions {
    margin-top: 12px;
    display: flex;
    justify-content: flex-end;
    
    .el-button {
      padding: 10px 24px;
      border-radius: 8px;
      background: linear-gradient(135deg, #a0522d 0%, #d4a574 100%);
      border: none;
      
      &:hover {
        background: linear-gradient(135deg, #8b4513 0%, #a0522d 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(160, 82, 45, 0.3);
      }
      
      i {
        margin-right: 6px;
      }
    }
  }
  
  .comment-tips {
    margin-top: 8px;
    padding: 8px 12px;
    background: #f8f9fa;
    border-radius: 6px;
    font-size: 12px;
    color: #666;
    display: flex;
    align-items: center;
    gap: 6px;
    
    i {
      color: #a0522d;
      font-size: 13px;
    }
  }
}

.login-prompt {
  padding: 24px;
  background: linear-gradient(135deg, #fff5f0 0%, #ffe8d9 100%);
  border-radius: 12px;
  text-align: center;
  color: #8b6239;
  font-size: 14px;
  margin-bottom: 32px;
  
  i {
    font-size: 18px;
    margin-right: 8px;
  }
}

.comment-list {
  min-height: 200px;
}

.empty-comments {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  
  i {
    font-size: 48px;
    margin-bottom: 16px;
    display: block;
    opacity: 0.3;
    color: #a0522d;
  }
  
  p {
    margin: 0;
    font-size: 15px;
  }
}
</style>
