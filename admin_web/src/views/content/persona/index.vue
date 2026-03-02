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

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="currentDetail?.name"
      width="800px"
      class="detail-dialog"
    >
    <div v-if="currentDetail" class="detail-content">
      <el-tabs v-model="activeTab">
        <!-- 基本信息 -->
        <el-tab-pane label="基本信息" name="info">
          <div class="info-section">
            <div class="info-row">
              <span class="info-label">人设卡名称:</span>
              <span class="info-value">{{ currentDetail.name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">上传者:</span>
              <span class="info-value">{{ currentDetail.uploader_name || '匿名' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">版权所有者:</span>
              <span class="info-value">{{ currentDetail.copyright_owner || '未知' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">版本号:</span>
              <span class="info-value">
                <span class="version-badge">v{{ currentDetail.version || '1.0' }}</span>
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">下载次数:</span>
              <span class="info-value">{{ currentDetail.downloads || 0 }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">收藏数:</span>
              <span class="info-value">{{ currentDetail.star_count || 0 }}</span>
            </div>
            <div class="info-row full-width">
              <span class="info-label">描述:</span>
              <div class="info-value">{{ currentDetail.description || '暂无描述' }}</div>
            </div>
            <div class="info-row full-width" v-if="currentDetail.content">
              <span class="info-label">内容:</span>
              <div class="info-value content-text">{{ currentDetail.content }}</div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 文件列表 -->
        <el-tab-pane label="文件列表" name="files">
          <div class="files-list">
            <div 
              v-for="file in currentDetail.files" 
              :key="file.id" 
              class="file-item"
            >
              <div class="file-info">
                <i class="fa fa-file-o"></i>
                <span class="file-name">{{ file.original_name }}</span>
                <span class="file-size">{{ formatFileSize(file.file_size) }}</span>
              </div>
              <el-button size="small" type="primary" @click="downloadFile(file)">
                <i class="fa fa-download"></i> 下载
              </el-button>
            </div>
            <div v-if="!currentDetail.files || currentDetail.files.length === 0" class="empty-files">
              <i class="fa fa-folder-open-o"></i>
              <p>暂无文件</p>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleStar">
          <i class="fa" :class="currentDetail?.is_starred ? 'fa-star' : 'fa-star-o'"></i>
          {{ currentDetail?.is_starred ? '取消收藏' : '收藏' }}
        </el-button>
      </div>
    </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { PlazaView } from '/@/components/plaza';
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

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
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

// 详情弹窗样式
.detail-dialog {
  .detail-content {
    .info-section {
      .info-row {
        display: flex;
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;

        &.full-width {
          flex-direction: column;

          .info-value {
            margin-top: 8px;
          }
        }

        .info-label {
          width: 120px;
          color: #666;
          flex-shrink: 0;
        }

        .info-value {
          flex: 1;
          color: #333;

          &.content-text {
            white-space: pre-wrap;
            line-height: 1.6;
          }

          .version-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 12px;
            background: rgba(160, 82, 45, 0.1);
            color: #A0522D;
            border-radius: 14px;
            font-size: 12px;
            font-weight: 500;
          }
        }
      }
    }

    .files-list {
      .file-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        margin-bottom: 10px;

        .file-info {
          display: flex;
          align-items: center;
          gap: 10px;
          flex: 1;

          i {
            font-size: 20px;
            color: #666;
          }

          .file-name {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .file-size {
            color: #999;
            font-size: 12px;
          }
        }
      }

      .empty-files {
        text-align: center;
        padding: 40px;
        color: #999;

        i {
          font-size: 48px;
          margin-bottom: 10px;
          display: block;
        }
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}
</style>
