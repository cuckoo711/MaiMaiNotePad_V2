<template>
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    width="80%"
    destroy-on-close
    class="file-viewer-dialog"
  >
    <div class="file-viewer-body">
      <div class="file-viewer-meta">
        <span class="file-language-tag">{{ languageLabel }}</span>
      </div>
      
      <div v-if="loading" class="file-viewer-loading">
        <el-skeleton :rows="10" animated />
      </div>
      
      <template v-else>
        <el-tabs v-if="isTomlFile" v-model="activeTab" class="file-viewer-tabs">
          <el-tab-pane label="数据详情" name="detail">
            <div class="toml-visual-panel">
              <div class="toml-visual-header">
                <div class="toml-visual-title">TOML 配置文件</div>
                <div class="toml-visual-stats">
                  <div class="toml-stat-item">
                    <span class="toml-stat-label">配置块数量</span>
                    <span class="toml-stat-value">{{ tomlBlocks.length }}</span>
                  </div>
                  <div class="toml-stat-item">
                    <span class="toml-stat-label">配置项总数</span>
                    <span class="toml-stat-value">{{ totalKeys }}</span>
                  </div>
                </div>
              </div>
              
              <div class="toml-blocks-container">
                <el-collapse v-model="activeBlocks">
                  <el-collapse-item
                    v-for="block in tomlBlocks"
                    :key="block.index"
                    :name="block.index"
                  >
                    <template #title>
                      <div class="toml-block-title">
                        <span class="toml-block-name">{{ getBlockLabel(block.title) }}</span>
                        <el-tag size="small" type="info">{{ block.keyCount }} 项</el-tag>
                      </div>
                    </template>
                    
                    <div class="toml-block-content">
                      <div v-if="block.description" class="toml-block-description">
                        {{ block.description }}
                      </div>
                      
                      <div class="toml-kv-list">
                        <div
                          v-for="(item, idx) in block.keyValues"
                          :key="`${block.index}-${idx}`"
                          class="toml-kv-item"
                        >
                          <div class="toml-kv-key">
                            <div class="toml-kv-key-label">{{ item.key }}</div>
                            <div v-if="getKeyLabelOnly(item.key) !== item.key" class="toml-kv-key-value">
                              {{ getKeyLabelOnly(item.key) }}
                            </div>
                            <el-tooltip v-if="item.comment" :content="item.comment" placement="top">
                              <el-icon class="toml-kv-info-icon"><InfoFilled /></el-icon>
                            </el-tooltip>
                          </div>
                          <div class="toml-kv-value">
                            <!-- 布尔值 -->
                            <div v-if="getValueType(item.value, item.type) === 'boolean'" class="value-boolean">
                              <el-tag :type="item.value === true || item.value === 'true' ? 'success' : 'info'" size="default">
                                {{ item.value === true || item.value === 'true' ? '✓ 是' : '✗ 否' }}
                              </el-tag>
                            </div>
                            
                            <!-- 数字 -->
                            <div v-else-if="getValueType(item.value, item.type) === 'number'" class="value-number">
                              <span class="number-badge">{{ item.value }}</span>
                            </div>
                            
                            <!-- 空值 -->
                            <div v-else-if="getValueType(item.value, item.type) === 'empty'" class="value-empty">
                              <el-tag type="info" size="small" effect="plain">空</el-tag>
                            </div>
                            
                            <!-- 数组 -->
                            <div v-else-if="getValueType(item.value, item.type) === 'array'" class="value-array">
                              <!-- 简单数组：用表格显示（带行号） -->
                              <div v-if="isSimpleArray(item.value)" class="array-simple">
                                <el-table 
                                  :data="formatSimpleArrayForTable(item.value)" 
                                  size="small"
                                  :border="true"
                                  class="simple-array-table"
                                  :show-header="false"
                                >
                                  <el-table-column type="index" width="60" align="center" label="#" />
                                  <el-table-column prop="value" label="值">
                                    <template #default="scope">
                                      <div class="array-cell-value">{{ scope.row.value }}</div>
                                    </template>
                                  </el-table-column>
                                </el-table>
                              </div>
                              <!-- 复杂数组（包含对象）：用表格显示（带行号和表头） -->
                              <div v-else class="array-complex">
                                <el-table 
                                  :data="item.value" 
                                  size="small"
                                  :border="true"
                                  class="complex-table"
                                  :header-cell-style="{ background: '#fafafa', color: '#333', fontWeight: '600' }"
                                >
                                  <el-table-column type="index" width="60" align="center" label="#" />
                                  <el-table-column
                                    v-for="(colKey, colIdx) in getObjectKeys(item.value)"
                                    :key="colIdx"
                                    :prop="colKey"
                                    :label="getKeyLabelOnly(colKey) !== colKey ? getKeyLabelOnly(colKey) : colKey"
                                    min-width="120"
                                  >
                                    <template #default="scope">
                                      <div 
                                        class="table-cell-value"
                                        :class="{ 'long-text': isLongText(scope.row[colKey]) }"
                                      >
                                        {{ formatCellValue(scope.row[colKey]) }}
                                      </div>
                                    </template>
                                  </el-table-column>
                                </el-table>
                              </div>
                            </div>
                            
                            <!-- 对象/字典 -->
                            <div v-else-if="getValueType(item.value, item.type) === 'object'" class="value-object">
                              <div class="object-preview">{{ formatObjectValue(item.value) }}</div>
                            </div>
                            
                            <!-- 多行文本 -->
                            <div v-else-if="getValueType(item.value, item.type) === 'multiline'" class="value-multiline">
                              <div class="multiline-preview">{{ cleanMultilineValue(item.value) }}</div>
                            </div>
                            
                            <!-- 普通字符串 -->
                            <el-input
                              v-else
                              :model-value="cleanStringValue(item.value)"
                              type="textarea"
                              :autosize="{ minRows: 1, maxRows: 10 }"
                              readonly
                              class="text-area"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="源代码" name="source">
            <div class="file-viewer-content">
              <el-input
                v-model="fileContent"
                type="textarea"
                :rows="20"
                readonly
                class="file-content-textarea"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
        
        <div v-else class="file-viewer-content">
          <el-input
            v-model="fileContent"
            type="textarea"
            :rows="20"
            readonly
            class="file-content-textarea"
          />
        </div>
      </template>
    </div>
    
    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
      <el-button type="primary" @click="handleDownload">
        <el-icon><Download /></el-icon>
        下载文件
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue';
import { Download, InfoFilled } from '@element-plus/icons-vue';
import { useTranslationStore } from '/@/stores/translation';

const translationStore = useTranslationStore();

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
  personaId: {
    type: String,
    default: ''
  },
  fileId: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:visible', 'download']);

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => {
    emit('update:visible', value);
  }
});

const dialogTitle = computed(() => {
  if (props.title) {
    return props.title;
  }
  if (props.fileName) {
    return `预览 - ${props.fileName}`;
  }
  return '文件预览';
});

const fileContent = ref('');
const tomlData = ref<any>(null);
const loading = ref(false);

const activeTab = ref('detail');
const activeBlocks = ref<number[]>([]);

// 翻译数据
let blockTranslations = new Map<string, string>();
let tokenTranslations = new Map<string, string>();

// 组件挂载时加载翻译数据
onMounted(async () => {
  try {
    // 加载块翻译
    blockTranslations = await translationStore.getTranslationsByType(
      'toml_visualizer_blocks'
    );
    
    // 加载 Token 翻译
    tokenTranslations = await translationStore.getTranslationsByType(
      'toml_visualizer_tokens'
    );
  } catch (error) {
    console.error('加载翻译数据失败:', error);
    // 降级方案：使用原始英文文本
  }
});

// 监听对话框打开，加载文件内容
watch(() => props.visible, async (newVal) => {
  if (newVal && props.personaId && props.fileId) {
    await loadFileContent();
  }
}, { immediate: true });

// 加载文件内容
const loadFileContent = async () => {
  if (!props.personaId || !props.fileId) return;
  
  loading.value = true;
  try {
    if (isTomlFile.value) {
      // TOML 文件使用解析 API
      const { parsePersonaToml } = await import('/@/views/content/persona/api');
      const response = await parsePersonaToml(props.personaId, props.fileId);
      
      if (response.data) {
        fileContent.value = response.data.raw_content || '';
        tomlData.value = response.data.blocks || [];
        
        // 默认展开第一个块
        if (tomlData.value.length > 0) {
          activeBlocks.value = [0];
        }
      }
    } else {
      // 其他文件直接获取文本内容
      const { previewPersonaFile } = await import('/@/views/content/persona/api');
      const blob = await previewPersonaFile(props.personaId, props.fileId);
      fileContent.value = await blob.text();
    }
  } catch (error) {
    console.error('加载文件失败:', error);
    ElMessage.error('加载文件失败');
  } finally {
    loading.value = false;
  }
};

// 判断文件类型
const isTomlFile = computed(() => {
  const fileName = props.fileName || '';
  return fileName.toLowerCase().endsWith('.toml');
});

const languageLabel = computed(() => {
  const fileName = props.fileName || '';
  const lower = fileName.toLowerCase();
  if (lower.endsWith('.toml')) return 'TOML';
  if (lower.endsWith('.json')) return 'JSON';
  if (lower.endsWith('.txt')) return 'TEXT';
  return 'TEXT';
});

// 解析 TOML 内容（使用后端返回的数据）
const tomlBlocks = computed(() => {
  if (!isTomlFile.value || !tomlData.value) {
    return [];
  }
  
  return tomlData.value.map((block: any, index: number) => ({
    index,
    title: block.title || '根配置',
    description: '',
    keyCount: block.key_values?.length || 0,
    keyValues: (block.key_values || []).map((kv: any) => ({
      key: kv.key,
      value: kv.value,
      type: kv.type,
      comment: ''
    }))
  }));
});

// 计算总配置项数
const totalKeys = computed(() => {
  return tomlBlocks.value.reduce((sum, block) => sum + block.keyCount, 0);
});

// 判断是否是多行值
const isMultiLineValue = (value: string) => {
  return value.includes('\n') || value.length > 100;
};

// 获取显示值
const getDisplayValue = (value: string) => {
  return value;
};

// 判断值的类型（使用后端返回的类型或前端判断）
const getValueType = (value: any, backendType?: string) => {
  // 优先使用后端返回的类型
  if (backendType) {
    switch (backendType) {
      case 'boolean':
        return 'boolean';
      case 'integer':
      case 'float':
        return 'number';
      case 'array':
        return 'array';
      case 'table':
        return 'object';
      case 'multiline_string':
        return 'multiline';
      case 'string':
        return 'string';
      default:
        break;
    }
  }
  
  // 如果值是原始类型（后端已解析）
  if (typeof value === 'boolean') {
    return 'boolean';
  }
  if (typeof value === 'number') {
    return 'number';
  }
  if (Array.isArray(value)) {
    return 'array';
  }
  if (typeof value === 'object' && value !== null) {
    return 'object';
  }
  
  // 字符串类型的判断
  const strValue = String(value);
  const trimmed = strValue.trim();
  
  // 空值
  if (trimmed === '' || trimmed === '[]' || trimmed === '{}') {
    return 'empty';
  }
  
  // 多行字符串
  if (strValue.includes('\n')) {
    return 'multiline';
  }
  
  return 'text';
};

// 格式化简单数组为表格数据
const formatSimpleArrayForTable = (arr: any[]) => {
  if (!Array.isArray(arr)) {
    return [];
  }
  
  return arr.map(item => ({
    value: String(item)
  }));
};

// 获取对象数组的所有键名
const getObjectKeys = (arr: any[]) => {
  if (!Array.isArray(arr) || arr.length === 0) {
    return [];
  }
  
  // 获取第一个对象的键
  const firstItem = arr[0];
  if (typeof firstItem === 'object' && firstItem !== null) {
    return Object.keys(firstItem);
  }
  
  return [];
};

// 格式化表格单元格的值
const formatCellValue = (value: any) => {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'boolean') {
    return value ? '✓' : '✗';
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch (e) {
      return String(value);
    }
  }
  return String(value);
};

// 判断单元格值是否需要多行显示
const isLongText = (value: any) => {
  const str = String(value);
  return str.length > 20;
};

// 判断是否是简单数组（不包含对象或数组）
const isSimpleArray = (value: any) => {
  if (!Array.isArray(value)) {
    return true; // 不是数组，按简单处理
  }
  
  // 检查数组中是否有对象或数组
  return !value.some(item => 
    typeof item === 'object' && item !== null
  );
};

// 格式化对象显示（处理后端返回的对象或字典）
const formatObjectValue = (value: any) => {
  if (typeof value === 'object' && value !== null) {
    try {
      return JSON.stringify(value, null, 2);
    } catch (e) {
      return String(value);
    }
  }
  return String(value);
};

// 清理多行字符串值
const cleanMultilineValue = (value: any) => {
  const strValue = String(value);
  return strValue.trim();
};

// 清理普通字符串值
const cleanStringValue = (value: any) => {
  return String(value);
};

// 获取键名的翻译（带原文）
const getKeyLabel = (key: string) => {
  try {
    const translation = tokenTranslations.get(key);
    if (translation) {
      return `${translation} (${key})`;
    }
  } catch (e) {
    console.error('翻译查找错误:', e);
  }
  return key;
};

// 只获取键名的中文标签（不带英文键名）
const getKeyLabelOnly = (key: string) => {
  try {
    const translation = tokenTranslations.get(key);
    if (translation) {
      return translation;
    }
  } catch (e) {
    console.error('翻译查找错误:', e);
  }
  return key;
};

// 获取块名的翻译
const getBlockLabel = (blockName: string) => {
  try {
    const translation = blockTranslations.get(blockName);
    if (translation) {
      return `${translation} (${blockName})`;
    }
  } catch (e) {
    console.error('块名翻译错误:', e);
  }
  return blockName;
};

const handleDownload = () => {
  emit('download');
};

// 监听内容变化，默认展开第一个块
watch(() => props.content, () => {
  if (tomlBlocks.value.length > 0) {
    activeBlocks.value = [tomlBlocks.value[0].index];
  }
}, { immediate: true });
</script>

<script lang="ts">
export default {
  name: 'FileViewerDialog'
};
</script>

<style scoped lang="scss">
.file-viewer-dialog {
  :deep(.el-dialog__body) {
    padding: 20px;
  }
}

.file-viewer-body {
  min-height: 400px;
}

.file-viewer-meta {
  margin-bottom: 16px;
  
  .file-language-tag {
    display: inline-block;
    padding: 4px 12px;
    background: #a0522d;
    color: white;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }
}

.file-viewer-loading {
  padding: 20px;
}

.file-viewer-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 20px;
  }
  
  :deep(.el-tabs__item) {
    font-size: 15px;
    font-weight: 500;
    
    &.is-active {
      color: #a0522d;
    }
  }
  
  :deep(.el-tabs__active-bar) {
    background-color: #a0522d;
  }
}

.file-viewer-content {
  .file-content-textarea {
    :deep(textarea) {
      font-family: 'Courier New', Courier, monospace;
      font-size: 13px;
      line-height: 1.6;
      background: #f8f9fa;
    }
  }
}

// TOML 可视化面板
.toml-visual-panel {
  .toml-visual-header {
    padding: 16px;
    background: linear-gradient(135deg, #d4a574 0%, #a0522d 100%);
    color: white;
    border-radius: 8px 8px 0 0;
    margin-bottom: 20px;
    
    .toml-visual-title {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 12px;
    }
    
    .toml-visual-stats {
      display: flex;
      gap: 24px;
      
      .toml-stat-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
        
        .toml-stat-label {
          font-size: 12px;
          opacity: 0.9;
        }
        
        .toml-stat-value {
          font-size: 20px;
          font-weight: 600;
        }
      }
    }
  }
}

.toml-blocks-container {
  :deep(.el-collapse) {
    border: none;
  }
  
  :deep(.el-collapse-item) {
    margin-bottom: 8px;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    overflow: hidden;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
  
  :deep(.el-collapse-item__header) {
    background: #f8f9fa;
    padding: 8px 16px;
    height: 40px;
    line-height: 40px;
    border: none;
    font-weight: 500;
    
    &:hover {
      background: #f0f0f0;
    }
    
    &.is-active {
      background: #fff5f0;
      color: #a0522d;
    }
  }
  
  :deep(.el-collapse-item__wrap) {
    border: none;
  }
  
  :deep(.el-collapse-item__content) {
    padding: 0;
  }
}

.toml-block-title {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  
  .toml-block-name {
    flex: 1;
    font-size: 14px;
    font-weight: 600;
  }
  
  .el-tag {
    background: rgba(160, 82, 45, 0.1);
    color: #a0522d;
    border-color: transparent;
    height: 22px;
    line-height: 22px;
    padding: 0 8px;
  }
}

.toml-block-content {
  padding: 16px;
  background: white;
  
  .toml-block-description {
    padding: 12px;
    background: #f8f9fa;
    border-left: 3px solid #a0522d;
    border-radius: 4px;
    margin-bottom: 16px;
    font-size: 14px;
    color: #666;
  }
}

.toml-kv-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toml-kv-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #f0f0f0;
  
  &:hover {
    background: #f5f5f5;
    border-color: #e0e0e0;
  }
  
  .toml-kv-key {
    min-width: 280px;
    max-width: 320px;
    padding-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex-shrink: 0;
    
    .toml-kv-key-label {
      font-weight: 600;
      color: #333;
      font-size: 14px;
      font-family: 'Courier New', Courier, monospace;
    }
    
    .toml-kv-key-value {
      font-size: 11px;
      color: #999;
    }
    
    .toml-kv-info-icon {
      color: #999;
      cursor: help;
      margin-top: 4px;
      
      &:hover {
        color: #a0522d;
      }
    }
  }
  
  .toml-kv-value {
    flex: 1;
    
    :deep(.el-input__inner),
    :deep(.el-textarea__inner) {
      background: white;
      border-color: #e0e0e0;
      font-family: 'Courier New', Courier, monospace;
      font-size: 13px;
      line-height: 1.6;
    }
    
    :deep(.el-textarea__inner) {
      padding: 8px 12px;
    }
    
    .text-area {
      :deep(.el-textarea__inner) {
        resize: none;
        overflow-y: hidden;
      }
    }
    
    .value-boolean,
    .value-number,
    .value-empty {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      min-height: 32px;
    }
    
    .number-badge {
      display: inline-block;
      padding: 6px 14px;
      background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
      color: #0369a1;
      border: 1px solid #bae6fd;
      border-radius: 6px;
      font-family: 'Courier New', Courier, monospace;
      font-size: 14px;
      font-weight: 600;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
    
    .value-array {
      flex: 1;
      
      .array-simple {
        .simple-array-table {
          width: 100%;
          border-radius: 6px;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
          
          :deep(.el-table__body) {
            td {
              font-size: 13px;
              padding: 8px 0;
            }
            
            // 行号列样式
            .el-table-column--selection {
              background: #fafafa;
              font-weight: 600;
              color: #999;
            }
          }
          
          .array-cell-value {
            font-family: 'Courier New', Courier, monospace;
            color: #333;
            padding: 4px 8px;
            word-break: break-word;
          }
        }
      }
      
      .array-complex {
        flex: 1;
        
        .complex-table {
          width: 100%;
          border-radius: 6px;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
          
          :deep(.el-table__header) {
            th {
              font-size: 13px;
              padding: 10px 0;
            }
          }
          
          :deep(.el-table__body) {
            td {
              font-size: 13px;
              padding: 8px 0;
            }
          }
          
          .table-cell-value {
            font-family: 'Courier New', Courier, monospace;
            color: #333;
            padding: 4px 8px;
            
            &.long-text {
              white-space: pre-wrap;
              word-break: break-word;
              line-height: 1.6;
              max-width: 400px;
            }
          }
        }
      }
    }
    
    .value-object {
      .object-preview {
        padding: 12px;
        background: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 13px;
        line-height: 1.8;
        color: #333;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 300px;
        overflow-y: auto;
      }
    }
    
    .value-multiline {
      .multiline-preview {
        padding: 12px;
        background: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 13px;
        line-height: 1.8;
        color: #333;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 200px;
        overflow-y: auto;
      }
    }
  }
}
</style>
