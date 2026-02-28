import { ref, computed } from 'vue';
import { ElMessageBox, ElMessage } from 'element-plus';
import {
  type BatchResult,
  formatSelectionText,
  validateRejectReason,
  parseBatchResult,
} from './batchOperationUtils';

// 重新导出工具函数和类型，方便外部使用
export { formatSelectionText, validateRejectReason, parseBatchResult };
export type { BatchResult };

/**
 * 批量操作选项接口
 */
export interface BatchOperationOptions {
  /** 模块名称，用于显示 */
  moduleName: string;
  /** 批量审核通过 API */
  batchApproveApi?: (ids: string[]) => Promise<BatchResult>;
  /** 批量审核拒绝 API */
  batchRejectApi?: (ids: string[], reason: string) => Promise<BatchResult>;
  /** 批量删除 API */
  batchDeleteApi?: (ids: string[]) => Promise<BatchResult>;
  /** 操作成功后的回调（通常是刷新列表） */
  onSuccess: () => void;
}

/**
 * 批量操作 composable 返回值接口
 */
export interface UseBatchOperationReturn {
  selectedRows: ReturnType<typeof ref<any[]>>;
  selectedCount: ReturnType<typeof computed<number>>;
  hasSelection: ReturnType<typeof computed<boolean>>;
  handleSelectionChange: (rows: any[]) => void;
  clearSelection: () => void;
  handleBatchApprove: () => Promise<void>;
  handleBatchReject: () => Promise<void>;
  handleBatchDelete: () => Promise<void>;
}

/**
 * 显示批量操作结果摘要
 */
function showResultSummary(result: BatchResult, operationName: string): void {
  if (result.fail_count === 0) {
    ElMessage.success(`${operationName}完成：${result.success_count} 条记录操作成功`);
  } else if (result.success_count === 0) {
    ElMessage.error(`${operationName}失败：${result.fail_count} 条记录操作失败`);
  } else {
    ElMessage.warning(
      `${operationName}完成：${result.success_count} 条成功，${result.fail_count} 条失败`
    );
  }
  // 如果有失败详情，显示详细信息
  if (result.failures && result.failures.length > 0) {
    const failDetails = result.failures
      .map((f) => `ID: ${f.id}，原因: ${f.reason}`)
      .join('\n');
    ElMessageBox.alert(
      `失败记录详情：\n${failDetails}`,
      '操作结果详情',
      { type: 'warning', confirmButtonText: '确定' }
    );
  }
}

/**
 * 批量操作组合式函数
 *
 * 提供批量选择状态管理和批量操作执行逻辑，供各模块 index.vue 调用
 */
export function useBatchOperation(options: BatchOperationOptions): UseBatchOperationReturn {
  const { batchApproveApi, batchRejectApi, batchDeleteApi, onSuccess } = options;

  const selectedRows = ref<any[]>([]);
  const selectedCount = computed(() => selectedRows.value.length);
  const hasSelection = computed(() => selectedRows.value.length > 0);

  const handleSelectionChange = (rows: any[]): void => {
    selectedRows.value = rows;
  };

  const clearSelection = (): void => {
    selectedRows.value = [];
  };

  const getSelectedIds = (): string[] => {
    return selectedRows.value.map((row) => row.id);
  };

  const handleBatchApprove = async (): Promise<void> => {
    if (!batchApproveApi) return;
    const ids = getSelectedIds();
    if (ids.length === 0) return;

    try {
      await ElMessageBox.confirm(
        `确定批量审核通过选中的 ${ids.length} 条记录吗？`,
        '批量审核通过',
        { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
      );
    } catch {
      return;
    }

    try {
      const result = await batchApproveApi(ids);
      const parsed = parseBatchResult(result, ids.length);
      showResultSummary(parsed, '批量审核通过');
      clearSelection();
      onSuccess();
    } catch (error: any) {
      if (error?.response?.status === 403) {
        ElMessage.error('权限不足，无法执行此操作');
        clearSelection();
      } else {
        ElMessage.error('批量操作失败，请检查网络连接后重试');
      }
    }
  };

  const handleBatchReject = async (): Promise<void> => {
    if (!batchRejectApi) return;
    const ids = getSelectedIds();
    if (ids.length === 0) return;

    let reason = '';
    try {
      const { value } = await ElMessageBox.prompt(
        `请输入拒绝原因（将应用于选中的 ${ids.length} 条记录）`,
        '批量审核拒绝',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          inputType: 'textarea',
          inputPlaceholder: '请输入拒绝原因',
          inputValidator: (val: string) => {
            if (!validateRejectReason(val || '')) {
              return '拒绝原因为必填项';
            }
            return true;
          },
        }
      );
      reason = value;
    } catch {
      return;
    }

    try {
      const result = await batchRejectApi(ids, reason);
      const parsed = parseBatchResult(result, ids.length);
      showResultSummary(parsed, '批量审核拒绝');
      clearSelection();
      onSuccess();
    } catch (error: any) {
      if (error?.response?.status === 403) {
        ElMessage.error('权限不足，无法执行此操作');
        clearSelection();
      } else {
        ElMessage.error('批量操作失败，请检查网络连接后重试');
      }
    }
  };

  const handleBatchDelete = async (): Promise<void> => {
    if (!batchDeleteApi) return;
    const ids = getSelectedIds();
    if (ids.length === 0) return;

    try {
      await ElMessageBox.confirm(
        `确定批量删除选中的 ${ids.length} 条记录吗？此操作不可恢复！`,
        '批量删除',
        { confirmButtonText: '确定', cancelButtonText: '取消', type: 'error' }
      );
    } catch {
      return;
    }

    try {
      const result = await batchDeleteApi(ids);
      const parsed = parseBatchResult(result, ids.length);
      showResultSummary(parsed, '批量删除');
      clearSelection();
      onSuccess();
    } catch (error: any) {
      if (error?.response?.status === 403) {
        ElMessage.error('权限不足，无法执行此操作');
        clearSelection();
      } else {
        ElMessage.error('批量操作失败，请检查网络连接后重试');
      }
    }
  };

  return {
    selectedRows,
    selectedCount,
    hasSelection,
    handleSelectionChange,
    clearSelection,
    handleBatchApprove,
    handleBatchReject,
    handleBatchDelete,
  };
}
