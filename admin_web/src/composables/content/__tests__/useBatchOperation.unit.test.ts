/**
 * 批量操作 composable 单元测试
 *
 * 测试 useBatchOperation 的选中状态管理、批量审核/拒绝/删除流程、
 * 以及网络错误和权限错误处理
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// 模拟 element-plus，避免 CJS 兼容性问题
vi.mock('element-plus', () => ({
  ElMessageBox: {
    confirm: vi.fn().mockResolvedValue(true),
    prompt: vi.fn().mockResolvedValue({ value: '测试拒绝原因' }),
    alert: vi.fn().mockResolvedValue(true),
  },
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

import { useBatchOperation, type BatchOperationOptions } from '../useBatchOperation';
import type { BatchResult } from '../batchOperationUtils';
import { ElMessageBox, ElMessage } from 'element-plus';

/** 创建默认的测试选项 */
function createTestOptions(overrides?: Partial<BatchOperationOptions>): BatchOperationOptions {
  return {
    moduleName: 'knowledge-base',
    batchApproveApi: vi.fn().mockResolvedValue({ success_count: 2, fail_count: 0, failures: [] }),
    batchRejectApi: vi.fn().mockResolvedValue({ success_count: 2, fail_count: 0, failures: [] }),
    batchDeleteApi: vi.fn().mockResolvedValue({ success_count: 2, fail_count: 0, failures: [] }),
    onSuccess: vi.fn(),
    ...overrides,
  };
}

describe('useBatchOperation - 选中状态管理', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('handleSelectionChange 正确更新选中状态', () => {
    const options = createTestOptions();
    const { selectedRows, selectedCount, hasSelection, handleSelectionChange } =
      useBatchOperation(options);

    // 初始状态
    expect(selectedRows.value).toEqual([]);
    expect(selectedCount.value).toBe(0);
    expect(hasSelection.value).toBe(false);

    // 选中两行
    const rows = [{ id: '1', name: '记录A' }, { id: '2', name: '记录B' }];
    handleSelectionChange(rows);

    expect(selectedRows.value).toEqual(rows);
    expect(selectedCount.value).toBe(2);
    expect(hasSelection.value).toBe(true);
  });

  it('handleSelectionChange 更新为空数组时 hasSelection 为 false', () => {
    const options = createTestOptions();
    const { hasSelection, handleSelectionChange } = useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    expect(hasSelection.value).toBe(true);

    handleSelectionChange([]);
    expect(hasSelection.value).toBe(false);
  });

  it('clearSelection 清空选中行', () => {
    const options = createTestOptions();
    const { selectedRows, selectedCount, hasSelection, handleSelectionChange, clearSelection } =
      useBatchOperation(options);

    handleSelectionChange([{ id: '1' }, { id: '2' }, { id: '3' }]);
    expect(selectedCount.value).toBe(3);

    clearSelection();
    expect(selectedRows.value).toEqual([]);
    expect(selectedCount.value).toBe(0);
    expect(hasSelection.value).toBe(false);
  });
});


describe('useBatchOperation - 批量审核通过流程', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('确认 → API 调用 → 结果摘要 → 列表刷新', async () => {
    const mockApproveApi = vi.fn().mockResolvedValue({
      success_count: 2,
      fail_count: 0,
      failures: [],
    });
    const mockOnSuccess = vi.fn();
    const options = createTestOptions({
      batchApproveApi: mockApproveApi,
      onSuccess: mockOnSuccess,
    });
    const { handleSelectionChange, handleBatchApprove } = useBatchOperation(options);

    // 选中记录
    handleSelectionChange([{ id: 'a1' }, { id: 'a2' }]);

    await handleBatchApprove();

    // 验证确认对话框被调用
    expect(ElMessageBox.confirm).toHaveBeenCalledOnce();
    // 验证 API 被调用，传入正确的 ID
    expect(mockApproveApi).toHaveBeenCalledWith(['a1', 'a2']);
    // 验证成功消息
    expect(ElMessage.success).toHaveBeenCalled();
    // 验证列表刷新回调
    expect(mockOnSuccess).toHaveBeenCalledOnce();
  });

  it('用户取消确认对话框时不调用 API', async () => {
    vi.mocked(ElMessageBox.confirm).mockRejectedValueOnce('cancel');
    const mockApproveApi = vi.fn();
    const options = createTestOptions({ batchApproveApi: mockApproveApi });
    const { handleSelectionChange, handleBatchApprove } = useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchApprove();

    expect(mockApproveApi).not.toHaveBeenCalled();
  });

  it('未选中记录时不执行操作', async () => {
    const mockApproveApi = vi.fn();
    const options = createTestOptions({ batchApproveApi: mockApproveApi });
    const { handleBatchApprove } = useBatchOperation(options);

    await handleBatchApprove();

    expect(ElMessageBox.confirm).not.toHaveBeenCalled();
    expect(mockApproveApi).not.toHaveBeenCalled();
  });

  it('未提供 batchApproveApi 时不执行操作', async () => {
    const options = createTestOptions({ batchApproveApi: undefined });
    const { handleSelectionChange, handleBatchApprove } = useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchApprove();

    expect(ElMessageBox.confirm).not.toHaveBeenCalled();
  });

  it('部分失败时显示警告消息和失败详情', async () => {
    const mockApproveApi = vi.fn().mockResolvedValue({
      success_count: 1,
      fail_count: 1,
      failures: [{ id: 'a2', reason: '记录已被删除' }],
    });
    const options = createTestOptions({ batchApproveApi: mockApproveApi });
    const { handleSelectionChange, handleBatchApprove } = useBatchOperation(options);

    handleSelectionChange([{ id: 'a1' }, { id: 'a2' }]);
    await handleBatchApprove();

    // 部分失败应显示 warning
    expect(ElMessage.warning).toHaveBeenCalled();
    // 应显示失败详情对话框
    expect(ElMessageBox.alert).toHaveBeenCalled();
  });
});

describe('useBatchOperation - 批量审核拒绝流程', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('拒绝原因验证 → API 调用 → 结果摘要', async () => {
    const mockRejectApi = vi.fn().mockResolvedValue({
      success_count: 3,
      fail_count: 0,
      failures: [],
    });
    const mockOnSuccess = vi.fn();
    const options = createTestOptions({
      batchRejectApi: mockRejectApi,
      onSuccess: mockOnSuccess,
    });
    const { handleSelectionChange, handleBatchReject } = useBatchOperation(options);

    handleSelectionChange([{ id: 'b1' }, { id: 'b2' }, { id: 'b3' }]);

    await handleBatchReject();

    // 验证 prompt 对话框被调用
    expect(ElMessageBox.prompt).toHaveBeenCalledOnce();
    // 验证 API 被调用，传入正确的 ID 和拒绝原因
    expect(mockRejectApi).toHaveBeenCalledWith(['b1', 'b2', 'b3'], '测试拒绝原因');
    // 验证成功消息
    expect(ElMessage.success).toHaveBeenCalled();
    // 验证列表刷新
    expect(mockOnSuccess).toHaveBeenCalledOnce();
  });

  it('用户取消拒绝对话框时不调用 API', async () => {
    vi.mocked(ElMessageBox.prompt).mockRejectedValueOnce('cancel');
    const mockRejectApi = vi.fn();
    const options = createTestOptions({ batchRejectApi: mockRejectApi });
    const { handleSelectionChange, handleBatchReject } = useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchReject();

    expect(mockRejectApi).not.toHaveBeenCalled();
  });

  it('prompt 对话框配置了 inputValidator 验证拒绝原因', async () => {
    const options = createTestOptions();
    const { handleSelectionChange, handleBatchReject } = useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchReject();

    // 验证 prompt 调用时传入了 inputValidator
    const promptCall = vi.mocked(ElMessageBox.prompt).mock.calls[0];
    const promptOptions = promptCall[2] as any;
    expect(promptOptions).toHaveProperty('inputValidator');
    expect(typeof promptOptions.inputValidator).toBe('function');

    // 验证空字符串被拒绝
    expect(promptOptions.inputValidator('')).toBe('拒绝原因为必填项');
    // 验证纯空格被拒绝
    expect(promptOptions.inputValidator('   ')).toBe('拒绝原因为必填项');
    // 验证有效输入通过
    expect(promptOptions.inputValidator('内容不合规')).toBe(true);
  });

  it('未提供 batchRejectApi 时不执行操作', async () => {
    const options = createTestOptions({ batchRejectApi: undefined });
    const { handleSelectionChange, handleBatchReject } = useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchReject();

    expect(ElMessageBox.prompt).not.toHaveBeenCalled();
  });
});


describe('useBatchOperation - 批量删除流程', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('确认 → API 调用 → 结果摘要', async () => {
    const mockDeleteApi = vi.fn().mockResolvedValue({
      success_count: 2,
      fail_count: 0,
      failures: [],
    });
    const mockOnSuccess = vi.fn();
    const options = createTestOptions({
      batchDeleteApi: mockDeleteApi,
      onSuccess: mockOnSuccess,
    });
    const { handleSelectionChange, handleBatchDelete } = useBatchOperation(options);

    handleSelectionChange([{ id: 'c1' }, { id: 'c2' }]);

    await handleBatchDelete();

    // 验证确认对话框被调用
    expect(ElMessageBox.confirm).toHaveBeenCalledOnce();
    // 确认对话框应包含警告信息
    const confirmCall = vi.mocked(ElMessageBox.confirm).mock.calls[0];
    expect(confirmCall[0]).toContain('不可恢复');
    // 验证 API 被调用
    expect(mockDeleteApi).toHaveBeenCalledWith(['c1', 'c2']);
    // 验证成功消息
    expect(ElMessage.success).toHaveBeenCalled();
    // 验证列表刷新
    expect(mockOnSuccess).toHaveBeenCalledOnce();
  });

  it('用户取消删除确认时不调用 API', async () => {
    vi.mocked(ElMessageBox.confirm).mockRejectedValueOnce('cancel');
    const mockDeleteApi = vi.fn();
    const options = createTestOptions({ batchDeleteApi: mockDeleteApi });
    const { handleSelectionChange, handleBatchDelete } = useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchDelete();

    expect(mockDeleteApi).not.toHaveBeenCalled();
  });

  it('全部失败时显示错误消息', async () => {
    const mockDeleteApi = vi.fn().mockResolvedValue({
      success_count: 0,
      fail_count: 2,
      failures: [
        { id: 'c1', reason: '记录被引用' },
        { id: 'c2', reason: '记录被引用' },
      ],
    });
    const options = createTestOptions({ batchDeleteApi: mockDeleteApi });
    const { handleSelectionChange, handleBatchDelete } = useBatchOperation(options);

    handleSelectionChange([{ id: 'c1' }, { id: 'c2' }]);
    await handleBatchDelete();

    // 全部失败应显示 error
    expect(ElMessage.error).toHaveBeenCalled();
    // 应显示失败详情
    expect(ElMessageBox.alert).toHaveBeenCalled();
  });

  it('未提供 batchDeleteApi 时不执行操作', async () => {
    const options = createTestOptions({ batchDeleteApi: undefined });
    const { handleSelectionChange, handleBatchDelete } = useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchDelete();

    expect(ElMessageBox.confirm).not.toHaveBeenCalled();
  });
});

describe('useBatchOperation - 网络错误和权限错误处理', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('网络错误时显示网络错误提示', async () => {
    const mockApproveApi = vi.fn().mockRejectedValue(new Error('Network Error'));
    const options = createTestOptions({ batchApproveApi: mockApproveApi });
    const { handleSelectionChange, handleBatchApprove, selectedRows } =
      useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchApprove();

    expect(ElMessage.error).toHaveBeenCalledWith('批量操作失败，请检查网络连接后重试');
    // 网络错误时保持选中状态
    expect(selectedRows.value.length).toBe(1);
  });

  it('权限错误（403）时显示权限不足提示并清空选中', async () => {
    const error403 = { response: { status: 403 } };
    const mockDeleteApi = vi.fn().mockRejectedValue(error403);
    const options = createTestOptions({ batchDeleteApi: mockDeleteApi });
    const { handleSelectionChange, handleBatchDelete, selectedRows } =
      useBatchOperation(options);

    handleSelectionChange([{ id: '1' }, { id: '2' }]);
    await handleBatchDelete();

    expect(ElMessage.error).toHaveBeenCalledWith('权限不足，无法执行此操作');
    // 权限错误时清空选中状态
    expect(selectedRows.value).toEqual([]);
  });

  it('批量拒绝时网络错误保持选中状态', async () => {
    const mockRejectApi = vi.fn().mockRejectedValue(new Error('timeout'));
    const options = createTestOptions({ batchRejectApi: mockRejectApi });
    const { handleSelectionChange, handleBatchReject, selectedRows } =
      useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchReject();

    expect(ElMessage.error).toHaveBeenCalledWith('批量操作失败，请检查网络连接后重试');
    expect(selectedRows.value.length).toBe(1);
  });

  it('批量拒绝时权限错误清空选中状态', async () => {
    const error403 = { response: { status: 403 } };
    const mockRejectApi = vi.fn().mockRejectedValue(error403);
    const options = createTestOptions({ batchRejectApi: mockRejectApi });
    const { handleSelectionChange, handleBatchReject, selectedRows } =
      useBatchOperation(options);

    handleSelectionChange([{ id: '1' }]);
    await handleBatchReject();

    expect(ElMessage.error).toHaveBeenCalledWith('权限不足，无法执行此操作');
    expect(selectedRows.value).toEqual([]);
  });
});
