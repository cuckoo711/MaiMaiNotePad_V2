import apiClient from './index'

// 获取翻译字典 (后端 InitDictionaryViewSet)
export const getTranslationDictionary = () => {
  return apiClient.get('/init/dictionary/', {
    params: {
      dictionary_key: 'translation' // 假设后端配置了 'translation' 这个字典key
    }
  })
}

