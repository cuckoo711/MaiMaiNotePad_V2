import { ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  type ExportParams,
  type ExportField,
  shouldShowLargeDataWarning,
  getExportOptions,
} from './dataExportUtils';

// 重新导出工具函数和类型
export { shouldShowLargeDataWarning, getExportOptions };
export type { ExportParams, ExportField };

/**
 * 数据导出选项接口
 */
export interface DataExportOptions {
  /** 模块名称 */
  moduleName: string;
  /** 导出 API 函数 */
  exportApi: (params: ExportParams) => Promise<void>;
  /** 可导出字段列表 */
  availableFields: ExportField[];
}

/**
 * 数据导出 composable 返回值接口
 */
export interface UseDataExportReturn {
  exportDialogVisible: ReturnType<typeof ref<boolean>>;
  exportForm: ReturnType<typeof ref<ExportParams>>;
  openExportDialog: (selectedIds?: string[]) => void;
  handleExport: (totalCount?: number) => Promise<void>;
}

/**
 * 数据导出组合式函数
 *
 * 提供导出对话框状态管理和导出执行逻辑，供各模块 index.vue 调用
 */
export function useDataExport(options: DataExportOptions): UseDataExportReturn {
  const { exportApi, availableFields } = options;

  const exportDialogVisible = ref(false);
  const exportForm = ref<ExportParams>({
    format: 'excel',
    fields: availableFields.map((f) => f.key),
  });

  /**
   * 打开导出对话框
   * @param selectedIds 选中记录的 ID 数组（可选）
   */
  const openExportDialog = (selectedIds?: string[]): void => {
    // 重置表单
    exportForm.value = {
      format: 'excel',
      fields: availableFields.map((f) => f.key),
    };
    // 如果有选中记录，附加 ids
    if (selectedIds && selectedIds.length > 0) {
      exportForm.value.ids = selectedIds;
    }
    exportDialogVisible.value = true;
  };

  /**
   * 执行导出
   * @param totalCount 数据总量（可选，用于大数据量提示）
   */
  const handleExport = async (totalCount?: number): Promise<void> => {
    // 大数据量提示
    if (totalCount && shouldShowLargeDataWarning(totalCount)) {
      try {
        await ElMessageBox.confirm(
          '数据量较大，导出可能需要一些时间',
          '提示',
          { confirmButtonText: '继续导出', cancelButtonText: '取消', type: 'warning' }
        );
      } catch {
        return; // 用户取消
      }
    }

    try {
      await exportApi(exportForm.value);
      exportDialogVisible.value = false;
      ElMessage.success('导出成功');
    } catch (error: any) {
      ElMessage.error('导出失败：' + (error.message || '未知错误'));
    }
  };

  return {
    exportDialogVisible,
    exportForm,
    openExportDialog,
    handleExport,
  };
}
