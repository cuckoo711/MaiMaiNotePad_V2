<template>
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    width="800px"
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
        <el-tabs
          v-if="hasVisualPanel"
          v-model="activeTab"
          class="file-viewer-tabs"
        >
          <el-tab-pane label="数据详情" name="detail">
            <div class="tab-fixed-content">
              <div
                v-if="isKnowledgeJson"
                class="json-visual-panel"
              >
                <div class="json-visual-header">
                  <div class="json-visual-title">
                    JSON 结构识别为知识文档，已生成概览
                  </div>
                  <div class="json-visual-stats">
                    <div class="json-stat-item">
                      <span class="json-stat-label">文档数</span>
                      <span class="json-stat-value">{{ jsonDocsCount }}</span>
                    </div>
                    <div class="json-stat-item">
                      <span class="json-stat-label">平均实体字数</span>
                      <span class="json-stat-value">{{ jsonAvgEntChars }}</span>
                    </div>
                    <div class="json-stat-item">
                      <span class="json-stat-label">平均实体词数</span>
                      <span class="json-stat-value">{{ jsonAvgEntWords }}</span>
                    </div>
                    <div class="json-stat-item">
                      <span class="json-stat-label">总实体数</span>
                      <span class="json-stat-value">{{ jsonTotalEntities }}</span>
                    </div>
                    <div class="json-stat-item">
                      <span class="json-stat-label">总三元组数</span>
                      <span class="json-stat-value">{{ jsonTotalTriples }}</span>
                    </div>
                    <div class="json-filter-wrapper">
                      <el-input
                        v-model="docsFilterKeyword"
                        size="small"
                        class="json-filter-input"
                        placeholder="输入关键字搜索"
                        clearable
                      />
                    </div>
                  </div>
                </div>
                <div class="json-table-wrapper">
                  <el-auto-resizer>
                    <template #default="{ height, width }">
                      <el-table-v2
                        :columns="jsonVirtualColumns"
                        :data="filteredJsonDocsPreview"
                        :width="width"
                        :height="height"
                        row-key="index"
                        :row-height="jsonRowHeight"
                        fixed
                        @scroll="handleJsonTableScroll"
                      />
                    </template>
                  </el-auto-resizer>
                </div>
              </div>
              <div
                v-else-if="isTomlVisual"
                class="json-visual-panel"
              >
                <div class="json-visual-header">
                  <div class="json-visual-title">
                    TOML 结构识别为分块配置，已生成概览
                  </div>
                  <div class="json-visual-stats">
                    <div class="json-stat-item">
                      <span class="json-stat-label">块数量</span>
                      <span class="json-stat-value">{{ tomlBlockCount }}</span>
                    </div>
                    <div class="json-stat-item">
                      <span class="json-stat-label">键总数</span>
                      <span class="json-stat-value">{{ tomlTotalKeys }}</span>
                    </div>
                    <div class="json-filter-wrapper">
                      <el-input
                        v-model="docsFilterKeyword"
                        size="small"
                        class="json-filter-input"
                        placeholder="输入关键字搜索"
                        clearable
                      />
                    </div>
                  </div>
                </div>
                <div class="toml-vertical-container">
                  <el-tabs
                    v-model="activeTomlTab"
                    tab-position="left"
                    class="toml-vertical-tabs"
                  >
                    <el-tab-pane
                      v-for="block in filteredTomlBlocks"
                      :key="block.index"
                      :name="String(block.index)"
                    >
                      <template #label>
                        <div class="toml-tab-label">
                          <div class="toml-tab-label-main">
                            {{ getTomlBlockDisplayTitle(block) }}
                          </div>
                          <div
                            v-if="getTomlBlockTranslation(block)"
                            class="toml-tab-label-sub"
                          >
                            {{ getTomlBlockTranslation(block) }}
                          </div>
                        </div>
                      </template>
                      <div class="toml-block-card-container">
                        <div class="toml-block-card">
                          <div class="toml-block-meta">
                            <div class="toml-block-title">
                              <div class="toml-block-title-main">
                                {{ getTomlBlockDisplayTitle(block) }}
                              </div>
                              <div
                                v-if="getTomlBlockTranslation(block)"
                                class="toml-block-title-sub"
                              >
                                {{ getTomlBlockTranslation(block) }}
                              </div>
                            </div>
                            <div
                              v-if="block.description"
                              class="toml-block-description"
                            >
                              {{ block.description }}
                            </div>
                            <div class="toml-block-extra">
                              <span>键数量：{{ block.keyCount }}</span>
                              <span class="toml-block-line-range">行范围：{{ block.lineRange }}</span>
                            </div>
                          </div>
                          <div class="toml-kv-list">
                            <div
                              v-for="item in block.keyValues"
                              :key="`${block.index}-${item.key}-${item.lineNumber || 0}`"
                              class="toml-kv-card"
                            >
                              <div class="toml-kv-key">
                                <span class="toml-kv-key-text">
                                  {{ item.key }}
                                </span>
                                <el-tooltip
                                  v-if="item.comment"
                                  :content="item.comment"
                                  placement="top"
                                >
                                  <el-icon class="toml-kv-info-icon">
                                    <InfoFilled />
                                  </el-icon>
                                </el-tooltip>
                              </div>
                              <div class="toml-kv-value">
                                <template
                                  v-if="block.title === 'expression' && item.key === 'learning_list' && parseLearningList(item.value).length"
                                >
                                  <div class="toml-learning-list">
                                    <div
                                      v-for="(rule, idx) in parseLearningList(item.value)"
                                      :key="`${block.index}-${item.key}-learning-${idx}`"
                                      class="toml-learning-item"
                                    >
                                      <div class="toml-learning-row">
                                        <el-tag size="small" effect="plain">
                                          {{ rule.scopeLabel }}
                                        </el-tag>
                                        <el-tag
                                          size="small"
                                          :type="rule.useExpr === 'enable' ? 'success' : 'info'"
                                        >
                                          使用表达: {{ rule.useExpr }}
                                        </el-tag>
                                        <el-tag
                                          size="small"
                                          :type="rule.learnExpr === 'enable' ? 'success' : 'info'"
                                        >
                                          学习表达: {{ rule.learnExpr }}
                                        </el-tag>
                                        <el-tag
                                          size="small"
                                          :type="rule.learnJargon === 'enable' ? 'success' : 'info'"
                                        >
                                          jargon: {{ rule.learnJargon }}
                                        </el-tag>
                                      </div>
                                    </div>
                                  </div>
                                </template>
                                <template
                                  v-else-if="block.title === 'keyword_reaction' && item.key === 'keyword_rules' && parseKeywordRules(item.value).length"
                                >
                                  <div class="toml-keyword-rules">
                                    <div
                                      v-for="(rule, idx) in parseKeywordRules(item.value)"
                                      :key="`${block.index}-${item.key}-kw-${idx}`"
                                      class="toml-keyword-rule"
                                    >
                                      <div class="toml-keyword-tags">
                                        <el-tag
                                          v-for="kw in rule.keywords"
                                          :key="kw"
                                          size="small"
                                          effect="plain"
                                          class="toml-keyword-tag"
                                        >
                                          {{ kw }}
                                        </el-tag>
                                      </div>
                                      <div
                                        v-if="rule.reaction"
                                        class="toml-keyword-reaction"
                                      >
                                        {{ rule.reaction }}
                                      </div>
                                    </div>
                                  </div>
                                </template>
                                <template
                                  v-else-if="block.title === 'keyword_reaction' && item.key === 'regex_rules' && parseRegexRules(item.value).length"
                                >
                                  <div class="toml-regex-rules">
                                    <div
                                      v-for="(rule, idx) in parseRegexRules(item.value)"
                                      :key="`${block.index}-${item.key}-regex-${idx}`"
                                      class="toml-regex-rule"
                                    >
                                      <div class="toml-regex-patterns">
                                        <el-tag
                                          v-for="pattern in rule.patterns"
                                          :key="pattern"
                                          size="small"
                                          effect="plain"
                                          class="toml-regex-tag"
                                        >
                                          {{ pattern }}
                                        </el-tag>
                                      </div>
                                      <div
                                        v-if="rule.reaction"
                                        class="toml-keyword-reaction"
                                      >
                                        {{ rule.reaction }}
                                      </div>
                                    </div>
                                  </div>
                                </template>
                                <template
                                  v-else-if="block.title === 'experimental' && item.key === 'chat_prompts' && parseChatPrompts(item.value).length"
                                >
                                  <div class="toml-chat-prompts">
                                    <div
                                      v-for="(prompt, idx) in parseChatPrompts(item.value)"
                                      :key="`${block.index}-${item.key}-chat-${idx}`"
                                      class="toml-chat-prompt"
                                    >
                                      <div
                                        v-if="prompt.scope"
                                        class="toml-chat-scope"
                                      >
                                        <el-tag
                                          size="small"
                                          effect="plain"
                                          class="toml-chat-scope-tag"
                                        >
                                          {{ prompt.scope }}
                                        </el-tag>
                                      </div>
                                      <div class="toml-chat-content">
                                        {{ prompt.content }}
                                      </div>
                                    </div>
                                  </div>
                                </template>
                                <template v-else>
                                  <div
                                    v-if="isBooleanValue(item.value)"
                                    class="toml-boolean-tag"
                                  >
                                    <el-tag
                                      :type="getBooleanTagType(item.value)"
                                      size="small"
                                      effect="plain"
                                    >
                                      {{ getBooleanLabel(item.value) }}
                                    </el-tag>
                                  </div>
                                  <div
                                    v-else-if="isListValue(item.value)"
                                    class="toml-array-tags"
                                  >
                                    <el-tag
                                      v-for="(entry, idx) in getListEntries(item.value)"
                                      :key="`${block.index}-${item.key}-${idx}`"
                                      size="small"
                                      effect="plain"
                                      class="toml-array-tag"
                                    >
                                      {{ entry }}
                                    </el-tag>
                                  </div>
                                  <el-input
                                    v-else-if="!isMultiLineValue(item.value)"
                                    :model-value="getDisplayValue(item.value)"
                                    size="small"
                                    readonly
                                    class="toml-kv-input"
                                  />
                                  <el-input
                                    v-else
                                    :model-value="getDisplayValue(item.value)"
                                    size="small"
                                    type="textarea"
                                    readonly
                                    class="toml-kv-textarea"
                                    :autosize="{ minRows: 2, maxRows: 6 }"
                                  />
                                </template>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </el-tab-pane>
                  </el-tabs>
                </div>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="源代码" name="source">
            <div class="file-viewer-content">
              <div ref="editorContainer" class="monaco-editor-container"></div>
            </div>
          </el-tab-pane>
        </el-tabs>
        <div v-else class="file-viewer-content">
          <div ref="editorContainer" class="monaco-editor-container"></div>
        </div>
      </template>
    </div>
    <template #footer>
      <el-button type="primary" @click="handleDownload">
        <el-icon>
          <Download />
        </el-icon>
        下载文件
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount, nextTick, h } from 'vue'
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'
import 'monaco-editor/min/vs/editor/editor.main.css'
import 'monaco-editor/esm/vs/editor/contrib/folding/browser/folding'
import { Download, InfoFilled } from '@element-plus/icons-vue'
import { ElTag, ElPopover, ElTableV2, ElAutoResizer } from 'element-plus'
import { getTranslationDictionary } from '../api/dictionary'

let jsonFoldingProviderRegistered = false

const ensureJsonFolding = () => {
  if (jsonFoldingProviderRegistered) {
    return
  }
  jsonFoldingProviderRegistered = true
  try {
    monaco.languages.register({ id: 'json' })
  } catch (e) {}
  monaco.languages.registerFoldingRangeProvider('json', {
    provideFoldingRanges(model) {
      const ranges = []
      const stack = []
      const lineCount = model.getLineCount()
      for (let lineNumber = 1; lineNumber <= lineCount; lineNumber += 1) {
        const text = model.getLineContent(lineNumber)
        for (let i = 0; i < text.length; i += 1) {
          const ch = text[i]
          if (ch === '{' || ch === '[') {
            stack.push({ start: lineNumber })
          } else if (ch === '}' || ch === ']') {
            if (stack.length) {
              const last = stack.pop()
              if (lineNumber > last.start) {
                ranges.push({
                  start: last.start,
                  end: lineNumber,
                  kind: monaco.languages.FoldingRangeKind.Region
                })
              }
            }
          }
        }
      }
      return ranges
    }
  })
}

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
  language: {
    type: String,
    default: ''
  },
  content: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'download'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => {
    emit('update:visible', value)
  }
})

const dialogTitle = computed(() => {
  if (props.title) {
    return props.title
  }
  if (props.fileName) {
    return `预览 - ${props.fileName}`
  }
  return '文件预览'
})

const resolvedLanguage = computed(() => {
  if (props.language) {
    return props.language
  }
  const name = props.fileName || ''
  const index = name.lastIndexOf('.')
  if (index !== -1) {
    const ext = name.slice(index + 1).toLowerCase()
    if (ext === 'json' || ext === 'toml' || ext === 'txt') {
      return ext
    }
  }
  return 'txt'
})

const languageLabel = computed(() => {
  const lang = resolvedLanguage.value
  if (lang === 'json') {
    return 'JSON'
  }
  if (lang === 'toml') {
    return 'TOML'
  }
  return 'TEXT'
})

const wrapEnabled = ref(true)
const editorContainer = ref(null)
let editorInstance = null
const activeTab = ref('source')
const docsFilterKeyword = ref('')
const activeTomlTab = ref('')

const parsedJson = computed(() => {
  const value = props.content || ''
  if (!value) {
    return null
  }
  try {
    return JSON.parse(value)
  } catch (error) {
    return null
  }
})

const isKnowledgeJson = computed(() => {
  if (!parsedJson.value || typeof parsedJson.value !== 'object') {
    return false
  }
  const data = parsedJson.value
  if (!Array.isArray(data.docs)) {
    return false
  }
  if (typeof data.avg_ent_chars !== 'number') {
    return false
  }
  if (typeof data.avg_ent_words !== 'number') {
    return false
  }
  for (let i = 0; i < data.docs.length; i += 1) {
    const doc = data.docs[i]
    if (!doc || typeof doc !== 'object') {
      return false
    }
    if (typeof doc.idx !== 'string') {
      return false
    }
    if (typeof doc.passage !== 'string') {
      return false
    }
    if (!Array.isArray(doc.extracted_entities)) {
      return false
    }
    for (let j = 0; j < doc.extracted_entities.length; j += 1) {
      if (typeof doc.extracted_entities[j] !== 'string') {
        return false
      }
    }
    if (!Array.isArray(doc.extracted_triples)) {
      return false
    }
    for (let k = 0; k < doc.extracted_triples.length; k += 1) {
      const triple = doc.extracted_triples[k]
      if (!Array.isArray(triple) || triple.length !== 3) {
        return false
      }
      if (typeof triple[0] !== 'string' || typeof triple[1] !== 'string' || typeof triple[2] !== 'string') {
        return false
      }
    }
  }
  return true
})

const tomlBlocks = computed(() => {
  if (resolvedLanguage.value !== 'toml') {
    return []
  }
  const text = props.content || ''
  if (!text) {
    return []
  }
  const lines = text.split(/\r?\n/)
  const blocks = []
  let pendingComments = []
  let current = null
  const totalLines = lines.length
  for (let i = 0; i < totalLines; i += 1) {
    const rawLine = lines[i]
    const lineNumber = i + 1
    const trimmed = rawLine.trim()
    if (!trimmed) {
      pendingComments = []
      continue
    }
    if (trimmed.startsWith('#')) {
      const commentText = trimmed.slice(1).trim()
      if (commentText) {
        pendingComments.push(commentText)
      }
      continue
    }
    let headerText = trimmed
    const commentIndex = headerText.indexOf('#')
    if (commentIndex !== -1) {
      headerText = headerText.slice(0, commentIndex).trim()
    }
    const headerMatch = headerText.match(/^\[([A-Za-z0-9_.-]+)]$/)
    if (headerMatch) {
      if (current) {
        current.endLine = lineNumber - 1
        current.lineRange = `${current.startLine}-${current.endLine}`
        blocks.push(current)
      }
      const title = headerMatch[1]
      current = {
        index: blocks.length + 1,
        title,
        description: pendingComments.join(' '),
        keyCount: 0,
        startLine: lineNumber,
        endLine: lineNumber,
        lineRange: `${lineNumber}-${lineNumber}`,
        keyValues: []
      }
      pendingComments = []
      continue
    }
    if (!current) {
      pendingComments = []
      continue
    }
    const keyMatch = trimmed.match(/^([A-Za-z0-9_.-]+)\s*=\s*(.*)$/)
    if (keyMatch) {
      current.keyCount += 1
      let valueText = keyMatch[2] || ''
      let inlineComment = ''
      const inlineIndex = valueText.indexOf('#')
      if (inlineIndex !== -1) {
        inlineComment = valueText.slice(inlineIndex + 1).trim()
        valueText = valueText.slice(0, inlineIndex).trim()
      }

      let fullValue = valueText
      const followingLines = []

      if (valueText.startsWith('[') && !valueText.includes(']')) {
        let foundEnd = false
        for (let j = i + 1; j < totalLines; j += 1) {
          const arrRaw = lines[j]
          const arrTrim = arrRaw.trim()
          followingLines.push(arrTrim)
          if (arrTrim.includes(']')) {
            i = j
            foundEnd = true
            break
          }
        }
        fullValue = [valueText, ...followingLines].join('\n')
      } else if (
        (valueText.startsWith('"""') && !valueText.endsWith('"""')) ||
        (valueText.startsWith("'''") && !valueText.endsWith("'''"))
      ) {
        const triple = valueText.startsWith('"""') ? '"""' : "'''"
        let foundEnd = valueText.endsWith(triple)
        for (let j = i + 1; j < totalLines && !foundEnd; j += 1) {
          const strRaw = lines[j]
          const strTrim = strRaw
          followingLines.push(strTrim)
          if (strTrim.trim().endsWith(triple)) {
            i = j
            foundEnd = true
            break
          }
        }
        fullValue = [valueText, ...followingLines].join('\n')
      }

      current.keyValues.push({
        key: keyMatch[1],
        value: fullValue,
        comment: inlineComment,
        lineNumber
      })
    }
  }
  if (current) {
    current.endLine = totalLines
    current.lineRange = `${current.startLine}-${current.endLine}`
    blocks.push(current)
  }
  return blocks
})

const isTomlVisual = computed(() => {
  if (resolvedLanguage.value !== 'toml') {
    return false
  }
  if (tomlBlocks.value.length > 0) {
    ensureTranslationDictLoaded()
    return true
  }
  return false
})

const tomlBlockCount = computed(() => {
  if (!isTomlVisual.value) {
    return 0
  }
  return tomlBlocks.value.length
})

const tomlTotalKeys = computed(() => {
  if (!isTomlVisual.value) {
    return 0
  }
  let total = 0
  const blocks = tomlBlocks.value
  for (let i = 0; i < blocks.length; i += 1) {
    total += blocks[i].keyCount || 0
  }
  return total
})

const jsonDocsCount = computed(() => {
  if (!isKnowledgeJson.value) {
    return 0
  }
  return Array.isArray(parsedJson.value.docs) ? parsedJson.value.docs.length : 0
})

const jsonAvgEntChars = computed(() => {
  if (!isKnowledgeJson.value) {
    return 0
  }
  return parsedJson.value.avg_ent_chars
})

const jsonAvgEntWords = computed(() => {
  if (!isKnowledgeJson.value) {
    return 0
  }
  return parsedJson.value.avg_ent_words
})

const jsonTotalEntities = computed(() => {
  if (!isKnowledgeJson.value) {
    return 0
  }
  const docs = parsedJson.value.docs || []
  let total = 0
  for (let i = 0; i < docs.length; i += 1) {
    const entities = docs[i].extracted_entities
    if (Array.isArray(entities)) {
      total += entities.length
    }
  }
  return total
})

const jsonTotalTriples = computed(() => {
  if (!isKnowledgeJson.value) {
    return 0
  }
  const docs = parsedJson.value.docs || []
  let total = 0
  for (let i = 0; i < docs.length; i += 1) {
    const triples = docs[i].extracted_triples
    if (Array.isArray(triples)) {
      total += triples.length
    }
  }
  return total
})

const jsonRowHeight = 40
const jsonPageSize = 50
const jsonDocsLoadedCount = ref(jsonPageSize)
const isLoadingMoreJsonDocs = ref(false)

const jsonAllRows = computed(() => {
  if (!isKnowledgeJson.value) {
    return []
  }
  const docs = parsedJson.value.docs || []
  const result = []
  for (let i = 0; i < docs.length; i += 1) {
    const doc = docs[i]
    const entities = Array.isArray(doc.extracted_entities) ? doc.extracted_entities.length : 0
    const triples = Array.isArray(doc.extracted_triples) ? doc.extracted_triples.length : 0
    result.push({
      index: i + 1,
      idx: doc.idx || '',
      passage: doc.passage || '',
      entityCount: entities,
      tripleCount: triples
    })
  }
  return result
})

const jsonFilteredRows = computed(() => {
  const source = jsonAllRows.value
  const keyword = docsFilterKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return source
  }
  return source.filter((item) => {
    const idxValue = String(item.idx || '').toLowerCase()
    const passageValue = String(item.passage || '').toLowerCase()
    return idxValue.includes(keyword) || passageValue.includes(keyword)
  })
})

const filteredJsonDocsPreview = computed(() => {
  if (!isKnowledgeJson.value) {
    return []
  }
  const source = jsonFilteredRows.value
  const count = Math.min(source.length, jsonDocsLoadedCount.value)
  return source.slice(0, count)
})

const jsonVirtualColumns = computed(() => {
  const baseColumns = [
    {
      key: 'index',
      dataKey: 'index',
      title: '#',
      width: 60,
      align: 'center'
    },
    {
      key: 'idx',
      dataKey: 'idx',
      title: '文档 ID',
      width: 180,
      minWidth: 120,
      maxWidth: 260,
      flexGrow: 1
    },
    {
      key: 'passage',
      dataKey: 'passage',
      title: '文本摘要',
      width: 260,
      minWidth: 200,
      flexGrow: 2
    }
  ]
  baseColumns.push({
    key: 'entityCount',
    dataKey: 'entityCount',
    title: '实体',
    width: 100,
    align: 'center',
    cellRenderer: ({ rowData }) => {
      const hasEntities = rowData.entityCount > 0
      const docIndex = rowData.index - 1
      const docs = Array.isArray(parsedJson.value.docs) ? parsedJson.value.docs : []
      const entities = docs[docIndex] && Array.isArray(docs[docIndex].extracted_entities) ? docs[docIndex].extracted_entities : []
      const title = hasEntities ? `共 ${rowData.entityCount} 个实体` : '无实体'
      if (!hasEntities) {
        return h(
          'span',
          {
            class: 'json-entity-count json-entity-count--empty'
          },
          '0'
        )
      }
      return h(
        ElPopover,
        {
          placement: 'left',
          width: 360,
          trigger: 'click'
        },
        {
          reference: () =>
            h(
              ElTag,
              {
                size: 'small',
                type: 'info',
                effect: 'plain',
                class: 'json-entity-count-tag',
                title
              },
              () => `${rowData.entityCount} 个`
            ),
          default: () =>
            h(
              'div',
              { class: 'json-entity-popover' },
              [
                h('div', { class: 'json-entity-popover-title' }, title),
                h(
                  'div',
                  { class: 'json-entity-popover-list' },
                  entities.map((ent, idx) =>
                    h(
                      'div',
                      { class: 'json-entity-item', key: `${docIndex}-ent-${idx}` },
                      `${idx + 1}. ${ent}`
                    )
                  )
                )
              ]
            )
        }
      )
    }
  })
  baseColumns.push({
    key: 'tripleCount',
    dataKey: 'tripleCount',
    title: '三元组',
    width: 110,
    align: 'center',
    cellRenderer: ({ rowData }) => {
      const hasTriples = rowData.tripleCount > 0
      const docIndex = rowData.index - 1
      const docs = Array.isArray(parsedJson.value.docs) ? parsedJson.value.docs : []
      const triples = docs[docIndex] && Array.isArray(docs[docIndex].extracted_triples) ? docs[docIndex].extracted_triples : []
      const title = hasTriples ? `共 ${rowData.tripleCount} 个三元组` : '无三元组'
      if (!hasTriples) {
        return h(
          'span',
          {
            class: 'json-triple-count json-triple-count--empty'
          },
          '0'
        )
      }
      return h(
        ElPopover,
        {
          placement: 'left',
          width: 420,
          trigger: 'click'
        },
        {
          reference: () =>
            h(
              ElTag,
              {
                size: 'small',
                type: 'success',
                effect: 'plain',
                class: 'json-triple-count-tag',
                title
              },
              () => `${rowData.tripleCount} 个`
            ),
          default: () =>
            h(
              'div',
              { class: 'json-triple-popover' },
              [
                h('div', { class: 'json-triple-popover-title' }, title),
                h(
                  'div',
                  { class: 'json-triple-popover-list' },
                  triples.map((triple, idx) => {
                    const [head, relation, tail] = triple
                    return h(
                      'div',
                      { class: 'json-triple-item', key: `${docIndex}-triple-${idx}` },
                      [
                        h('span', { class: 'json-triple-index' }, `${idx + 1}. `),
                        h('span', { class: 'json-triple-entity json-triple-head' }, head),
                        h('span', { class: 'json-triple-sep' }, ' — '),
                        h('span', { class: 'json-triple-relation' }, relation),
                        h('span', { class: 'json-triple-sep' }, ' → '),
                        h('span', { class: 'json-triple-entity json-triple-tail' }, tail)
                      ]
                    )
                  })
                )
              ]
            )
        }
      )
    }
  })
  return baseColumns
})

const handleJsonTableScroll = ({ scrollTop }) => {
  if (!isKnowledgeJson.value) {
    return
  }
  const total = jsonFilteredRows.value.length
  if (jsonDocsLoadedCount.value >= total) {
    return
  }
  const topIndex = Math.floor(scrollTop / jsonRowHeight)
  const buffer = 10
  if (topIndex + buffer < jsonDocsLoadedCount.value) {
    return
  }
  if (isLoadingMoreJsonDocs.value) {
    return
  }
  isLoadingMoreJsonDocs.value = true
  const nextCount = Math.min(jsonDocsLoadedCount.value + jsonPageSize, total)
  jsonDocsLoadedCount.value = nextCount
  requestAnimationFrame(() => {
    isLoadingMoreJsonDocs.value = false
  })
}

const translationDict = ref({
  blocks: {
    inner: '内在',
    bot: '机器人',
    personality: '人格',
    expression: '表达',
    chat: '聊天',
    memory: '记忆',
    dream: '梦境',
    tool: '工具',
    tools: '工具',
    emoji: '表情',
    voice: '语音',
    system: '系统',
    profile: '档案',
    preference: '偏好'
  },
  tokens: {
    inner: '内在',
    bot: '机器人',
    personality: '人格',
    expression: '表达',
    chat: '聊天',
    memory: '记忆',
    dream: '梦境',
    tool: '工具',
    tools: '工具',
    emoji: '表情',
    voice: '语音',
    system: '系统',
    profile: '档案',
    preference: '偏好',
    config: '配置',
    setting: '设置',
    settings: '设置',
    user: '用户',
    global: '全局',
    persona: '人设',
    behavior: '行为'
  }
})

const translationDictLoaded = ref(false)

const filteredTomlBlocks = computed(() => {
  if (!isTomlVisual.value) {
    return []
  }
  const source = tomlBlocks.value
  const keyword = docsFilterKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return source
  }
  return source.filter((item) => {
    const titleValue = String(item.title || '').toLowerCase()
    const descValue = String(item.description || '').toLowerCase()
    if (titleValue.includes(keyword) || descValue.includes(keyword)) {
      return true
    }
    const keyValues = Array.isArray(item.keyValues) ? item.keyValues : []
    for (let i = 0; i < keyValues.length; i += 1) {
      const kv = keyValues[i]
      const keyText = String(kv.key || '').toLowerCase()
      const valueText = String(kv.value || '').toLowerCase()
      const commentText = String(kv.comment || '').toLowerCase()
      if (keyText.includes(keyword) || valueText.includes(keyword) || commentText.includes(keyword)) {
        return true
      }
    }
    return false
  })
})

const ensureTranslationDictLoaded = async () => {
  if (translationDictLoaded.value) {
    return
  }
  try {
    const response = await getTranslationDictionary()
    if (response && response.data) {
      const data = response.data || {}
      const blocks = data.blocks || {}
      const tokens = data.tokens || {}
      if (Object.keys(blocks).length || Object.keys(tokens).length) {
        translationDict.value = {
          blocks: { ...translationDict.value.blocks, ...blocks },
          tokens: { ...translationDict.value.tokens, ...tokens }
        }
      }
    }
  } catch (error) {}
  translationDictLoaded.value = true
}

const translateTomlBlockTitle = (title) => {
  if (!title) {
    return ''
  }
  const raw = String(title)
  const lower = raw.toLowerCase()
  const dictValue = translationDict.value || {}
  const fullMap = dictValue.blocks || {}
  if (fullMap[lower]) {
    return fullMap[lower]
  }
  const tokenMap = dictValue.tokens || {}
  const tokens = lower.split(/[_\-\.]/g).filter(Boolean)
  const translatedTokens = tokens
    .map((token) => tokenMap[token] || token)
    .filter(Boolean)
  if (!translatedTokens.length) {
    return ''
  }
  return translatedTokens.join(' ')
}

const getTomlBlockDisplayTitle = (block) => {
  if (!block) {
    return ''
  }
  const base = block.title || `块 ${block.index}`
  return base
}

const getTomlBlockTranslation = (block) => {
  if (!block || !block.title) {
    return ''
  }
  return translateTomlBlockTitle(block.title)
}

watch(
  () => filteredTomlBlocks.value,
  (blocks) => {
    if (!blocks.length) {
      activeTomlTab.value = ''
      return
    }
    if (!activeTomlTab.value) {
      activeTomlTab.value = String(blocks[0].index)
    } else {
      const exists = blocks.some((block) => String(block.index) === activeTomlTab.value)
      if (!exists) {
        activeTomlTab.value = String(blocks[0].index)
      }
    }
  },
  {
    immediate: true
  }
)

const hasVisualPanel = computed(() => {
  return isKnowledgeJson.value || isTomlVisual.value
})

const getDisplayValue = (value) => {
  if (value === null || value === undefined) {
    return ''
  }
  const lines = String(value).split(/\r?\n/)
  let start = 0
  let end = lines.length - 1
  while (start <= end && !lines[start].trim()) {
    start += 1
  }
  while (end >= start && !lines[end].trim()) {
    end -= 1
  }
  if (start > end) {
    return ''
  }
  const first = lines[start].trim()
  const last = lines[end].trim()
  if (first === '[' && last === ']') {
    const inner = lines.slice(start + 1, end)
    return inner.join('\n')
  }
  let textLines = lines.slice(start, end + 1)
  if (
    (first === '"""' && last === '"""') ||
    (first === "'''" && last === "'''")
  ) {
    if (end <= start + 1) {
      return ''
    }
    textLines = lines.slice(start + 1, end)
  }
  let text = textLines.join('\n')
  let trimmed = text.trim()
  if (
    (trimmed.startsWith('"""') && trimmed.endsWith('"""') && trimmed.length >= 6) ||
    (trimmed.startsWith("'''") && trimmed.endsWith("'''") && trimmed.length >= 6)
  ) {
    trimmed = trimmed.slice(3, trimmed.length - 3).trim()
  }
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"') && trimmed.length >= 2) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'") && trimmed.length >= 2)
  ) {
    trimmed = trimmed.slice(1, trimmed.length - 1)
  }
  return trimmed
}

const isMultiLineValue = (value) => {
  const text = getDisplayValue(value)
  if (!text) {
    return false
  }
  return text.includes('\n')
}

const isListValue = (value) => {
  if (value === null || value === undefined) {
    return false
  }
  const text = String(value).trim()
  if (!text.startsWith('[')) {
    return false
  }
  if (text.includes('{')) {
    return false
  }
  return true
}

const isBooleanValue = (value) => {
  const text = getDisplayValue(value).trim().toLowerCase()
  return text === 'true' || text === 'false'
}

const getBooleanLabel = (value) => {
  const text = getDisplayValue(value).trim().toLowerCase()
  if (text === 'true') {
    return 'true'
  }
  if (text === 'false') {
    return 'false'
  }
  return getDisplayValue(value)
}

const getBooleanTagType = (value) => {
  const text = getDisplayValue(value).trim().toLowerCase()
  if (text === 'true') {
    return 'success'
  }
  if (text === 'false') {
    return 'info'
  }
  return 'info'
}

const getListEntries = (value) => {
  if (value === null || value === undefined) {
    return []
  }
  const lines = String(value).split(/\r?\n/)
  const result = []
  for (let i = 0; i < lines.length; i += 1) {
    let line = lines[i]
    if (!line) {
      continue
    }
    let trimmed = line.trim()
    if (!trimmed) {
      continue
    }
    if (trimmed === '[' || trimmed === ']') {
      continue
    }
    const hashIndex = trimmed.indexOf('#')
    if (hashIndex !== -1) {
      trimmed = trimmed.slice(0, hashIndex).trim()
    }
    if (!trimmed) {
      continue
    }
    if (trimmed.endsWith(',')) {
      trimmed = trimmed.slice(0, -1).trim()
    }
    if (!trimmed) {
      continue
    }
    result.push(trimmed)
  }
  return result
}

const parseLearningList = (value) => {
  const entries = getListEntries(value)
  const result = []
  for (let i = 0; i < entries.length; i += 1) {
    const raw = entries[i]
    try {
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed) || parsed.length < 4) {
        continue
      }
      const scope = parsed[0] || ''
      const useExpr = parsed[1] || ''
      const learnExpr = parsed[2] || ''
      const learnJargon = parsed[3] || ''
      let scopeLabel = scope
      if (!scopeLabel) {
        scopeLabel = '全局'
      }
      result.push({
        scope,
        scopeLabel,
        useExpr,
        learnExpr,
        learnJargon
      })
    } catch (error) {}
  }
  return result
}

const parseKeywordRules = (value) => {
  const text = getDisplayValue(value)
  if (!text) {
    return []
  }
  const matches = text.match(/\{[^}]*\}/g)
  if (!matches) {
    return []
  }
  const result = []
  for (let i = 0; i < matches.length; i += 1) {
    const block = matches[i]
    let keywords = []
    let reaction = ''
    const keywordsMatch = block.match(/keywords\s*=\s*(\[[^\]]*\])/)
    if (keywordsMatch) {
      try {
        keywords = JSON.parse(keywordsMatch[1])
      } catch (error) {}
    }
    const reactionMatch = block.match(/reaction\s*=\s*"([^"]*)"/)
    if (reactionMatch) {
      reaction = reactionMatch[1]
    }
    result.push({
      keywords,
      reaction
    })
  }
  return result
}

const parseRegexRules = (value) => {
  const text = getDisplayValue(value)
  if (!text) {
    return []
  }
  const matches = text.match(/\{[^}]*\}/g)
  if (!matches) {
    return []
  }
  const result = []
  for (let i = 0; i < matches.length; i += 1) {
    const block = matches[i]
    let patterns = []
    let reaction = ''
    const regexMatch = block.match(/regex\s*=\s*(\[[^\]]*\])/)
    if (regexMatch) {
      try {
        patterns = JSON.parse(regexMatch[1])
      } catch (error) {}
    }
    const reactionMatch = block.match(/reaction\s*=\s*"([^"]*)"/)
    if (reactionMatch) {
      reaction = reactionMatch[1]
    }
    result.push({
      patterns,
      reaction
    })
  }
  return result
}

const parseChatPrompts = (value) => {
  const text = getDisplayValue(value)
  if (!text) {
    return []
  }
  const lines = text.split(/\r?\n/).filter((line) => line.trim())
  const result = []
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].trim()
    const firstColon = line.indexOf(':')
    const secondColon = firstColon === -1 ? -1 : line.indexOf(':', firstColon + 1)
    const thirdColon = secondColon === -1 ? -1 : line.indexOf(':', secondColon + 1)
    let scope = ''
    let content = line
    if (thirdColon !== -1) {
      scope = line.slice(0, thirdColon)
      content = line.slice(thirdColon + 1).trim()
    }
    result.push({
      scope,
      content
    })
  }
  return result
}

watch(
  () => ({
    json: isKnowledgeJson.value,
    toml: isTomlVisual.value
  }),
  (state) => {
    if (state.json || state.toml) {
      activeTab.value = 'detail'
    } else {
      activeTab.value = 'source'
    }
  },
  {
    immediate: true
  }
)

const previewSource = computed(() => {
  const value = props.content || ''
  if (!value) {
    return ''
  }
  const lang = resolvedLanguage.value
  if (lang === 'json') {
    try {
      const parsed = JSON.parse(value)
      return JSON.stringify(parsed, null, 2)
    } catch (error) {
      return value
    }
  }
  return value
})

const monacoLanguage = computed(() => {
  const lang = resolvedLanguage.value
  if (lang === 'json') {
    return 'json'
  }
  return 'plaintext'
})

const createEditor = () => {
  if (!editorContainer.value) {
    return
  }
  if (editorInstance) {
    editorInstance.dispose()
    editorInstance = null
  }
  if (monacoLanguage.value === 'json') {
    ensureJsonFolding()
  }
  monaco.editor.setTheme('vs-dark')
  editorInstance = monaco.editor.create(editorContainer.value, {
    value: previewSource.value,
    language: monacoLanguage.value,
    readOnly: true,
    wordWrap: wrapEnabled.value ? 'on' : 'off',
    lineNumbers: 'on',
    glyphMargin: true,
    showFoldingControls: 'always',
    minimap: {
      enabled: false
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    folding: true
  })
}

const updateEditorContent = () => {
  if (!editorInstance) {
    return
  }
  const model = editorInstance.getModel()
  const value = previewSource.value || ''
  if (model) {
    model.setValue(value)
    monaco.editor.setModelLanguage(model, monacoLanguage.value)
  } else {
    editorInstance.setValue(value)
  }
}

watch(
  () => props.content,
  () => {
    wrapEnabled.value = true
    nextTick(() => {
      if (editorInstance) {
        updateEditorContent()
        editorInstance.updateOptions({
          wordWrap: wrapEnabled.value ? 'on' : 'off'
        })
      } else if (dialogVisible.value) {
        createEditor()
      }
    })
  }
)

watch(
  () => dialogVisible.value,
  (visible) => {
    if (visible) {
      nextTick(() => {
        createEditor()
      })
    } else if (editorInstance) {
      editorInstance.dispose()
      editorInstance = null
    }
  }
)

onMounted(() => {
  if (dialogVisible.value) {
    createEditor()
  }
})

onBeforeUnmount(() => {
  if (editorInstance) {
    editorInstance.dispose()
    editorInstance = null
  }
})

const handleDownload = () => {
  emit('download')
}
</script>

<style scoped>
.file-viewer-dialog :deep(.el-dialog__body) {
  padding: 16px 20px;
}

.file-viewer-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tab-fixed-content {
  height: 520px;
}

.file-viewer-tabs {
  margin-top: 8px;
}

.json-visual-panel {
  height: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background-color: rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.json-visual-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.json-table-wrapper {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.json-entity-count-tag,
.json-triple-count-tag {
  cursor: pointer;
}

.json-entity-count--empty,
.json-triple-count--empty {
  color: var(--el-text-color-placeholder);
}

.json-entity-popover,
.json-triple-popover {
  max-height: 320px;
  overflow: auto;
}

.json-entity-popover-title,
.json-triple-popover-title {
  font-weight: 500;
  margin-bottom: 8px;
}

.json-entity-popover-preview {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.json-entity-popover-list,
.json-triple-popover-list {
  font-size: 13px;
  line-height: 1.5;
}

.json-entity-item,
.json-triple-item {
  margin-bottom: 4px;
}

.json-triple-index {
  color: var(--el-text-color-secondary);
}

.json-triple-entity {
  font-weight: 500;
}

.json-triple-relation {
  color: var(--el-color-primary);
}

.json-triple-sep {
  color: var(--el-text-color-placeholder);
}

.json-triple-more-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.toml-vertical-container {
  flex: 1 1 auto;
  min-height: 0;
  margin-top: 4px;
  overflow: hidden;
}

.toml-vertical-tabs {
  height: 100%;
}

.toml-vertical-tabs :deep(.el-tabs__content) {
  height: 100%;
}

.toml-vertical-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.toml-block-card-container {
  height: 100%;
  padding: 0 4px 4px;
  box-sizing: border-box;
}

.toml-block-card {
  height: 100%;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  padding: 10px 12px;
  background-color: rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.toml-block-meta {
  margin-bottom: 12px;
}

.toml-block-title {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  text-align: right;
}

.toml-block-title-main {
  font-size: 14px;
  font-weight: 500;
}

.toml-block-title-sub {
  font-size: 12px;
  color: var(--muted-text-color);
}

.toml-block-description {
  font-size: 12px;
  color: var(--muted-text-color);
  margin-bottom: 4px;
}

.toml-block-extra {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--muted-text-color);
}

.toml-block-line-range {
  opacity: 0.9;
}

.toml-kv-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.toml-kv-card {
  width: 100%;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background-color: rgba(0, 0, 0, 0.08);
  box-sizing: border-box;
}

.toml-kv-key {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
}

.toml-kv-key-text {
  flex: 0 0 auto;
}

.toml-kv-info-icon {
  flex: 0 0 auto;
  font-size: 14px;
  cursor: default;
}

.toml-kv-value {
  font-size: 12px;
  word-break: break-all;
}

.toml-learning-list,
.toml-keyword-rules,
.toml-regex-rules {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.toml-learning-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toml-learning-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.toml-keyword-tags,
.toml-regex-patterns {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.toml-keyword-reaction {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.4;
}

.toml-keyword-tag,
.toml-regex-tag {
  max-width: 100%;
  white-space: normal;
  word-break: break-all;
}

.toml-boolean-tag {
  display: inline-flex;
}

.toml-chat-prompts {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.toml-chat-prompt {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toml-chat-scope {
  margin-bottom: 2px;
}

.toml-chat-scope-tag {
  max-width: 100%;
}

.toml-chat-content {
  font-size: 12px;
  line-height: 1.4;
  white-space: pre-wrap;
}

.toml-array-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.toml-array-tag {
  max-width: 100%;
  white-space: normal;
  word-break: break-all;
  line-height: 1.4;
}

.toml-array-tag :deep(.el-tag__content) {
  white-space: normal;
  word-break: break-all;
}

.toml-kv-input,
.toml-kv-textarea {
  width: 100%;
}

.toml-tab-label {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  text-align: right;
}

.toml-tab-label-main {
  font-size: 13px;
}

.toml-tab-label-sub {
  font-size: 11px;
  color: var(--muted-text-color);
}

.json-visual-title {
  font-size: 13px;
  font-weight: 500;
}

.json-visual-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.json-stat-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 80px;
}

.json-stat-label {
  font-size: 11px;
  color: var(--muted-text-color);
}

.json-stat-value {
  font-size: 13px;
}

.json-filter-wrapper {
  display: flex;
  align-items: center;
}

.json-filter-input {
  width: 220px;
}

.file-viewer-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  font-size: 13px;
  color: var(--muted-text-color);
}

.file-language-tag {
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(246, 196, 83, 0.4);
  font-size: 11px;
}

.file-truncate-tip {
  margin-left: 8px;
  font-size: 11px;
  opacity: 0.8;
}

.file-viewer-content {
  height: 520px;
  max-height: 520px;
  overflow: hidden;
  border-radius: 8px;
  background-color: var(--hover-color);
  border: 1px solid var(--border-color);
}

.code-block {
  margin: 0;
  padding: 12px 14px;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre;
}

.file-viewer-loading {
  padding: 12px;
}

.monaco-editor-container {
  width: 100%;
  height: 100%;
}

.code-editor {
  display: flex;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}

.code-editor-gutter {
  flex: 0 0 auto;
  padding: 12px 6px 12px 10px;
  text-align: right;
  user-select: none;
  border-right: 1px solid var(--border-color);
  background-color: rgba(0, 0, 0, 0.08);
}

.code-line-number {
  color: var(--muted-text-color);
  padding: 0 4px;
  cursor: default;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.code-line-number-text {
  min-width: 24px;
  text-align: right;
}

.code-fold-marker {
  width: 10px;
  margin-right: 4px;
  font-size: 10px;
}

.code-line-number.is-foldable {
  cursor: pointer;
}

.code-line-number.is-foldable:hover {
  color: var(--secondary-color);
}

.code-editor-lines {
  flex: 1 1 auto;
  padding: 12px 14px;
}

.code-line-pre {
  margin: 0;
  white-space: pre;
}

.code-editor.is-wrap-enabled .code-line-pre {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
