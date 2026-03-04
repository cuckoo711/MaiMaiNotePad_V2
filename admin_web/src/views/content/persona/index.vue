<template>
  <div class="persona-plaza-wrapper">
    <PlazaView
      :loading="loading"
      :data-list="personaList"
      :total="total"
      :popular-tags="popularTags"
      :hot-list="hotPersonas"
      :new-list="newPersonas"
      :show-version-filter="true"
      empty-text="暂无人设卡"
      @search="handleSearch"
      @show-detail="showDetail"
      @toggle-star="toggleStar"
    />

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailVisible"
      direction="rtl"
      size="50%"
      :with-header="false"
      destroy-on-close
      class="persona-detail-drawer"
    >
      <div v-if="currentDetail" class="drawer-container">
        <!-- 自定义头部 -->
        <div class="drawer-header">
          <div class="header-content">
            <div class="title-section">
              <h2 class="drawer-title">{{ currentDetail?.name || '人设卡详情' }}</h2>
              <el-tag
                v-if="currentDetail && currentDetail.version"
                size="large"
                class="version-tag"
              >
                v{{ currentDetail.version }}
              </el-tag>
            </div>
            <div class="header-meta">
              <span class="meta-item">
                <i class="fa fa-user"></i>
                {{ currentDetail.uploader_name || '匿名' }}
              </span>
              <span class="meta-item">
                <i class="fa fa-download"></i>
                {{ currentDetail.downloads || 0 }} 次下载
              </span>
              <span class="meta-item">
                <i class="fa fa-star"></i>
                {{ currentDetail.star_count || 0 }} 次收藏
              </span>
            </div>
          </div>
        </div>

        <!-- 内容区域 -->
        <div class="drawer-body">
          <el-tabs v-model="activeTab" class="detail-tabs">
            <!-- 基本信息 -->
            <el-tab-pane name="info">
              <template #label>
                <span class="tab-label">
                  <i class="fa fa-info-circle"></i>
                  基本信息
                </span>
              </template>
              <div class="info-content">
                <!-- 描述卡片 -->
                <div class="info-card description-card">
                  <h3 class="card-title">
                    <i class="fa fa-align-left"></i>
                    描述
                  </h3>
                  <p class="description-text">
                    {{ currentDetail.description || '暂无描述' }}
                  </p>
                </div>

                <!-- 详细信息卡片 -->
                <div class="info-card details-card">
                  <h3 class="card-title">
                    <i class="fa fa-list-ul"></i>
                    详细信息
                  </h3>
                  <div class="details-grid">
                    <div class="detail-item">
                      <span class="detail-label">版权所有者</span>
                      <span class="detail-value">{{ currentDetail.copyright_owner || '未知' }}</span>
                    </div>
                    <div class="detail-item">
                      <span class="detail-label">版本号</span>
                      <span class="detail-value">
                        <el-tag size="small" type="info">v{{ currentDetail.version || '1.0' }}</el-tag>
                      </span>
                    </div>
                  </div>
                </div>

                <!-- 内容卡片 -->
                <div v-if="currentDetail.content" class="info-card content-card">
                  <h3 class="card-title">
                    <i class="fa fa-file-text-o"></i>
                    内容
                  </h3>
                  <div class="content-text">{{ currentDetail.content }}</div>
                </div>
              </div>
            </el-tab-pane>

            <!-- 文件列表 -->
            <el-tab-pane name="files">
              <template #label>
                <span class="tab-label">
                  <i class="fa fa-folder-open"></i>
                  文件列表<span v-if="currentDetail.files && currentDetail.files.length" class="file-count">（{{ currentDetail.files.length }}）</span>
                </span>
              </template>
              <div class="files-content">
                <div v-if="currentDetail.files && currentDetail.files.length" class="files-grid">
                  <div 
                    v-for="file in currentDetail.files" 
                    :key="file.id" 
                    class="file-card"
                    @click="previewFile(file)"
                  >
                    <div class="file-icon">
                      <i class="fa fa-file-o"></i>
                    </div>
                    <div class="file-info">
                      <div class="file-name" :title="file.original_name">
                        {{ file.original_name }}
                      </div>
                      <div class="file-meta">
                        <span class="file-size">{{ formatFileSize(file.file_size) }}</span>
                      </div>
                    </div>
                    <el-icon 
                      class="download-btn"
                      :size="20"
                      @click.stop="downloadFile(file)"
                    >
                      <Download />
                    </el-icon>
                  </div>
                </div>
                <div v-else class="empty-state">
                  <i class="fa fa-folder-open-o"></i>
                  <p>暂无文件</p>
                </div>
              </div>
            </el-tab-pane>

            <!-- 评论区 -->
            <el-tab-pane name="comments">
              <template #label>
                <span class="tab-label">
                  <i class="fa fa-comments"></i>
                  评论<span v-if="currentDetail?.comment_count" class="comment-badge">（{{ formatCommentCount(currentDetail.comment_count) }}）</span>
                </span>
              </template>
              <div class="comments-content">
                <CommentSection
                  v-if="currentDetail?.id"
                  :target-id="String(currentDetail.id)"
                  target-type="persona"
                  :show-header="false"
                />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 底部操作栏 -->
        <div class="drawer-footer">
          <el-button 
            type="primary" 
            size="large"
            @click="handleStar"
          >
            <i class="fa" :class="currentDetail?.is_starred ? 'fa-star' : 'fa-star-o'"></i>
            {{ currentDetail?.is_starred ? '取消收藏' : '收藏' }}
          </el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 文件浏览弹窗 -->
    <FileViewerDialog
      v-model:visible="fileViewerVisible"
      :title="fileViewerTitle"
      :file-name="fileViewerFileName"
      :persona-id="currentDetail?.id"
      :file-id="fileViewerFile?.id"
      @download="downloadFromViewer"
    />
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Download } from '@element-plus/icons-vue';
import { PlazaView } from '/@/components/plaza';
import FileViewerDialog from '/@/components/FileViewerDialog.vue';
import CommentSection from '/@/components/CommentSection.vue';
import * as api from './api';

// 状态管理
const loading = ref(false);
const personaList = ref<any[]>([]);
const total = ref(0);

// 详情弹窗
const detailVisible = ref(false);
const currentDetail = ref<any>(null);
const activeTab = ref('info');

// 热门标签
const popularTags = ref<string[]>([]);

// 右侧卡片数据
const hotPersonas = ref<any[]>([]);
const newPersonas = ref<any[]>([]);

// 文件浏览器
const fileViewerVisible = ref(false);
const fileViewerTitle = ref('');
const fileViewerFileName = ref('');
const fileViewerFile = ref<any>(null);

// 加载热门标签
const loadPopularTags = async () => {
  try {
    const res = await api.getPopularTags(12, 'persona');
    if (res.code === 2000 && res.data) {
      popularTags.value = res.data.map((item: any) => item.tag);
    }
  } catch (error) {
    console.error('加载热门标签失败:', error);
  }
};

// 加载人设卡列表
const loadPersonaList = async (searchParams: any) => {
  loading.value = true;
  try {
    const params: any = {
      page: searchParams.page,
      page_size: searchParams.page_size,
    };

    // 搜索关键词
    if (searchParams.search) {
      params.search = searchParams.search;
      if (searchParams.orderBy !== 'relevance') {
        if (searchParams.orderBy === 'hot') {
          params.ordering = '-downloads,-star_count';
        } else {
          params.ordering = searchParams.orderBy;
        }
      }
    } else {
      if (searchParams.orderBy === 'relevance' || searchParams.orderBy === 'hot') {
        params.ordering = '-downloads,-star_count';
      } else {
        params.ordering = searchParams.orderBy;
      }
    }

    // 只显示收藏
    if (searchParams.starred) {
      params.starred = true;
    }

    // 标签筛选
    if (searchParams.tags && searchParams.tags.length > 0) {
      params.tags = searchParams.tags.join(',');
    }

    // 版本号筛选
    if (searchParams.version) {
      params.version = searchParams.version;
    }

    const res = await api.getPersonaList(params);
    if (res.code === 2000) {
      if (Array.isArray(res.data)) {
        personaList.value = res.data;
        total.value = res.total || res.data.length;
      } else {
        personaList.value = res.data.results || res.data || [];
        total.value = res.data.count || res.total || personaList.value.length;
      }
    }
  } catch (error) {
    console.error('加载人设卡列表失败:', error);
    ElMessage.error('加载失败');
  } finally {
    loading.value = false;
  }
};

// 处理搜索
const handleSearch = (params: any) => {
  loadPersonaList(params);
};

// 显示详情
const showDetail = async (item: any) => {
  try {
    const res = await api.getPersonaDetail(item.id);
    if (res.code === 2000) {
      currentDetail.value = res.data;
      detailVisible.value = true;
      activeTab.value = 'info';
    }
  } catch (error) {
    console.error('加载详情失败:', error);
    ElMessage.error('加载详情失败');
  }
};

// 刷新详情数据
const refreshDetailData = async () => {
  if (!currentDetail.value) return;
  try {
    const res = await api.getPersonaDetail(currentDetail.value.id);
    if (res.code === 2000) {
      currentDetail.value = res.data;
    }
  } catch (error) {
    console.error('刷新详情失败:', error);
  }
};

// 收藏/取消收藏（卡片上的按钮）
const toggleStar = async (item: any) => {
  try {
    if (item.is_starred) {
      await api.unstarPersona(item.id);
      ElMessage.success('取消收藏成功');
      item.is_starred = false;
      item.star_count = (item.star_count || 1) - 1;
    } else {
      await api.starPersona(item.id);
      ElMessage.success('收藏成功');
      item.is_starred = true;
      item.star_count = (item.star_count || 0) + 1;
    }
  } catch (error) {
    console.error('操作失败:', error);
    ElMessage.error('操作失败');
  }
};

// 收藏/取消收藏（详情弹窗中的按钮）
const handleStar = async () => {
  if (!currentDetail.value) return;
  
  try {
    if (currentDetail.value.is_starred) {
      await api.unstarPersona(currentDetail.value.id);
      ElMessage.success('取消收藏成功');
      currentDetail.value.is_starred = false;
      currentDetail.value.star_count = (currentDetail.value.star_count || 1) - 1;
    } else {
      await api.starPersona(currentDetail.value.id);
      ElMessage.success('收藏成功');
      currentDetail.value.is_starred = true;
      currentDetail.value.star_count = (currentDetail.value.star_count || 0) + 1;
    }
    // 重新加载列表
    handleSearch({
      page: 1,
      page_size: 12,
      orderBy: 'hot',
      search: '',
      tags: [],
      starred: false
    });
  } catch (error) {
    console.error('操作失败:', error);
    ElMessage.error('操作失败');
  }
};

// 下载文件
const downloadFile = async (file: any) => {
  try {
    const res = await api.downloadPersonaFile(currentDetail.value.id, file.id);
    const url = window.URL.createObjectURL(new Blob([res]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', file.original_name);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    ElMessage.success('下载成功');
    
    await refreshDetailData();
    handleSearch({
      page: 1,
      page_size: 12,
      orderBy: 'hot',
      search: '',
      tags: [],
      starred: false
    });
  } catch (error) {
    console.error('下载失败:', error);
    ElMessage.error('下载失败');
  }
};

// 预览文件
const previewFile = async (file: any) => {
  if (!currentDetail.value) {
    ElMessage.error('未找到要预览的人设卡');
    return;
  }
  
  const fileName = file.original_name || '';
  const lowerName = fileName.toLowerCase();
  
  // 检查是否支持预览
  if (!lowerName.endsWith('.toml') && !lowerName.endsWith('.json') && !lowerName.endsWith('.txt')) {
    ElMessage.warning('当前文件类型暂不支持在线预览，请使用下载功能查看');
    return;
  }
  
  fileViewerTitle.value = fileName || '文件预览';
  fileViewerFileName.value = fileName;
  fileViewerFile.value = file;
  fileViewerVisible.value = true;
};

// 从浏览器下载文件
const downloadFromViewer = async () => {
  if (!fileViewerFile.value) {
    return;
  }
  await downloadFile(fileViewerFile.value);
};

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

// 格式化评论数量
const formatCommentCount = (count: number): string => {
  if (!count) return '0';
  if (count > 999) return '999+';
  return count.toString();
};

// 加载右侧卡片数据
const loadSidebarData = async () => {
  try {
    // 加载热门推荐
    const hotRes = await api.getPersonaList({
      page: 1,
      page_size: 5,
      ordering: '-downloads'
    });
    if (hotRes.code === 2000) {
      if (Array.isArray(hotRes.data)) {
        hotPersonas.value = hotRes.data;
      } else {
        hotPersonas.value = hotRes.data.results || hotRes.data || [];
      }
    }

    // 加载最新上传
    const newRes = await api.getPersonaList({
      page: 1,
      page_size: 5,
      ordering: '-create_datetime'
    });
    if (newRes.code === 2000) {
      if (Array.isArray(newRes.data)) {
        newPersonas.value = newRes.data;
      } else {
        newPersonas.value = newRes.data.results || newRes.data || [];
      }
    }
  } catch (error) {
    console.error('加载侧边栏数据失败:', error);
  }
};

// 页面加载
onMounted(() => {
  loadPopularTags();
  loadSidebarData();
  // 初始加载
  handleSearch({
    page: 1,
    page_size: 12,
    orderBy: 'hot',
    search: '',
    tags: [],
    starred: false
  });
});
</script>

<script lang="ts">
export default {
  name: 'PersonaPlaza'
};
</script>

<style scoped lang="scss">
.persona-plaza-wrapper {
  width: 100%;
  height: 100%;
}

// 抽屉整体样式
.persona-detail-drawer {
  :deep(.el-drawer) {
    border-radius: 0;
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
  }

  :deep(.el-drawer__body) {
    padding: 0;
    overflow: hidden;
  }
}

// 抽屉容器
.drawer-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(to bottom, #fafafa 0%, #ffffff 100px);
}

// 自定义头部
.drawer-header {
  position: relative;
  padding: 32px 32px 24px;
  background: linear-gradient(135deg, #d4a574 0%, #a0522d 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(212, 165, 116, 0.15);

  .header-content {
    width: 100%;
  }

  .title-section {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;

    .drawer-title {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
      color: white;
      line-height: 1.3;
    }

    .version-tag {
      padding: 6px 14px;
      background: rgba(255, 255, 255, 0.25);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.3);
      color: white;
      font-weight: 600;
      font-size: 13px;
      border-radius: 20px;
    }
  }

  .header-meta {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.95);
      font-weight: 500;

      i {
        font-size: 16px;
        opacity: 0.9;
      }
    }
  }
}

// 内容区域
.drawer-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  .detail-tabs {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;

    :deep(.el-tabs__header) {
      margin: 0;
      padding: 0 32px;
      background: white;
      border-bottom: 2px solid #f0f0f0;
    }

    :deep(.el-tabs__nav-wrap::after) {
      display: none;
    }

    :deep(.el-tabs__item) {
      padding: 0 24px;
      height: 56px;
      line-height: 56px;
      font-size: 15px;
      font-weight: 500;
      color: #666;
      transition: all 0.3s;

      &:hover {
        color: #a0522d;
      }

      &.is-active {
        color: #a0522d;
      }
    }

    :deep(.el-tabs__active-bar) {
      height: 3px;
      background: linear-gradient(90deg, #d4a574 0%, #a0522d 100%);
      border-radius: 3px 3px 0 0;
    }

    :deep(.el-tabs__content) {
      flex: 1;
      overflow-y: auto;
      padding: 0;
    }

    .tab-label {
      display: flex;
      align-items: center;
      gap: 8px;

      i {
        font-size: 16px;
      }

      .file-count {
        margin-left: 2px;
        font-size: 14px;
        opacity: 0.9;
      }
    }
  }
}

// 基本信息内容
.info-content {
  padding: 24px 32px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid #f0f0f0;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 4px 16px rgba(212, 165, 116, 0.1);
    border-color: #f5e6d3;
  }

  .card-title {
    margin: 0 0 16px 0;
    font-size: 16px;
    font-weight: 600;
    color: #333;
    display: flex;
    align-items: center;
    gap: 10px;

    i {
      color: #a0522d;
      font-size: 18px;
    }
  }
}

.description-card {
  .description-text {
    margin: 0;
    line-height: 1.8;
    color: #555;
    font-size: 14px;
  }
}

.details-card {
  .details-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;

    .detail-item {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .detail-label {
        font-size: 12px;
        color: #999;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .detail-value {
        font-size: 15px;
        color: #333;
        font-weight: 600;
      }
    }
  }
}

.content-card {
  .content-text {
    white-space: pre-wrap;
    line-height: 1.8;
    color: #555;
    font-size: 14px;
    background: #f8f9fa;
    padding: 16px;
    border-radius: 8px;
    border-left: 3px solid #a0522d;
  }
}

// 文件列表内容
.files-content {
  padding: 24px 32px 32px;
}

.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.file-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 2px solid #f0f0f0;
  transition: all 0.3s;
  cursor: pointer;

  &:hover {
    border-color: #a0522d;
    box-shadow: 0 4px 16px rgba(212, 165, 116, 0.15);
    transform: translateY(-2px);

    .file-icon {
      background: linear-gradient(135deg, #d4a574 0%, #a0522d 100%);

      i {
        color: white;
      }
    }

    .download-btn {
      opacity: 1;
    }
  }

  .file-icon {
    width: 48px;
    height: 48px;
    border-radius: 10px;
    background: #f5f7fa;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.3s;

    i {
      font-size: 24px;
      color: #a0522d;
      transition: all 0.3s;
    }
  }

  .file-info {
    flex: 1;
    min-width: 0;

    .file-name {
      font-size: 14px;
      font-weight: 600;
      color: #333;
      margin-bottom: 6px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .file-meta {
      display: flex;
      gap: 12px;
      font-size: 12px;

      .file-size {
        color: #999;
      }
    }
  }

  .download-btn {
    flex-shrink: 0;
    color: #999;
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      color: #a0522d;
      transform: scale(1.2);
    }
  }
}

// 空状态
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #999;

  i {
    font-size: 64px;
    margin-bottom: 16px;
    display: block;
    opacity: 0.3;
    color: #a0522d;
  }

  p {
    margin: 0;
    font-size: 15px;
    color: #999;
  }
}

// 底部操作栏
.drawer-footer {
  padding: 20px 32px;
  background: white;
  border-top: 2px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.04);

  .el-button {
    min-width: 100px;
    font-weight: 500;
    border-radius: 8px;
    transition: all 0.3s;

    &.el-button--primary {
      background: linear-gradient(135deg, #d4a574 0%, #a0522d 100%);
      border: none;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(212, 165, 116, 0.4);
      }
    }

    &:not(.el-button--primary) {
      &:hover {
        border-color: #a0522d;
        color: #a0522d;
      }
    }
  }
}

// 评论区内容
.comments-content {
  padding: 0;
  
  :deep(.comment-section) {
    margin-top: 0;
    padding: 24px 32px 32px;
    background: transparent;
    box-shadow: none;
    border-radius: 0;
  }
}
</style>
