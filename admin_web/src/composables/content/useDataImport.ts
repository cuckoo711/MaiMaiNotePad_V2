import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import {
  type ImportResult,
  validateFileFormat,
  parseImportResult,
} from './dataImportUtils';

// 重新导出工具函数和类型
export { validateFileFormat, parseImportResult };
export type { ImportResult };

/**
 * 数据导入选项接口
 */
export interface DataImportOptions {
  /** 模块名称 */
  moduleName: string;
  /** 导入 API 函数 */
  importApi: (file: File) => Promise<ImportResult>;
  /** 模板下载 API 函数 */
  templateApi: () => Promise<void>;
}

/**
 * 数据导入 composable 返回值接口
 */
export interface UseDataImportReturn {
  importDialogVisible: ReturnType<typeof ref<boolean>>;
  importFile: ReturnType<typeof ref<File | null>>;
  importLoading: ReturnType<typeof ref<boolean>>;
  importResult: ReturnType<typeof ref<ImportResult | null>>;
  openImportDialog: () => void;
  handleImport: () => Promise<void>;
  handleDownloadTemplate: () => Promise<void>;
  handleFileChange: (file: File) => boolean;
}

/**
 * 数据导入组合式函数
 *
 * 提供导入对话框状态管理和导入执行逻辑，供各模块 index.vue 调用
 */
export function useDataImport(options: DataImportOptions): UseDataImportReturn {
  const { importApi, templateApi } = options;

  const importDialogVisible = ref(false);
  const importFile = ref<File | null>(null);
  const importLoading = ref(false);
  const importResult = ref<ImportResult | null>(null);

  /**
   * 打开导入对话框
   */
  const openImportDialog = (): void => {
    importFile.value = null;
    importResult.value = null;
    importLoading.value = false;
    importDialogVisible.value = true;
  };

  /**
   * 处理文件选择变化
   * @param file 选择的文件
   * @returns 是否通过格式验证
   */
  const handleFileChange = (file: File): boolean => {
    if (!validateFileFormat(file.name)) {
      ElMessage.error('仅支持 .xlsx 和 .csv 格式文件');
      importFile.value = null;
      return false;
    }
    importFile.value = file;
    return true;
  };

  /**
   * 执行导入
   */
  const handleImport = async (): Promise<void> => {
    if (!importFile.value) {
      ElMessage.warning('请先选择导入文件');
      return;
    }

    importLoading.value = true;
    try {
      const result = await importApi(importFile.value);
      const parsed = parseImportResult(result);
      importResult.value = parsed;

      if (parsed.fail_count === 0) {
        ElMessage.success(`导入完成：${parsed.success_count} 条记录导入成功`);
      } else {
        ElMessage.warning(
          `导入完成：${parsed.success_count} 条成功，${parsed.fail_count} 条失败`
        );
      }
    } catch (error: any) {
      ElMessage.error('导入失败：' + (error.message || '未知错误'));
    } finally {
      importLoading.value = false;
    }
  };

  /**
   * 下载导入模板
   */
  const handleDownloadTemplate = async (): Promise<void> => {
    try {
      await templateApi();
    } catch (error: any) {
      ElMessage.error('模板下载失败，请稍后重试');
    }
  };

  return {
    importDialogVisible,
    importFile,
    importLoading,
    importResult,
    openImportDialog,
    handleImport,
    handleDownloadTemplate,
    handleFileChange,
  };
}
