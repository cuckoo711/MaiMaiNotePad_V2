<template>
  <fs-page>
    <div class="user-messages-container">
      <!-- 顶部区域：标签页 + 全部已读按钮 -->
      <div class="message-header">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="message-tabs">
          <el-tab-pane label="全部" name="all"></el-tab-pane>
          <el-tab-pane label="通知" name="notice"></el-tab-pane>
          <el-tab-pane label="评论" name="comment"></el-tab-pane>
          <el-tab-pane label="回复" name="reply"></el-tab-pane>
        </el-tabs>
        
        <el-button 
          type="primary" 
          size="default" 
          @click="handleMarkAllRead"
          :loading="markingAllRead"
          class="mark-all-btn"
        >
          全部已读
        </el-button>
      </div>

      <!-- 消息列表 -->
      <div class="message-list" v-loading="loading" ref="messageListRef">
        <el-empty v-if="!loading && messages.length === 0" description="暂无消息" />
        
        <div
          v-for="message in messages"
          :key="message.id"
          class="message-card"
          @click="handleMessageClick(message)"
        >
          <!-- 未读红点 -->
          <div v-if="!message.is_read" class="unread-dot"></div>
          
          <!-- 消息内容 -->
          <div class="message-content">
            <div class="message-title">
              <span class="message-sender">{{ getMessageSender(message) }}</span>
              <span class="message-separator">-</span>
              <span class="message-subject">{{ message.title }}</span>
            </div>
            <div class="message-meta">
              <el-tag :type="getMessageTypeTag(message.message_type)" size="small">
                {{ getMessageTypeLabel(message.message_type) }}
              </el-tag>
              <span class="message-time">{{ formatTime(message.create_datetime) }}</span>
            </div>
          </div>
          
          <!-- 箭头图标 -->
          <el-icon class="message-arrow">
            <ele-ArrowRight />
          </el-icon>
        </div>

        <!-- 加载更多提示 -->
        <div v-if="hasMore && !loading" class="load-more-trigger" ref="loadMoreTrigger">
          <span class="load-more-text">加载更多...</span>
        </div>
        
        <div v-if="!hasMore && messages.length > 0" class="no-more-text">
          没有更多消息了
        </div>
      </div>

      <!-- 消息详情弹窗 -->
      <MessageDetailDialog
        v-model="dialogVisible"
        :message="currentMessage"
        @read="handleMessageRead"
      />
    </div>
  </fs-page>
</template>

<script setup lang="ts" name="userMessages">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import { formatDate } from '/@/utils/formatTime';
import { request } from '/@/utils/service';
import MessageDetailDialog from '/@/components/MessageDetailDialog.vue';

// 状态
const activeTab = ref('all');
const loading = ref(false);
const messages = ref<any[]>([]);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);
const dialogVisible = ref(false);
const currentMessage = ref<any>(null);
const markingAllRead = ref(false);
const hasMore = ref(true);
const messageListRef = ref<HTMLElement | null>(null);
const loadMoreTrigger = ref<HTMLElement | null>(null);
const observer = ref<IntersectionObserver | null>(null);

// 消息类型映射
const MESSAGE_TYPE_MAP = {
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

// 获取消息类型过滤参数
const getMessageTypeFilter = () => {
  switch (activeTab.value) {
    case 'notice':
      return '0,4'; // 系统通知和审核
    case 'comment':
      return '1'; // 评论
    case 'reply':
      return '2,3'; // 回复和点赞
    default:
      return ''; // 全部
  }
};

// 加载消息列表
const loadMessages = async (append = false) => {
  if (loading.value) return;
  
  loading.value = true;
  try {
    const params: any = {
      page: currentPage.value,
      limit: pageSize.value
    };
    
    const messageType = getMessageTypeFilter();
    if (messageType) {
      params.message_type = messageType;
    }
    
    const response = await request({
      url: '/api/system/message_center/get_self_receive/',
      method: 'get',
      params
    });
    
    if (response && response.code === 2000) {
      const newMessages = Array.isArray(response.data) ? response.data : [];
      
      if (append) {
        messages.value = [...messages.value, ...newMessages];
      } else {
        messages.value = newMessages;
      }
      
      total.value = response.total || 0;
      
      // 判断是否还有更多数据
      hasMore.value = messages.value.length < total.value;
      
      // 如果是追加模式且还有更多数据，设置观察器
      if (append && hasMore.value) {
        await nextTick();
        setupObserver();
      }
    } else {
      ElMessage.error(response?.msg || '加载消息失败');
    }
  } catch (error: any) {
    ElMessage.error(error?.msg || error?.message || '加载消息失败');
  } finally {
    loading.value = false;
  }
};

// 加载更多
const loadMore = async () => {
  if (!hasMore.value || loading.value) return;
  
  currentPage.value += 1;
  await loadMessages(true);
};

// 设置 IntersectionObserver
const setupObserver = () => {
  // 清除旧的观察器
  if (observer.value) {
    observer.value.disconnect();
  }
  
  if (!loadMoreTrigger.value) return;
  
  observer.value = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && hasMore.value && !loading.value) {
          loadMore();
        }
      });
    },
    {
      root: null,
      rootMargin: '100px',
      threshold: 0.1
    }
  );
  
  observer.value.observe(loadMoreTrigger.value);
};

// 标签页切换
const handleTabChange = () => {
  currentPage.value = 1;
  messages.value = [];
  hasMore.value = true;
  loadMessages();
};

// 点击消息卡片
const handleMessageClick = (message: any) => {
  currentMessage.value = message;
  dialogVisible.value = true;
};

// 消息已读回调
const handleMessageRead = (message: any) => {
  // 更新本地状态
  const index = messages.value.findIndex(m => m.id === message.id);
  if (index !== -1) {
    messages.value[index].is_read = true;
  }
};

// 全部已读
const handleMarkAllRead = async () => {
  markingAllRead.value = true;
  try {
    const response = await request({
      url: '/api/system/message_center/mark_all_read/',
      method: 'post'
    });
    
    if (response && response.code === 2000) {
      ElMessage.success('全部消息已标记为已读');
      // 刷新消息列表
      await loadMessages();
    } else {
      ElMessage.error(response?.msg || '标记失败');
    }
  } catch (error: any) {
    ElMessage.error(error?.msg || error?.message || '标记失败');
  } finally {
    markingAllRead.value = false;
  }
};

// 初始化
onMounted(async () => {
  await loadMessages();
  await nextTick();
  setupObserver();
});

// 清理
onUnmounted(() => {
  if (observer.value) {
    observer.value.disconnect();
  }
});
</script>

<style scoped lang="scss" src="./style.scss"></style>
