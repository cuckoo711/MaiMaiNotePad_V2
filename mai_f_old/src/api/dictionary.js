import apiClient from './index'

// 获取翻译字典 (后端 InitDictionaryViewSet)
// 前端期望返回: { data: { blocks: {...}, tokens: {...} } }
// 后端 InitDictionaryViewSet 返回列表: [{label, value, ...}, ...]
// 我们需要在这里进行转换和合并
export const getTranslationDictionary = async () => {
  try {
    // 并行获取 blocks 和 tokens
    const [blocksRes, tokensRes] = await Promise.all([
      apiClient.get('/init/dictionary/', { params: { dictionary_key: 'toml_visualizer_blocks' } }),
      apiClient.get('/init/dictionary/', { params: { dictionary_key: 'toml_visualizer_tokens' } })
    ])

    const blocks = {}
    if (blocksRes.data && Array.isArray(blocksRes.data)) {
      blocksRes.data.forEach(item => {
        blocks[item.value] = item.label
      })
    }

    const tokens = {}
    if (tokensRes.data && Array.isArray(tokensRes.data)) {
      tokensRes.data.forEach(item => {
        tokens[item.value] = item.label
      })
    }

    return {
      code: 2000,
      msg: 'success',
      data: {
        blocks,
        tokens
      }
    }
  } catch (error) {
    console.error('Failed to fetch translation dictionary:', error)
    return {
      code: 500,
      msg: 'failed',
      data: {
        blocks: {},
        tokens: {}
      }
    }
  }
}

