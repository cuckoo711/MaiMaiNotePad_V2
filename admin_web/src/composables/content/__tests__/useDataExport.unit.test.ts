/**
 * 数据导出 composable 单元测试
 *
 * 测试 useDataExport 的导出对话框打开/关闭流程、格式选择、
 * 字段选择、导出选中/全部记录、以及导出失败错误处理
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// 模拟 element-plus，避免 CJS 兼容性问题
vi.mock('element-plus', () => ({
  ElMessageBox: {
    confirm: vi.fn().mockResolvedValue(true),
    alert: vi.fn().mockResolvedValue(true),
  },
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

import { useDataExport, type DataExportOptions, type ExportField } from '../useDataExport';
import { ElMessageBox, ElMessage } from 'element-plus';

/** 测试用可导出字段 */
const TEST_FIELDS: ExportField[] = [
  { key: 'name', label: '名称' },
  { key: 'author', label: '作者' },
  { key: 'status', label: '状态' },
];

/** 创建默认的测试选项 */
function createTestOptions(overrides?: Partial<DataExportOptions>): DataExportOptions {
  return {
    moduleName: 'knowledge-base',
    exportApi: vi.fn().mockResolvedValue(undefined),
    availableFields: TEST_FIELDS,
    ...overrides,
  };
}

describe('useDataExport - 导出对话框打开/关闭流程', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('初始状态下对话框不可见', () => {
    const options = createTestOptions();
    const { exportDialogVisible } = useDataExport(options);

    expect(exportDialogVisible.value).toBe(false);
  });

  it('openExportDialog 打开对话框', () => {
    const options = createTestOptions();
    const { exportDialogVisible, openExportDialog } = useDataExport(options);

    openExportDialog();

    expect(exportDialogVisible.value).toBe(true);
  });

  it('openExportDialog 重置表单为默认值', () => {
    const options = createTestOptions();
    const { exportForm, openExportDialog } = useDataExport(options);

    // 修改表单
    exportForm.value.format = 'csv';
    exportForm.value.fields = ['name'];

    // 重新打开对话框应重置
    openExportDialog();

    expect(exportForm.value.format).toBe('excel');
    expect(exportForm.value.fields).toEqual(['name', 'author', 'status']);
  });

  it('导出成功后关闭对话框', async () => {
    const options = createTestOptions();
    const { exportDialogVisible, openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    expect(exportDialogVisible.value).toBe(true);

    await handleExport();

    expect(exportDialogVisible.value).toBe(false);
  });
});

describe('useDataExport - 格式选择（Excel/CSV）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('默认导出格式为 excel', () => {
    const options = createTestOptions();
    const { exportForm, openExportDialog } = useDataExport(options);

    openExportDialog();

    expect(exportForm.value.format).toBe('excel');
  });

  it('可以切换导出格式为 csv 并正确传递给 API', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);
    const options = createTestOptions({ exportApi: mockExportApi });
    const { exportForm, openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    exportForm.value.format = 'csv';

    await handleExport();

    expect(mockExportApi).toHaveBeenCalledWith(
      expect.objectContaining({ format: 'csv' })
    );
  });

  it('excel 格式正确传递给 API', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);
    const options = createTestOptions({ exportApi: mockExportApi });
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();

    await handleExport();

    expect(mockExportApi).toHaveBeenCalledWith(
      expect.objectContaining({ format: 'excel' })
    );
  });
});

describe('useDataExport - 字段选择', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('默认选中所有可导出字段', () => {
    const options = createTestOptions();
    const { exportForm, openExportDialog } = useDataExport(options);

    openExportDialog();

    expect(exportForm.value.fields).toEqual(['name', 'author', 'status']);
  });

  it('可以选择部分字段并正确传递给 API', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);
    const options = createTestOptions({ exportApi: mockExportApi });
    const { exportForm, openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    exportForm.value.fields = ['name', 'status'];

    await handleExport();

    expect(mockExportApi).toHaveBeenCalledWith(
      expect.objectContaining({ fields: ['name', 'status'] })
    );
  });

  it('重新打开对话框时字段重置为全选', () => {
    const options = createTestOptions();
    const { exportForm, openExportDialog } = useDataExport(options);

    openExportDialog();
    exportForm.value.fields = ['name'];

    // 重新打开
    openExportDialog();

    expect(exportForm.value.fields).toEqual(['name', 'author', 'status']);
  });
});

describe('useDataExport - 导出选中记录 vs 导出全部记录', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('无选中记录时 exportForm 不包含 ids', () => {
    const options = createTestOptions();
    const { exportForm, openExportDialog } = useDataExport(options);

    openExportDialog();

    expect(exportForm.value.ids).toBeUndefined();
  });

  it('传入空数组时 exportForm 不包含 ids', () => {
    const options = createTestOptions();
    const { exportForm, openExportDialog } = useDataExport(options);

    openExportDialog([]);

    expect(exportForm.value.ids).toBeUndefined();
  });

  it('传入选中 ID 时 exportForm 包含 ids', () => {
    const options = createTestOptions();
    const { exportForm, openExportDialog } = useDataExport(options);

    openExportDialog(['id1', 'id2', 'id3']);

    expect(exportForm.value.ids).toEqual(['id1', 'id2', 'id3']);
  });

  it('导出选中记录时 API 接收到 ids 参数', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);
    const options = createTestOptions({ exportApi: mockExportApi });
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog(['sel1', 'sel2']);

    await handleExport();

    expect(mockExportApi).toHaveBeenCalledWith(
      expect.objectContaining({ ids: ['sel1', 'sel2'] })
    );
  });

  it('导出全部记录时 API 不接收 ids 参数', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);
    const options = createTestOptions({ exportApi: mockExportApi });
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();

    await handleExport();

    const callArgs = mockExportApi.mock.calls[0][0];
    expect(callArgs.ids).toBeUndefined();
  });

  it('重新打开对话框时清除之前的选中 ID', () => {
    const options = createTestOptions();
    const { exportForm, openExportDialog } = useDataExport(options);

    // 先带选中 ID 打开
    openExportDialog(['id1']);
    expect(exportForm.value.ids).toEqual(['id1']);

    // 不带选中 ID 重新打开
    openExportDialog();
    expect(exportForm.value.ids).toBeUndefined();
  });
});

describe('useDataExport - 大数据量提示', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('数据量超过 5000 时显示确认对话框', async () => {
    const options = createTestOptions();
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    await handleExport(6000);

    expect(ElMessageBox.confirm).toHaveBeenCalledOnce();
  });

  it('数据量不超过 5000 时不显示确认对话框', async () => {
    const options = createTestOptions();
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    await handleExport(5000);

    expect(ElMessageBox.confirm).not.toHaveBeenCalled();
  });

  it('用户取消大数据量确认时不执行导出', async () => {
    vi.mocked(ElMessageBox.confirm).mockRejectedValueOnce('cancel');
    const mockExportApi = vi.fn();
    const options = createTestOptions({ exportApi: mockExportApi });
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    await handleExport(10000);

    expect(mockExportApi).not.toHaveBeenCalled();
  });

  it('用户确认大数据量后继续执行导出', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);
    const options = createTestOptions({ exportApi: mockExportApi });
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    await handleExport(8000);

    expect(ElMessageBox.confirm).toHaveBeenCalledOnce();
    expect(mockExportApi).toHaveBeenCalledOnce();
  });

  it('不传 totalCount 时不显示确认对话框', async () => {
    const options = createTestOptions();
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    await handleExport();

    expect(ElMessageBox.confirm).not.toHaveBeenCalled();
  });
});

describe('useDataExport - 导出失败错误处理', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('导出 API 失败时显示错误消息', async () => {
    const mockExportApi = vi.fn().mockRejectedValue(new Error('服务器内部错误'));
    const options = createTestOptions({ exportApi: mockExportApi });
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    await handleExport();

    expect(ElMessage.error).toHaveBeenCalledWith('导出失败：服务器内部错误');
  });

  it('导出失败时对话框保持打开状态', async () => {
    const mockExportApi = vi.fn().mockRejectedValue(new Error('网络错误'));
    const options = createTestOptions({ exportApi: mockExportApi });
    const { exportDialogVisible, openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    expect(exportDialogVisible.value).toBe(true);

    await handleExport();

    // 失败时对话框不关闭，用户可以重试
    expect(exportDialogVisible.value).toBe(true);
  });

  it('错误无 message 属性时显示"未知错误"', async () => {
    const mockExportApi = vi.fn().mockRejectedValue({});
    const options = createTestOptions({ exportApi: mockExportApi });
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    await handleExport();

    expect(ElMessage.error).toHaveBeenCalledWith('导出失败：未知错误');
  });

  it('导出成功时显示成功消息', async () => {
    const options = createTestOptions();
    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    await handleExport();

    expect(ElMessage.success).toHaveBeenCalledWith('导出成功');
  });
});
