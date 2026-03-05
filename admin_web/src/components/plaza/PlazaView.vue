<template>
  <div class="plaza-container">
    <!-- 左侧主内容区 -->
    <div class="main-content">
      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <!-- 排序选择 -->
        <el-select 
          v-model="orderBy" 
          placeholder="排序方式"
          style="width: 140px;"
          @change="handleOrderChange"
        >
          <el-option label="相关度" value="relevance" />
          <el-option label="最热门" value="hot" />
          <el-option label="最新" value="-create_datetime" />
          <el-option label="最早" value="create_datetime" />
          <el-option label="最多收藏" value="-star_count" />
          <el-option label="最多下载" value="-downloads" />
        </el-select>

        <!-- 搜索栏 -->
        <el-input
          v-model="searchKeyword"
          placeholder="请输入关键词搜索"
          class="search-input"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <i class="fa fa-search"></i>
          </template>
        </el-input>

        <!-- 版本筛选（仅人设卡显示） -->
        <el-input
          v-if="showVersionFilter"
          v-model="versionFilter"
          placeholder="版本号"
          style="width: 160px;"
          clearable
          @keyup.enter="handleVersionFilter"
          @clear="handleVersionFilter"
        >
          <template #prefix>
            <i class="fa fa-code-fork"></i>
          </template>
          <template #suffix>
            <el-tooltip 
              content="支持：精确版本 (1.2.3) | 主版本 (1.*) | 主次版本 (1.2.*)" 
              placement="bottom"
            >
              <i class="fa fa-question-circle" style="cursor: help; color: #909399;"></i>
            </el-tooltip>
          </template>
        </el-input>

        <!-- 搜索按钮 -->
        <el-button type="primary" @click="handleSearch">
          <i class="fa fa-search"></i> 搜索
        </el-button>

        <!-- 我的收藏按钮 -->
        <el-button 
          :type="showStarredOnly ? 'warning' : 'default'"
          @click="toggleStarredFilter"
        >
          <i class="fa fa-star"></i> 我的收藏
        </el-button>
      </div>

      <!-- 卡片列表 -->
      <div class="card-list" v-loading="loading">
        <div 
          v-for="item in dataList" 
          :key="item.id" 
          class="data-card"
          @click="$emit('show-detail', item)"
        >
          <div class="card-header">
            <div class="card-icon">
              <el-avatar 
                v-if="item.uploader_avatar" 
                :src="getBaseURL(item.uploader_avatar)" 
                :size="40"
              />
              <el-avatar v-else :size="40">
                {{ (item.uploader_name || '匿名')[0] }}
              </el-avatar>
            </div>
            <div class="card-title-area">
              <h4 class="card-title">{{ item.name }}</h4>
              <div class="card-meta">
                <span class="uploader">
                  <i class="fa fa-user"></i> {{ item.uploader_name || '匿名' }}
                </span>
                <span class="upload-time" v-if="item.create_datetime">
                  <i class="fa fa-clock-o"></i> {{ formatDate(item.create_datetime) }}
                </span>
              </div>
            </div>
            <div class="card-actions-top" @click.stop>
              <el-button 
                size="small"
                :type="item.is_starred ? 'warning' : 'default'"
                @click="$emit('toggle-star', item)"
              >
                <i class="fa" :class="item.is_starred ? 'fa-star' : 'fa-star-o'"></i>
                收藏
              </el-button>
            </div>
            <div class="card-badge" v-if="item.is_new">
              <span class="badge-new">New</span>
            </div>
          </div>

          <div class="card-description">
            {{ item.description || '暂无描述' }}
          </div>

          <div class="card-meta-row">
            <div class="card-version" v-if="showVersionFilter && item.version">
              <span class="version-badge">
                <i class="fa fa-code-fork"></i> v{{ item.version }}
              </span>
            </div>

            <div class="card-tags" v-if="parseTagsString(item.tags).length > 0">
              <span v-for="tag in parseTagsString(item.tags).slice(0, 3)" :key="tag" class="tag">
                {{ tag }}
              </span>
              <span v-if="parseTagsString(item.tags).length > 3" class="tag-more">
                +{{ parseTagsString(item.tags).length - 3 }}
              </span>
            </div>
          </div>

          <div class="card-footer">
            <div class="card-stats">
              <span class="stat-item">
                <i class="fa fa-download"></i> {{ item.downloads || 0 }}
              </span>
              <span class="stat-item">
                <i class="fa fa-star"></i> {{ item.star_count || 0 }}
              </span>
            </div>
            <div class="card-comments">
              <span class="stat-item">
                <i class="fa fa-comment"></i> {{ formatCount(item.comment_count) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="!loading && dataList.length === 0" class="empty-state">
          <i class="fa fa-inbox"></i>
          <p>{{ emptyText }}</p>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-container" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[12, 24, 48, 96]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 右侧悬浮卡片区域 -->
    <div class="sidebar-cards">
      <!-- 热门标签卡片 -->
      <div class="info-card tags-card">
        <div class="card-header-title">
          <i class="fa fa-tags"></i>
          <span>热门标签</span>
        </div>
        <div class="card-content">
          <div class="tags-wrapper">
            <el-tag
              v-for="tag in popularTags"
              :key="tag"
              :type="selectedTags.includes(tag) ? 'primary' : undefined"
              :effect="selectedTags.includes(tag) ? 'dark' : 'plain'"
              size="default"
              round
              class="tag-item"
              @click="toggleTag(tag)"
            >
              {{ tag }}
            </el-tag>
          </div>
          <div v-if="popularTags.length === 0" class="empty-tip">
            <i class="fa fa-inbox"></i>
            <p>暂无标签</p>
          </div>
        </div>
      </div>

      <!-- 热门推荐卡片 -->
      <div class="info-card hot-card">
        <div class="card-header-title">
          <i class="fa fa-fire"></i>
          <span>热门推荐</span>
        </div>
        <div class="card-content">
          <div 
            v-for="(item, index) in hotList.slice(0, 5)" 
            :key="item.id"
            class="mini-item"
            @click="$emit('show-detail', item)"
          >
            <div class="mini-rank">{{ index + 1 }}</div>
            <div class="mini-info">
              <div class="mini-name">{{ item.name }}</div>
              <div class="mini-stats">
                <span><i class="fa fa-download"></i> {{ item.downloads || 0 }}</span>
              </div>
            </div>
          </div>
          <div v-if="hotList.length === 0" class="empty-tip">
            <i class="fa fa-inbox"></i>
            <p>暂无数据</p>
          </div>
        </div>
      </div>

      <!-- 最新上传卡片 -->
      <div class="info-card new-card">
        <div class="card-header-title">
          <i class="fa fa-clock-o"></i>
          <span>最新上传</span>
        </div>
        <div class="card-content">
          <div 
            v-for="item in newList.slice(0, 5)" 
            :key="item.id"
            class="mini-item"
            @click="$emit('show-detail', item)"
          >
            <el-avatar :size="32" v-if="item.uploader_avatar" :src="getBaseURL(item.uploader_avatar)" />
            <el-avatar :size="32" v-else>{{ (item.uploader_name || '匿名')[0] }}</el-avatar>
            <div class="mini-info">
              <div class="mini-name">{{ item.name }}</div>
              <div class="mini-time">{{ formatDate(item.create_datetime) }}</div>
            </div>
          </div>
          <div v-if="newList.length === 0" class="empty-tip">
            <i class="fa fa-inbox"></i>
            <p>暂无数据</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue';
import { getBaseURL } from '/@/utils/baseUrl';

// Props
const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  },
  dataList: {
    type: Array,
    default: () => []
  },
  total: {
    type: Number,
    default: 0
  },
  popularTags: {
    type: Array,
    default: () => []
  },
  hotList: {
    type: Array,
    default: () => []
  },
  newList: {
    type: Array,
    default: () => []
  },
  showVersionFilter: {
    type: Boolean,
    default: false
  },
  emptyText: {
    type: String,
    default: '暂无数据'
  }
});

// Emits
const emit = defineEmits(['search', 'show-detail', 'toggle-star']);

// 状态管理
const orderBy = ref('hot');
const searchKeyword = ref('');
const selectedTags = ref<string[]>([]);
const versionFilter = ref('');
const showStarredOnly = ref(false);
const currentPage = ref(1);
const pageSize = ref(12);

// 排序变化
const handleOrderChange = () => {
  currentPage.value = 1;
  emitSearch();
};

// 切换收藏筛选
const toggleStarredFilter = () => {
  showStarredOnly.value = !showStarredOnly.value;
  currentPage.value = 1;
  emitSearch();
};

// 切换标签
const toggleTag = (tag: string) => {
  const index = selectedTags.value.indexOf(tag);
  if (index > -1) {
    selectedTags.value.splice(index, 1);
  } else {
    selectedTags.value.push(tag);
  }
  currentPage.value = 1;
  emitSearch();
};

// 版本号筛选
const handleVersionFilter = () => {
  currentPage.value = 1;
  emitSearch();
};

// 搜索
const handleSearch = () => {
  currentPage.value = 1;
  emitSearch();
};

// 分页
const handlePageChange = (page: number) => {
  currentPage.value = page;
  emitSearch();
};

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  emitSearch();
};

// 发送搜索事件
const emitSearch = () => {
  const params: any = {
    page: currentPage.value,
    page_size: pageSize.value,
    orderBy: orderBy.value,
    search: searchKeyword.value,
    tags: selectedTags.value,
    starred: showStarredOnly.value
  };

  if (props.showVersionFilter && versionFilter.value) {
    params.version = versionFilter.value.trim();
  }

  emit('search', params);
};

// 工具函数
const parseTagsString = (tagsData: string | string[]): string[] => {
  if (!tagsData) return [];
  // 如果已经是数组，直接返回
  if (Array.isArray(tagsData)) {
    return tagsData.filter((tag: string) => tag && tag.trim());
  }
  // 如果是字符串，按逗号分割（向后兼容）
  return tagsData.split(',').map((tag: string) => tag.trim()).filter((tag: string) => tag);
};

const formatDate = (dateString: string): string => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (days === 0) return '今天';
  if (days === 1) return '昨天';
  if (days < 7) return `${days}天前`;
  if (days < 30) return `${Math.floor(days / 7)}周前`;
  if (days < 365) return `${Math.floor(days / 30)}个月前`;
  return `${Math.floor(days / 365)}年前`;
};

const formatCount = (count: number | undefined): string => {
  if (!count) return '0';
  if (count > 999) return '999+';
  return count.toString();
};
</script>

<style scoped lang="scss">
.plaza-container {
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 84px);
  background: #f5f5f5;
  padding: 20px;

  // 左侧主内容区
  .main-content {
    flex: 1;
    min-width: 0;

    // 顶部工具栏
    .toolbar {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      align-items: center;
      background: white;
      padding: 16px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);

      .search-input {
        flex: 1;
        min-width: 200px;
      }
    }

    // 卡片列表
    .card-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
      min-height: 400px;

      .data-card {
        background: white;
        border-radius: 8px;
        padding: 16px;
        cursor: pointer;
        transition: all 0.3s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        height: 200px;

        &:hover {
          transform: translateY(-4px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .card-header {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 10px;
          position: relative;

          .card-icon {
            flex-shrink: 0;
          }

          .card-title-area {
            flex: 1;
            min-width: 0;

            .card-title {
              margin: 0 0 6px 0;
              font-size: 15px;
              font-weight: 600;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }

            .card-meta {
              font-size: 12px;
              color: #999;
              display: flex;
              gap: 12px;

              .uploader, .upload-time {
                display: flex;
                align-items: center;
                gap: 4px;
                
                i {
                  font-size: 11px;
                }
              }
            }
          }

          .card-actions-top {
            position: absolute;
            top: -4px;
            right: -4px;
            z-index: 2;

            .el-button {
              padding: 5px 12px;
              font-size: 12px;
              border-radius: 16px;
              box-shadow: 0 2px 8px rgba(0,0,0,0.15);
              
              &:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
              }

              i {
                margin-right: 4px;
              }
            }
          }

          .card-badge {
            position: absolute;
            top: 0;
            right: 40px;

            .badge-new {
              background: #ff4444;
              color: white;
              padding: 2px 8px;
              border-radius: 4px;
              font-size: 11px;
            }
          }
        }

        .card-description {
          font-size: 13px;
          color: #666;
          line-height: 1.5;
          margin-bottom: 10px;
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          flex: 1;
        }

        .card-meta-row {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 10px;
          min-height: 24px;
          flex-wrap: wrap;
        }

        .card-version {
          flex-shrink: 0;
          
          .version-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 10px;
            background: rgba(160, 82, 45, 0.1);
            color: #A0522D;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
            
            i {
              font-size: 10px;
            }
          }
        }

        .card-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          flex: 1;

          .tag {
            padding: 4px 12px;
            background: #f0f0f0;
            border-radius: 12px;
            font-size: 11px;
            color: #666;
          }
          
          .tag-more {
            padding: 4px 12px;
            background: #e0e0e0;
            border-radius: 12px;
            font-size: 11px;
            color: #999;
          }
        }

        .card-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 10px;
          border-top: 1px solid #f0f0f0;
          margin-top: auto;

          .card-stats {
            display: flex;
            gap: 15px;

            .stat-item {
              font-size: 12px;
              color: #999;
              display: flex;
              align-items: center;
              gap: 4px;

              i {
                font-size: 13px;
              }
            }
          }
          
          .card-comments {
            .stat-item {
              font-size: 12px;
              color: #999;
              display: flex;
              align-items: center;
              gap: 4px;

              i {
                font-size: 13px;
              }
            }
          }
        }
      }

      .empty-state {
        grid-column: 1 / -1;
        text-align: center;
        padding: 60px 20px;
        color: #999;

        i {
          font-size: 64px;
          margin-bottom: 20px;
          display: block;
        }

        p {
          font-size: 16px;
        }
      }
    }

    .pagination-container {
      margin-top: 30px;
      display: flex;
      justify-content: center;
    }
  }

  // 右侧悬浮卡片区域
  .sidebar-cards {
    width: 280px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
    position: sticky;
    top: 20px;
    align-self: flex-start;
    max-height: calc(100vh - 124px);
    overflow-y: auto;

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-thumb {
      background: #ddd;
      border-radius: 3px;

      &:hover {
        background: #bbb;
      }
    }

    .info-card {
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      overflow: hidden;
      transition: box-shadow 0.3s;

      &:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      }

      .card-header-title {
        padding: 16px;
        background: #A0522D;
        color: white;
        font-size: 14px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;

        i {
          font-size: 16px;
        }
      }

      .card-content {
        padding: 12px;

        .mini-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.3s;
          margin-bottom: 8px;

          &:last-child {
            margin-bottom: 0;
          }

          &:hover {
            background: #f5f5f5;
          }

          .mini-rank {
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #A0522D;
            color: white;
            border-radius: 50%;
            font-size: 12px;
            font-weight: 600;
            flex-shrink: 0;
          }

          .mini-info {
            flex: 1;
            min-width: 0;

            .mini-name {
              font-size: 13px;
              font-weight: 500;
              color: #333;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              margin-bottom: 4px;
            }

            .mini-stats {
              font-size: 11px;
              color: #999;
              display: flex;
              gap: 8px;

              span {
                display: flex;
                align-items: center;
                gap: 3px;
              }
            }

            .mini-time {
              font-size: 11px;
              color: #999;
            }
          }
        }

        .tags-wrapper {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;

          .tag-item {
            cursor: pointer;
            transition: all 0.3s;

            &:hover {
              transform: translateY(-2px);
            }

            // 未选中状态使用灰色
            &.el-tag--plain {
              background-color: #f4f4f5;
              border-color: #e9e9eb;
              color: #909399;
            }

            // 选中状态使用主题色
            &.el-tag--primary.el-tag--dark {
              background-color: #A0522D;
              border-color: #A0522D;
              color: white;
            }
          }
        }

        .empty-tip {
          text-align: center;
          padding: 20px;
          color: #999;

          i {
            font-size: 32px;
            margin-bottom: 8px;
            display: block;
          }

          p {
            font-size: 12px;
            margin: 0;
          }
        }
      }
    }
  }
}
</style>
