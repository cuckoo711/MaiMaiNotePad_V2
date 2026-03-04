<template>
  <div class="comment-section">
    <div v-if="showHeader" class="comment-header">
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
        placeholder="发表你的看法..."
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
        <span>评论将经过内容审核，请文明发言</span>
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
      />
      
      <!-- 加载更多按钮 -->
      <div v-if="hasMore && !loading" class="load-more-wrapper">
        <el-button 
          :loading="loadingMore" 
          @click="loadMoreComments"
          class="load-more-btn"
        >
          <i v-if="!loadingMore" class="fa fa-angle-down"></i>
          {{ loadingMore ? '加载中...' : '加载更多评论' }}
        </el-button>
      </div>
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
  },
  showHeader: {
    type: Boolean,
    default: true
  }
});

// ==================== 响应式数据 ====================
const userStore = useUserInfo();
const loading = ref(false);
const submitting = ref(false);
const comments = ref<any[]>([]);
const newCommentContent = ref('');

// 分页状态
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const hasMore = ref(false);
const loadingMore = ref(false);

// ==================== 计算属性 ====================
const isAuthenticated = computed(() => userStore.userInfos && userStore.userInfos.id);

const totalComments = computed(() => total.value);

// ==================== 方法 ====================
/**
 * 加载评论列表
 */
const loadComments = async (reset: boolean = true) => {
  if (!props.targetId || !props.targetType) return;
  
  if (reset) {
    loading.value = true;
    page.value = 1;
    comments.value = [];
  } else {
    loadingMore.value = true;
  }
  
  try {
    const { getComments } = await import('/@/api/comment');
    const response = await getComments(props.targetId, props.targetType, page.value, pageSize.value);
    
    if (response.code === 2000) {
      const newComments = response.data || [];
      
      if (reset) {
        comments.value = newComments;
      } else {
        comments.value = [...comments.value, ...newComments];
      }
      
      total.value = response.total || 0;
      hasMore.value = response.has_more || false;
    }
  } catch (error) {
    ElMessage.error('加载评论失败');
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
};

/**
 * 加载更多评论
 */
const loadMoreComments = async () => {
  if (loadingMore.value || !hasMore.value) return;
  
  page.value += 1;
  await loadComments(false);
};

/**
 * 提交评论（局部更新）
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
        // 成功：将新评论添加到列表顶部
        ElMessage.success('评论发表成功');
        newCommentContent.value = '';
        
        const newComment = response.data;
        // 初始化回复列表
        newComment.replies = [];
        newComment.reply_total = 0;
        
        // 添加到列表顶部
        comments.value.unshift(newComment);
        
        // 更新总数
        total.value += 1;
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
 * 处理回复（局部更新）
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
        return;
      }
      
      // 成功：局部更新，将新回复添加到对应的根评论下
      ElMessage.success('回复成功');
      
      const newReply = response.data;
      
      // 查找根评论并添加回复
      const addReplyToComment = (comment: any) => {
        if (comment.id === data.parentId) {
          // 找到根评论，添加回复
          if (!comment.replies) {
            comment.replies = [];
          }
          comment.replies.push(newReply);
          
          // 更新回复总数
          if (comment.reply_total !== undefined) {
            comment.reply_total += 1;
          }
          return true;
        }
        return false;
      };
      
      // 在评论列表中查找并添加回复
      for (const comment of comments.value) {
        if (addReplyToComment(comment)) {
          break;
        }
      }
      
      // 更新总评论数
      total.value += 1;
    } else {
      // 其他错误
      ElMessage.error(response.msg || '回复失败');
    }
  } catch (error: any) {
    // 网络错误或其他异常
    const errorMsg = error.response?.data?.msg || error.msg || '回复失败';
    ElMessage.error(errorMsg);
  }
};

/**
 * 处理删除（局部更新）
 */
const handleDelete = async (commentId: string) => {
  try {
    const { deleteComment } = await import('/@/api/comment');
    const response = await deleteComment(commentId);
    
    if (response.code === 2000) {
      ElMessage.success('删除成功');
      
      // 局部更新：从列表中移除评论
      const removeComment = (commentList: any[], parentComment?: any) => {
        const index = commentList.findIndex(c => c.id === commentId);
        if (index !== -1) {
          commentList.splice(index, 1);
          
          // 更新父评论的回复总数
          if (parentComment && parentComment.reply_total !== undefined) {
            parentComment.reply_total -= 1;
          }
          
          // 更新总评论数
          total.value -= 1;
          return true;
        }
        
        // 递归查找子评论
        for (const comment of commentList) {
          if (comment.replies && comment.replies.length > 0) {
            if (removeComment(comment.replies, comment)) {
              return true;
            }
          }
        }
        return false;
      };
      
      removeComment(comments.value);
    }
  } catch (error: any) {
    ElMessage.error(error.msg || '删除失败');
  }
};

/**
 * 处理点赞/点踩（局部更新）
 */
const handleReact = async (data: { commentId: string; action: string }) => {
  try {
    const { reactComment } = await import('/@/api/comment');
    const response = await reactComment(data.commentId, data.action);
    
    if (response.code === 2000) {
      // 局部更新：只更新对应评论的点赞数据
      const updateComment = (comment: any) => {
        if (comment.id === data.commentId) {
          comment.like_count = response.data.like_count;
          comment.dislike_count = response.data.dislike_count;
          comment.my_reaction = response.data.my_reaction;
          return true;
        }
        // 递归更新子评论
        if (comment.replies && comment.replies.length > 0) {
          for (const reply of comment.replies) {
            if (updateComment(reply)) {
              return true;
            }
          }
        }
        return false;
      };
      
      // 在评论列表中查找并更新
      for (const comment of comments.value) {
        if (updateComment(comment)) {
          break;
        }
      }
    }
  } catch (error: any) {
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

.load-more-wrapper {
  text-align: center;
  padding: 24px 0;
  
  .load-more-btn {
    padding: 10px 32px;
    border-radius: 8px;
    background: white;
    border: 2px solid #f0f0f0;
    color: #666;
    font-size: 14px;
    transition: all 0.3s;
    
    &:hover {
      border-color: #a0522d;
      color: #a0522d;
      background: rgba(160, 82, 45, 0.05);
    }
    
    i {
      margin-right: 6px;
      font-size: 16px;
    }
  }
}
</style>
