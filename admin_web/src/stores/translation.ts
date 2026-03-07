import { defineStore } from 'pinia';
import { request } from '../utils/service';

/**
 * 翻译项接口
 */
export interface TranslationItem {
  id: string;
  source_text: string;
  translated_text: string;
  source_language: string;
  target_language: string;
  translation_type: string;
  sort: number;
  status: boolean;
}

/**
 * 翻译 Store 状态接口
 */
export interface TranslationStates {
  data: Map<string, string>;
  loading: boolean;
  error: string | null;
}

/**
 * 翻译管理数据
 * @methods getTranslationsByType 获取指定类型的翻译数据
 * @methods getTranslation 获取翻译文本
 * @methods clearTranslations 清空翻译数据
 */
export const useTranslationStore = defineStore('Translation', {
  state: (): TranslationStates => ({
    data: new Map(),
    loading: false,
    error: null,
  }),
  
  actions: {
    /**
     * 获取指定类型的翻译数据
     * @param translationType 翻译类型
     * @returns 翻译 Map（原文 -> 译文）
     */
    async getTranslationsByType(translationType: string): Promise<Map<string, string>> {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await request({
          url: `/api/system/translation/get_by_type/?translation_type=${translationType}`,
          method: 'get',
        });
        
        // 转换为 Map 结构
        const translationMap = new Map<string, string>();
        // 响应格式：{ code: 2000, msg: '获取成功', data: [...] }
        const data = response.data;
        if (data && Array.isArray(data)) {
          data.forEach((item: TranslationItem) => {
            translationMap.set(item.source_text, item.translated_text);
          });
        }
        
        this.data = translationMap;
        return translationMap;
      } catch (error) {
        console.error('获取翻译数据失败:', error);
        this.error = '获取翻译数据失败';
        // 降级方案：返回空 Map
        return new Map();
      } finally {
        this.loading = false;
      }
    },
    
    /**
     * 获取翻译文本
     * @param key 原文键
     * @param fallback 降级文本（默认为原文）
     * @returns 译文或降级文本
     */
    getTranslation(key: string, fallback?: string): string {
      return this.data.get(key) || fallback || key;
    },
    
    /**
     * 清空翻译数据
     */
    clearTranslations() {
      this.data.clear();
      this.error = null;
    }
  },
  
  persist: {
    enabled: true,
  },
});
