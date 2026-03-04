<template>
  <fs-page>
    <div class="user-messages-container">
      <!-- 顶部区域：标签页 + 免打扰设置 + 全部已读按钮 -->
      <div class="message-header">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="message-tabs">
          <el-tab-pane label="全部" name="all"></el-tab-pane>
          <el-tab-pane label="通知" name="notice"></el-tab-pane>
          <el-tab-pane label="评论" name="comment"></el-tab-pane>
          <el-tab-pane label="回复" name="reply"></el-tab-pane>
          <el-tab-pane label="赞" name="like"></el-tab-pane>
        </el-tabs>
        
        <div class="header-actions">
          <el-icon 
            class="mute-settings-icon" 
            @click="showMuteDialog = true"
            title="免打扰设置"
          >
            <ele-Setting />
          </el-icon>
          
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

      <!-- 免打扰设置对话框 -->
      <el-dialog
        v-model="showMuteDialog"
        title="免打扰设置"
        width="500px"
      >
        <div class="mute-settings-content" v-loading="loadingPreferences">
          <el-alert
            title="提示"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 20px;"
          >
            开启免打扰后，该类型的新消息将自动标记为已读，不再提醒。系统通知和审核通知不可设置免打扰。
          </el-alert>

          <div class="mute-item" v-for="item in muteSettings" :key="item.type">
            <div class="mute-item-info">
              <div class="mute-item-title">
                <el-icon :style="{ color: item.color }">
                  <component :is="item.icon" />
                </el-icon>
                <span>{{ item.label }}</span>
              </div>
              <div class="mute-item-desc">{{ item.description }}</div>
            </div>
            <el-switch
              v-model="item.muted"
              :disabled="item.disabled"
              @change="handleMuteChange(item)"
            />
          </div>
        </div>

        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showMuteDialog = false">取消</el-button>
            <el-button type="primary" @click="handleSaveMuteSettings" :loading="savingPreferences">
              确定
            </el-button>
          </span>
        </template>
      </el-dialog>
    </div>
  </fs-page>
</template>

<script setup lang="ts" name="userMessages">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
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

// 免打扰设置相关
const showMuteDialog = ref(false);
const loadingPreferences = ref(false);
const savingPreferences = ref(false);
const muteSettings = ref([
  {
    type: 1,
    label: '评论通知',
    description: '当有人评论您的内容时',
    icon: 'ChatDotRound',
    color: '#67C23A',
    muted: false,
    disabled: false,
    changed: false
  },
  {
    type: 2,
    label: '回复通知',
    description: '当有人回复您的评论时',
    icon: 'ChatLineRound',
    color: '#409EFF',
    muted: false,
    disabled: false,
    changed: false
  },
  {
    type: 3,
    label: '点赞通知',
    description: '当有人点赞您的内容或评论时',
    icon: 'Star',
    color: '#F56C6C',
    muted: false,
    disabled: false,
    changed: false
  }
]);

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
      return '2'; // 回复
    case 'like':
      return '3'; // 点赞
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

// 加载免打扰偏好设置
const loadMutePreferences = async () => {
  loadingPreferences.value = true;
  try {
    const response = await request({
      url: '/api/system/user_notification_preference/get_preferences/',
      method: 'get'
    });
    
    if (response && response.code === 2000) {
      const preferences = response.data || {};
      // 更新设置状态
      muteSettings.value.forEach(item => {
        if (preferences[item.type]) {
          item.muted = preferences[item.type].is_muted;
        }
        item.changed = false;
      });
    }
  } catch (error: any) {
    console.error('加载免打扰设置失败:', error);
  } finally {
    loadingPreferences.value = false;
  }
};

// 处理免打扰开关变化
const handleMuteChange = (item: any) => {
  item.changed = true;
};

// 保存免打扰设置
const handleSaveMuteSettings = async () => {
  // 找出有变化的设置项
  const changedItems = muteSettings.value.filter(item => item.changed);
  
  if (changedItems.length === 0) {
    showMuteDialog.value = false;
    return;
  }
  
  savingPreferences.value = true;
  try {
    // 批量处理所有变化的设置
    const promises = changedItems.map(item => {
      const url = item.muted
        ? '/api/system/user_notification_preference/set_mute/'
        : '/api/system/user_notification_preference/cancel_mute/';
      
      return request({
        url,
        method: 'post',
        data: { message_type: item.type }
      });
    });
    
    const results = await Promise.all(promises);
    
    // 检查是否全部成功
    const allSuccess = results.every(res => res && res.code === 2000);
    
    if (allSuccess) {
      ElMessage.success('免打扰设置已保存');
      // 重置变化标记
      muteSettings.value.forEach(item => {
        item.changed = false;
      });
      showMuteDialog.value = false;
      
      // 刷新当前消息列表
      await loadMessages();
    } else {
      ElMessage.error('部分设置保存失败，请重试');
    }
  } catch (error: any) {
    ElMessage.error(error?.msg || error?.message || '保存失败');
  } finally {
    savingPreferences.value = false;
  }
};

// 监听对话框状态，打开时加载最新设置
watch(showMuteDialog, (newVal) => {
  if (newVal) {
    loadMutePreferences();
  }
});

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
