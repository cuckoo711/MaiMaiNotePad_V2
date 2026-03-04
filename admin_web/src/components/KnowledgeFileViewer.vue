<template>
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    width="80%"
    destroy-on-close
    class="knowledge-file-viewer"
    @opened="onDialogOpened"
  >
    <template #header>
      <div class="dialog-header">
        <span>{{ dialogTitle }}</span>
      </div>
    </template>

    <!-- 浮动操作栏 -->
    <div 
      v-if="fileData && (fileData.file_type === 'json' || fileData.file_type === 'txt')" 
      class="floating-action-bar"
    >
      <!-- 搜索框 -->
      <div class="floating-search-bar" :class="{ expanded: searchExpanded }">
        <transition name="search-expand">
          <div v-if="searchExpanded" class="search-content">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索内容..."
              clearable
              class="search-input"
              @input="handleSearchDebounced"
              @clear="clearSearch"
            >
              <template #prefix>
                <i class="fa fa-search"></i>
              </template>
            </el-input>
            <div v-if="searchKeyword && fileData" class="search-result-info">
              <template v-if="fileData.file_type === 'json'">
                找到 <span class="highlight-count">{{ fileData.total_docs }}</span> 条结果
              </template>
              <template v-else-if="fileData.file_type === 'txt'">
                找到 <span class="highlight-count">{{ fileData.total_paragraphs }}</span> 条结果
              </template>
            </div>
          </div>
        </transition>
        <div class="search-toggle" @click="toggleSearch">
          <i class="fa" :class="searchExpanded ? 'fa-times' : 'fa-search'"></i>
        </div>
      </div>
      
      <!-- 返回顶部按钮 -->
      <transition name="fade">
        <div v-if="showBackTop" class="back-to-top-btn" @click="scrollToTop">
          <i class="fa fa-arrow-up"></i>
        </div>
      </transition>
    </div>

    <div class="viewer-content">
      <div v-if="loading && !fileData" class="viewer-loading">
        <el-skeleton :rows="10" animated />
      </div>
      
      <template v-else>
        <!-- JSON 文件展示 -->
        <div v-if="fileData && fileData.file_type === 'json'" class="json-viewer">
          <div class="viewer-header">
            <div class="header-stats">
              <div class="stat-item">
                <el-statistic title="文档总数" :value="fileData.total_docs">
                  <template #suffix>
                    <span class="stat-unit">篇</span>
                  </template>
                </el-statistic>
              </div>
              
              <div class="stat-item">
                <el-statistic title="总字符数" :value="formatLargeNumber(fileData.metadata?.total_chars || 0)">
                  <template #suffix>
                    <span class="stat-unit">字</span>
                  </template>
                </el-statistic>
                <div class="stat-detail">
                  平均 {{ fileData.metadata?.avg_passage_len?.toFixed(1) }} 字/篇
                </div>
              </div>
              
              <div class="stat-item">
                <el-statistic title="平均实体数" :value="fileData.metadata?.avg_entities" :precision="1">
                  <template #suffix>
                    <span class="stat-unit">个/篇</span>
                  </template>
                </el-statistic>
                <div class="stat-detail">
                  共 {{ fileData.metadata?.total_entities }} 个实体
                </div>
              </div>
              
              <div class="stat-item">
                <el-statistic title="平均三元组数" :value="fileData.metadata?.avg_triples" :precision="1">
                  <template #suffix>
                    <span class="stat-unit">个/篇</span>
                  </template>
                </el-statistic>
                <div class="stat-detail">
                  共 {{ fileData.metadata?.total_triples }} 个三元组
                </div>
              </div>
            </div>
          </div>
          
          <div class="docs-list">
            <div v-if="allDocs.length === 0 && searchKeyword" class="empty-search">
              <i class="fa fa-search"></i>
              <p>未找到匹配的内容</p>
              <el-button text @click="clearSearch">清除搜索</el-button>
            </div>
            <div v-for="(doc, index) in allDocs" :key="doc.idx" class="doc-card">
              <div class="doc-header">
                <span class="doc-index">#{{ index + 1 }}</span>
                <el-tag size="small" type="info">{{ doc.idx.substring(0, 8) }}...</el-tag>
              </div>
              
              <div class="doc-content">
                <div class="doc-section">
                  <div class="section-title">
                    <i class="fa fa-file-text-o"></i>
                    段落内容
                  </div>
                  <div class="section-content passage" v-html="highlightText(doc.passage)"></div>
                </div>
                
                <div class="doc-section">
                  <div class="section-title">
                    <i class="fa fa-tags"></i>
                    提取实体
                  </div>
                  <div class="section-content entities">
                    <el-tag
                      v-for="(entity, idx) in doc.extracted_entities"
                      :key="idx"
                      size="small"
                      class="entity-tag"
                    >
                      {{ entity }}
                    </el-tag>
                  </div>
                </div>
                
                <div class="doc-section">
                  <div class="section-title">
                    <i class="fa fa-sitemap"></i>
                    提取三元组
                  </div>
                  <div class="section-content triples">
                    <div v-for="(triple, idx) in doc.extracted_triples" :key="idx" class="triple-item">
                      <span class="triple-subject">{{ triple[0] }}</span>
                      <i class="fa fa-arrow-right triple-arrow"></i>
                      <span class="triple-predicate">{{ triple[1] }}</span>
                      <i class="fa fa-arrow-right triple-arrow"></i>
                      <span class="triple-object">{{ triple[2] }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 加载更多提示 -->
          <div v-if="hasMore && !loading" class="load-more-tip">
            <span>滚动到底部加载更多...</span>
          </div>
          <div v-if="loading && fileData" class="loading-more">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <div v-if="!hasMore && allDocs.length > 0" class="no-more-tip">
            <span>已加载全部内容</span>
          </div>
        </div>
        
        <!-- TXT 文件展示 -->
        <div v-else-if="fileData && fileData.file_type === 'txt'" class="txt-viewer">
          <div class="viewer-header">
            <el-statistic title="段落总数" :value="fileData.total_paragraphs" />
          </div>
          
          <div class="paragraphs-list">
            <div v-if="fileData.paragraphs && fileData.paragraphs.length === 0 && searchKeyword" class="empty-search">
              <i class="fa fa-search"></i>
              <p>未找到匹配的内容</p>
              <el-button text @click="searchKeyword = ''; handleSearch()">清除搜索</el-button>
            </div>
            <div v-for="(paragraph, index) in fileData.paragraphs" :key="index" class="paragraph-item">
              <div class="paragraph-index">{{ index + 1 }}</div>
              <div class="paragraph-content" v-html="highlightText(paragraph)"></div>
            </div>
          </div>
        </div>
        
        <!-- 压缩包提示 -->
        <div v-else-if="fileData && fileData.file_type === 'archive'" class="archive-viewer">
          <div class="archive-icon">
            <i class="fa fa-file-archive-o"></i>
          </div>
          <div class="archive-message">
            <h3>{{ fileData.message }}</h3>
            <p>文件名：{{ fileData.file_name }}</p>
            <p>文件大小：{{ formatFileSize(fileData.file_size) }}</p>
          </div>
          <el-button type="primary" size="large" @click="handleDownload">
            <i class="fa fa-download"></i>
            下载文件
          </el-button>
        </div>
      </template>
    </div>

    <!-- 底部操作栏 -->
    <template #footer>
      <div class="dialog-footer">
        <!-- 空的 footer，保持布局 -->
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import { Loading } from '@element-plus/icons-vue';

// ==================== 类型定义 ====================
interface FileData {
  file_type: 'json' | 'txt' | 'archive';
  file_name: string;
  file_size?: number;
  message?: string;
  total_docs?: number;
  total_paragraphs?: number;
  docs?: any[];
  paragraphs?: string[];
  metadata?: {
    avg_ent_chars?: number;
    avg_ent_words?: number;
  };
}

// ==================== Props & Emits ====================
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  fileName: {
    type: String,
    default: ''
  },
  knowledgeId: {
    type: String,
    default: ''
  },
  fileId: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:visible', 'download']);

// ==================== 响应式数据 ====================
const loading = ref(false);
const fileData = ref<FileData | null>(null);
const currentPage = ref(1);
const pageSize = ref(20);
const searchKeyword = ref('');
const showBackTop = ref(false);
const dialogBodyRef = ref<HTMLElement | null>(null);
const searchExpanded = ref(false);
const allDocs = ref<any[]>([]);
let searchTimer: number | null = null;

// ==================== 计算属性 ====================
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const dialogTitle = computed(() => {
  return props.title || (props.fileName ? `预览 - ${props.fileName}` : '文件预览');
});

const hasMore = computed(() => {
  if (!fileData.value || fileData.value.file_type !== 'json') return false;
  return allDocs.value.length < (fileData.value.total_docs || 0);
});

const isJsonFile = computed(() => props.fileName.toLowerCase().endsWith('.json'));

/**
 * 格式化大数字（使用 k/w 缩略）
 */
const formatLargeNumber = (num: number): string => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
};

// ==================== 核心方法 ====================
/**
 * 加载文件内容
 * @param append 是否追加到现有数据（用于无限滚动）
 */
const loadFileContent = async (append = false) => {
  if (!props.knowledgeId || !props.fileId) return;
  
  loading.value = true;
  try {
    const { parseKnowledgeFile } = await import('/@/views/content/knowledge/api');
    const params: Record<string, any> = {};
    
    // JSON 文件需要分页参数
    if (isJsonFile.value) {
      params.page = currentPage.value;
      params.page_size = pageSize.value;
    }
    
    // 添加搜索参数
    const trimmedKeyword = searchKeyword.value.trim();
    if (trimmedKeyword) {
      params.search = trimmedKeyword;
    }
    
    const response = await parseKnowledgeFile(props.knowledgeId, props.fileId, params);
    
    if (response.data) {
      fileData.value = response.data;
      
      // JSON 文件：追加或替换文档列表
      if (response.data.file_type === 'json') {
        const newDocs = response.data.docs || [];
        allDocs.value = append ? [...allDocs.value, ...newDocs] : newDocs;
      }
    }
  } catch (error) {
    console.error('加载文件失败:', error);
    ElMessage.error('加载文件失败');
  } finally {
    loading.value = false;
  }
};

/**
 * 加载更多数据（无限滚动）
 */
const loadMore = () => {
  if (!hasMore.value || loading.value) return;
  currentPage.value++;
  loadFileContent(true);
};

/**
 * 处理搜索（带防抖，用户停止输入 0.5 秒后自动搜索）
 */
const handleSearchDebounced = () => {
  // 清除之前的定时器
  if (searchTimer) {
    clearTimeout(searchTimer);
    searchTimer = null;
  }
  
  // 如果对话框还没打开，不执行搜索
  if (!props.visible) return;
  
  // 设置新的定时器，500ms 后执行搜索
  searchTimer = window.setTimeout(() => {
    resetAndLoad();
    searchTimer = null;
  }, 500);
};

/**
 * 清除搜索
 */
const clearSearch = () => {
  // 清除防抖定时器
  if (searchTimer) {
    clearTimeout(searchTimer);
    searchTimer = null;
  }
  searchKeyword.value = '';
  resetAndLoad();
};

/**
 * 重置状态并重新加载
 */
const resetAndLoad = () => {
  currentPage.value = 1;
  allDocs.value = [];
  loadFileContent();
};

/**
 * 切换搜索框展开/收起
 */
const toggleSearch = () => {
  searchExpanded.value = !searchExpanded.value;
  
  // 收起时清空搜索
  if (!searchExpanded.value && searchKeyword.value) {
    clearSearch();
  }
};

/**
 * 返回顶部
 */
const scrollToTop = () => {
  dialogBodyRef.value?.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
};

/**
 * 高亮文本中的搜索关键词
 */
const highlightText = (text: string): string => {
  const trimmedKeyword = searchKeyword.value.trim();
  if (!trimmedKeyword || !text) return text;
  
  // 转义特殊字符
  const escapedKeyword = trimmedKeyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escapedKeyword})`, 'gi');
  return text.replace(regex, '<span class="highlight">$1</span>');
};

/**
 * 格式化文件大小
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Math.round((bytes / Math.pow(k, i)) * 100) / 100} ${sizes[i]}`;
};

/**
 * 处理下载
 */
const handleDownload = () => {
  emit('download');
};

// ==================== 事件处理 ====================
/**
 * 处理滚动事件
 */
const handleScroll = (event: Event) => {
  const target = event.target as HTMLElement;
  const { scrollTop, scrollHeight, clientHeight } = target;
  
  // 显示/隐藏返回顶部按钮
  showBackTop.value = scrollTop > 200;
  
  // 滚动到底部时加载更多（仅 JSON 文件）
  if (fileData.value?.file_type === 'json' && hasMore.value && !loading.value) {
    const distanceToBottom = scrollHeight - scrollTop - clientHeight;
    if (distanceToBottom <= 200) {
      loadMore();
    }
  }
};

/**
 * 对话框打开后的回调
 */
const onDialogOpened = () => {
  nextTick(() => {
    const dialogElement = document.querySelector('.knowledge-file-viewer .el-dialog__body');
    if (dialogElement) {
      dialogBodyRef.value = dialogElement as HTMLElement;
      dialogElement.addEventListener('scroll', handleScroll);
    }
  });
};

/**
 * 清理资源
 */
const cleanup = () => {
  if (dialogBodyRef.value) {
    dialogBodyRef.value.removeEventListener('scroll', handleScroll);
    dialogBodyRef.value = null;
  }
  if (searchTimer) {
    clearTimeout(searchTimer);
    searchTimer = null;
  }
};

// ==================== 生命周期 ====================
onBeforeUnmount(() => {
  cleanup();
});

// ==================== 监听器 ====================
watch(() => props.visible, (newVal, oldVal) => {
  if (!newVal && oldVal) {
    // 对话框关闭时清理资源
    cleanup();
  }
  
  if (newVal && props.knowledgeId && props.fileId) {
    // 对话框打开时重置状态
    cleanup();
    searchKeyword.value = '';
    searchExpanded.value = false;
    currentPage.value = 1;
    allDocs.value = [];
    showBackTop.value = false;
    fileData.value = null;
    loadFileContent();
  }
});
</script>

<script lang="ts">
export default {
  name: 'KnowledgeFileViewer'
};
</script>

<style scoped lang="scss">
.knowledge-file-viewer {
  :deep(.el-dialog__body) {
    padding: 0;
    height: 70vh;
    overflow-y: auto;
    overflow-x: hidden;
    position: relative;
  }
  
  :deep(.el-dialog__header) {
    padding: 20px;
    border-bottom: 1px solid #e0e0e0;
  }
  
  :deep(.el-dialog__footer) {
    padding: 16px 20px;
    border-top: 1px solid #e8e8e8;
    background: #fafafa;
    display: none; // 隐藏 footer
  }
}

.dialog-header {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

// 浮动操作栏（包含搜索和返回顶部）
.floating-action-bar {
  position: fixed;
  top: 80px;
  right: 40px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: flex-end;
}

// 浮动搜索框（毛玻璃效果）
.floating-search-bar {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  
  &.expanded {
    .search-toggle {
      background: linear-gradient(135deg, rgba(160, 82, 45, 0.95) 0%, rgba(212, 165, 116, 0.95) 100%);
    }
  }
  
  .search-content {
    backdrop-filter: blur(20px);
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(212, 165, 116, 0.3);
    border-radius: 20px;
    padding: 20px 24px;
    box-shadow: 0 8px 32px rgba(160, 82, 45, 0.15);
    min-width: 340px;
    
    .search-input {
      :deep(.el-input__wrapper) {
        background: rgba(255, 255, 255, 0.95);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        border-radius: 12px;
        padding: 10px 18px;
        border: 1px solid rgba(212, 165, 116, 0.2);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        
        &:hover {
          border-color: rgba(160, 82, 45, 0.4);
          box-shadow: 0 4px 12px rgba(160, 82, 45, 0.1);
        }
        
        &.is-focus {
          border-color: rgba(160, 82, 45, 0.6);
          box-shadow: 0 4px 16px rgba(160, 82, 45, 0.15);
        }
      }
      
      :deep(.el-input__prefix) {
        color: #a0522d;
      }
      
      :deep(.el-input__inner) {
        font-size: 14px;
        background: transparent;
      }
    }
    
    .search-result-info {
      margin-top: 14px;
      font-size: 13px;
      color: #666;
      text-align: center;
      padding: 8px 12px;
      background: rgba(160, 82, 45, 0.05);
      border-radius: 8px;
      
      .highlight-count {
        font-weight: 700;
        color: #a0522d;
        font-size: 16px;
        margin: 0 4px;
      }
    }
  }
  
  .search-toggle {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    backdrop-filter: blur(20px);
    background: linear-gradient(135deg, rgba(212, 165, 116, 0.9) 0%, rgba(160, 82, 45, 0.9) 100%);
    border: 2px solid rgba(255, 255, 255, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 20px rgba(160, 82, 45, 0.25);
    
    &:hover {
      background: linear-gradient(135deg, rgba(160, 82, 45, 0.95) 0%, rgba(212, 165, 116, 0.95) 100%);
      transform: scale(1.08);
      box-shadow: 0 6px 24px rgba(160, 82, 45, 0.35);
      border-color: rgba(255, 255, 255, 0.8);
    }
    
    &:active {
      transform: scale(0.98);
    }
    
    i {
      color: white;
      font-size: 20px;
    }
  }
}

// 返回顶部按钮（放在搜索按钮下方）
.back-to-top-btn {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  backdrop-filter: blur(20px);
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.9) 0%, rgba(160, 82, 45, 0.9) 100%);
  border: 2px solid rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 20px rgba(160, 82, 45, 0.25);
  
  &:hover {
    background: linear-gradient(135deg, rgba(160, 82, 45, 0.95) 0%, rgba(212, 165, 116, 0.95) 100%);
    transform: scale(1.08) translateY(-2px);
    box-shadow: 0 6px 24px rgba(160, 82, 45, 0.35);
    border-color: rgba(255, 255, 255, 0.8);
  }
  
  &:active {
    transform: scale(0.98);
  }
  
  i {
    color: white;
    font-size: 20px;
  }
}

// 搜索框展开动画
.search-expand-enter-active,
.search-expand-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.search-expand-enter-from {
  opacity: 0;
  transform: translateX(20px) scale(0.95);
}

.search-expand-leave-to {
  opacity: 0;
  transform: translateX(20px) scale(0.95);
}

.viewer-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  position: relative;
}

.viewer-content {
  padding: 20px;
}

.viewer-loading {
  padding: 20px;
}

// 高亮样式
:deep(.highlight) {
  background: linear-gradient(120deg, #fff5e6 0%, #ffe4b3 100%);
  color: #a0522d;
  font-weight: 600;
  padding: 2px 4px;
  border-radius: 3px;
  box-shadow: 0 1px 3px rgba(160, 82, 45, 0.1);
}

// 空搜索结果样式
.empty-search {
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
    margin: 0 0 16px 0;
    font-size: 15px;
    color: #999;
  }
  
  .el-button {
    color: #a0522d;
    
    &:hover {
      color: #d4a574;
    }
  }
}

.viewer-header {
  margin-bottom: 32px;
  padding: 36px;
  background: linear-gradient(135deg, #f5e6d3 0%, #e8d4b8 100%);
  border-radius: 20px;
  color: #5d3a1a;
  box-shadow: 0 6px 20px rgba(160, 82, 45, 0.12);
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.2) 0%, transparent 70%);
    border-radius: 50%;
  }
  
  .header-stats {
    display: flex;
    gap: 40px;
    justify-content: space-evenly;
    position: relative;
    z-index: 1;
    width: 100%;
    
    .stat-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      flex: 1;
      min-width: 0;
    }
    
    :deep(.el-statistic) {
      .el-statistic__head {
        color: #8b6239;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
        letter-spacing: 0.5px;
        text-align: center;
      }
      
      .el-statistic__content {
        color: #5d3a1a;
        font-size: 32px;
        font-weight: 700;
        display: flex;
        align-items: baseline;
        justify-content: center;
        
        .el-statistic__number {
          font-variant-numeric: tabular-nums;
        }
      }
    }
    
    .stat-unit {
      font-size: 16px;
      font-weight: 500;
      color: #8b6239;
      margin-left: 6px;
    }
    
    .stat-detail {
      font-size: 12px;
      color: #a0826d;
      font-weight: 500;
      padding: 4px 12px;
      background: rgba(160, 82, 45, 0.08);
      border-radius: 12px;
      white-space: nowrap;
    }
  }
}

// JSON 文件样式
.json-viewer {
  .docs-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .doc-card {
    background: white;
    border: 1px solid #f5f5f5;
    border-radius: 16px;
    padding: 28px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
    
    &:hover {
      box-shadow: 0 12px 32px rgba(160, 82, 45, 0.12);
      border-color: #e8d4b8;
      transform: translateY(-4px);
    }
    
    .doc-header {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 24px;
      padding-bottom: 18px;
      border-bottom: 2px solid #f8f8f8;
      
      .doc-index {
        font-size: 20px;
        font-weight: 700;
        color: #a0522d;
        background: linear-gradient(135deg, #fff5f0 0%, #ffe8d9 100%);
        padding: 6px 16px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(160, 82, 45, 0.08);
      }
      
      .el-tag {
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 12px;
      }
    }
    
    .doc-content {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    
    .doc-section {
      .section-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 14px;
        font-weight: 600;
        color: #5d3a1a;
        margin-bottom: 12px;
        
        i {
          color: #a0522d;
          font-size: 16px;
        }
      }
      
      .section-content {
        padding: 16px;
        background: #fafafa;
        border-radius: 8px;
        border: 1px solid #f0f0f0;
        
        &.passage {
          line-height: 1.8;
          color: #333;
          font-size: 14px;
        }
        
        &.entities {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          
          .entity-tag {
            background: linear-gradient(135deg, #fff5f0 0%, #ffe8d9 100%);
            border-color: #d4a574;
            color: #8b6239;
            font-weight: 500;
            padding: 6px 14px;
            border-radius: 16px;
          }
        }
        
        &.triples {
          display: flex;
          flex-direction: column;
          gap: 10px;
          
          .triple-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            background: white;
            border-radius: 8px;
            border: 1px solid #f0f0f0;
            transition: all 0.2s;
            
            &:hover {
              border-color: #e8d4b8;
              box-shadow: 0 2px 8px rgba(160, 82, 45, 0.05);
            }
            
            .triple-subject,
            .triple-object {
              padding: 6px 12px;
              background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
              border-radius: 6px;
              color: #1565c0;
              font-weight: 500;
              font-size: 13px;
            }
            
            .triple-predicate {
              padding: 6px 12px;
              background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
              border-radius: 6px;
              color: #e65100;
              font-weight: 500;
              font-size: 13px;
            }
            
            .triple-arrow {
              color: #bbb;
              font-size: 14px;
            }
          }
        }
      }
    }
  }
  
  // 加载提示
  .load-more-tip,
  .loading-more,
  .no-more-tip {
    text-align: center;
    padding: 32px 20px;
    font-size: 14px;
    margin-top: 24px;
  }
  
  .load-more-tip {
    color: #a0522d;
    font-weight: 500;
    
    span {
      padding: 10px 24px;
      background: linear-gradient(135deg, #fff5f0 0%, #ffe8d9 100%);
      border-radius: 24px;
      border: 2px dashed #d4a574;
      display: inline-block;
      transition: all 0.3s;
      
      &:hover {
        background: linear-gradient(135deg, #ffe8d9 0%, #ffd9bf 100%);
        border-color: #a0522d;
      }
    }
  }
  
  .loading-more {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: #a0522d;
    font-weight: 500;
    
    .el-icon {
      font-size: 20px;
    }
  }
  
  .no-more-tip {
    color: #bbb;
    font-size: 13px;
    font-style: italic;
  }
}

// TXT 文件样式
.txt-viewer {
  .paragraphs-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .paragraph-item {
    display: flex;
    gap: 16px;
    padding: 16px;
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    transition: all 0.3s;
    
    &:hover {
      box-shadow: 0 2px 8px rgba(212, 165, 116, 0.1);
      border-color: #d4a574;
    }
    
    .paragraph-index {
      flex-shrink: 0;
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #d4a574 0%, #a0522d 100%);
      color: white;
      border-radius: 50%;
      font-weight: 600;
      font-size: 14px;
    }
    
    .paragraph-content {
      flex: 1;
      line-height: 1.8;
      color: #333;
    }
  }
}

// 压缩包样式
.archive-viewer {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  
  .archive-icon {
    font-size: 80px;
    color: #a0522d;
    margin-bottom: 24px;
    opacity: 0.8;
  }
  
  .archive-message {
    margin-bottom: 32px;
    
    h3 {
      font-size: 20px;
      color: #333;
      margin-bottom: 16px;
    }
    
    p {
      font-size: 14px;
      color: #666;
      margin: 8px 0;
    }
  }
  
  .el-button {
    padding: 12px 32px;
    font-size: 16px;
    
    i {
      margin-right: 8px;
    }
  }
}

// 底部操作栏（保持空白）
.dialog-footer {
  min-height: 20px;
}

// 淡入淡出动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
