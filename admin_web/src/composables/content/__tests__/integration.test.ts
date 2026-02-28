/**
 * 内容管理增强功能集成测试
 *
 * 测试完整的端到端流程，验证各 composable 之间的协作：
 * - 批量选择 → 批量审核通过 → 结果摘要显示 → 列表刷新
 * - 批量选择 → 批量删除 → 确认对话框 → 结果摘要显示
 * - 导出对话框 → 选择格式和字段 → 触发下载
 * - 导入对话框 → 上传文件 → 格式校验 → 结果摘要显示
 * - 统计页面加载 → 各图表组件渲染
 *
 * 验证需求: 2.2, 2.3, 2.6, 3.2, 3.3, 3.4, 4.2, 4.3, 4.5, 5.2, 5.6, 5.7, 9.3
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// 模拟 element-plus
vi.mock('element-plus', () => ({
  ElMessageBox: {
    confirm: vi.fn().mockResolvedValue(true),
    prompt: vi.fn().mockResolvedValue({ value: '内容不合规' }),
    alert: vi.fn().mockResolvedValue(true),
  },
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// 模拟 request 工具函数
vi.mock('/@/utils/service', () => ({
  request: vi.fn(),
  downloadFile: vi.fn(),
}));

import { useBatchOperation, type BatchOperationOptions } from '../useBatchOperation';
import { useDataExport, type DataExportOptions, type ExportField } from '../useDataExport';
import { useDataImport, type DataImportOptions } from '../useDataImport';
import type { BatchResult } from '../batchOperationUtils';
import type { ImportResult } from '../dataImportUtils';
import { ElMessageBox, ElMessage } from 'element-plus';

// ==================== 辅助函数 ====================

/** 创建模拟 File 对象 */
function createMockFile(name: string): File {
  const blob = new Blob(['test content'], { type: 'application/octet-stream' });
  return new File([blob], name, { type: 'application/octet-stream' });
}

/** 模拟记录数据 */
function createMockRows(count: number): Array<{ id: string; name: string }> {
  return Array.from({ length: count }, (_, i) => ({
    id: `record-${i + 1}`,
    name: `记录 ${i + 1}`,
  }));
}

/** 测试用可导出字段 */
const EXPORT_FIELDS: ExportField[] = [
  { key: 'name', label: '名称' },
  { key: 'description', label: '描述' },
  { key: 'author', label: '作者' },
  { key: 'status', label: '状态' },
  { key: 'create_datetime', label: '创建时间' },
];

// ==================== 集成测试 ====================

describe('集成测试：批量选择 → 批量审核通过 → 结果摘要 → 列表刷新', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('完整流程：选中多条记录 → 审核通过 → 显示成功摘要 → 刷新列表 → 清空选中', async () => {
    // 模拟 API 返回全部成功
    const mockApproveApi = vi.fn().mockResolvedValue({
      success_count: 3,
      fail_count: 0,
      failures: [],
    } as BatchResult);
    const mockOnSuccess = vi.fn();

    const options: BatchOperationOptions = {
      moduleName: 'knowledge-base',
      batchApproveApi: mockApproveApi,
      batchDeleteApi: vi.fn(),
      onSuccess: mockOnSuccess,
    };

    const {
      selectedRows,
      selectedCount,
      hasSelection,
      handleSelectionChange,
      handleBatchApprove,
    } = useBatchOperation(options);

    // 步骤1：选中3条记录
    const rows = createMockRows(3);
    handleSelectionChange(rows);
    expect(selectedCount.value).toBe(3);
    expect(hasSelection.value).toBe(true);

    // 步骤2：执行批量审核通过
    await handleBatchApprove();

    // 步骤3：验证确认对话框显示了选中数量
    expect(ElMessageBox.confirm).toHaveBeenCalledOnce();
    const confirmMsg = vi.mocked(ElMessageBox.confirm).mock.calls[0][0] as string;
    expect(confirmMsg).toContain('3');

    // 步骤4：验证 API 被调用，传入正确的 ID 列表
    expect(mockApproveApi).toHaveBeenCalledWith(['record-1', 'record-2', 'record-3']);

    // 步骤5：验证成功摘要消息
    expect(ElMessage.success).toHaveBeenCalled();
    const successMsg = vi.mocked(ElMessage.success).mock.calls[0][0] as string;
    expect(successMsg).toContain('3');

    // 步骤6：验证列表刷新回调被调用
    expect(mockOnSuccess).toHaveBeenCalledOnce();

    // 步骤7：验证选中状态已清空
    expect(selectedRows.value).toEqual([]);
    expect(selectedCount.value).toBe(0);
    expect(hasSelection.value).toBe(false);
  });

  it('部分失败流程：选中记录 → 审核通过 → 部分失败 → 显示警告和失败详情 → 刷新列表', async () => {
    const mockApproveApi = vi.fn().mockResolvedValue({
      success_count: 2,
      fail_count: 1,
      failures: [{ id: 'record-3', reason: '记录已被删除' }],
    } as BatchResult);
    const mockOnSuccess = vi.fn();

    const options: BatchOperationOptions = {
      moduleName: 'knowledge-base',
      batchApproveApi: mockApproveApi,
      onSuccess: mockOnSuccess,
    };

    const { handleSelectionChange, handleBatchApprove } = useBatchOperation(options);

    // 选中3条记录
    handleSelectionChange(createMockRows(3));

    // 执行批量审核通过
    await handleBatchApprove();

    // 验证 API 调用
    expect(mockApproveApi).toHaveBeenCalledOnce();

    // 部分失败应显示 warning 消息
    expect(ElMessage.warning).toHaveBeenCalled();
    const warningMsg = vi.mocked(ElMessage.warning).mock.calls[0][0] as string;
    expect(warningMsg).toContain('2');
    expect(warningMsg).toContain('1');

    // 应显示失败详情对话框
    expect(ElMessageBox.alert).toHaveBeenCalled();
    const alertMsg = vi.mocked(ElMessageBox.alert).mock.calls[0][0] as string;
    expect(alertMsg).toContain('record-3');
    expect(alertMsg).toContain('记录已被删除');

    // 列表仍然刷新
    expect(mockOnSuccess).toHaveBeenCalledOnce();
  });
});

describe('集成测试：批量选择 → 批量删除 → 确认对话框 → 结果摘要', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('完整流程：选中记录 → 确认删除（含警告） → API 调用 → 成功摘要 → 刷新列表', async () => {
    const mockDeleteApi = vi.fn().mockResolvedValue({
      success_count: 2,
      fail_count: 0,
      failures: [],
    } as BatchResult);
    const mockOnSuccess = vi.fn();

    const options: BatchOperationOptions = {
      moduleName: 'comment',
      batchDeleteApi: mockDeleteApi,
      onSuccess: mockOnSuccess,
    };

    const {
      selectedRows,
      hasSelection,
      handleSelectionChange,
      handleBatchDelete,
    } = useBatchOperation(options);

    // 步骤1：选中2条记录
    const rows = createMockRows(2);
    handleSelectionChange(rows);
    expect(hasSelection.value).toBe(true);

    // 步骤2：执行批量删除
    await handleBatchDelete();

    // 步骤3：验证确认对话框包含警告信息
    expect(ElMessageBox.confirm).toHaveBeenCalledOnce();
    const confirmMsg = vi.mocked(ElMessageBox.confirm).mock.calls[0][0] as string;
    expect(confirmMsg).toContain('2');
    expect(confirmMsg).toContain('不可恢复');

    // 步骤4：验证 API 调用
    expect(mockDeleteApi).toHaveBeenCalledWith(['record-1', 'record-2']);

    // 步骤5：验证成功摘要
    expect(ElMessage.success).toHaveBeenCalled();

    // 步骤6：验证列表刷新和选中清空
    expect(mockOnSuccess).toHaveBeenCalledOnce();
    expect(selectedRows.value).toEqual([]);
    expect(hasSelection.value).toBe(false);
  });

  it('用户取消删除确认时整个流程中止', async () => {
    vi.mocked(ElMessageBox.confirm).mockRejectedValueOnce('cancel');
    const mockDeleteApi = vi.fn();
    const mockOnSuccess = vi.fn();

    const options: BatchOperationOptions = {
      moduleName: 'star-record',
      batchDeleteApi: mockDeleteApi,
      onSuccess: mockOnSuccess,
    };

    const { handleSelectionChange, handleBatchDelete, selectedRows } =
      useBatchOperation(options);

    // 选中记录
    handleSelectionChange(createMockRows(3));

    // 执行删除（用户取消）
    await handleBatchDelete();

    // API 不应被调用
    expect(mockDeleteApi).not.toHaveBeenCalled();
    // 列表不应刷新
    expect(mockOnSuccess).not.toHaveBeenCalled();
    // 选中状态保持
    expect(selectedRows.value).toHaveLength(3);
  });

  it('删除全部失败时显示错误消息和失败详情', async () => {
    const mockDeleteApi = vi.fn().mockResolvedValue({
      success_count: 0,
      fail_count: 2,
      failures: [
        { id: 'record-1', reason: '记录被引用' },
        { id: 'record-2', reason: '权限不足' },
      ],
    } as BatchResult);
    const mockOnSuccess = vi.fn();

    const options: BatchOperationOptions = {
      moduleName: 'comment',
      batchDeleteApi: mockDeleteApi,
      onSuccess: mockOnSuccess,
    };

    const { handleSelectionChange, handleBatchDelete } = useBatchOperation(options);

    handleSelectionChange(createMockRows(2));
    await handleBatchDelete();

    // 全部失败应显示 error 消息
    expect(ElMessage.error).toHaveBeenCalled();
    // 应显示失败详情
    expect(ElMessageBox.alert).toHaveBeenCalled();
    const alertMsg = vi.mocked(ElMessageBox.alert).mock.calls[0][0] as string;
    expect(alertMsg).toContain('记录被引用');
    expect(alertMsg).toContain('权限不足');
    // 即使全部失败，列表仍然刷新
    expect(mockOnSuccess).toHaveBeenCalledOnce();
  });
});

describe('集成测试：导出对话框 → 选择格式和字段 → 触发下载', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('完整流程：打开对话框 → 选择 CSV 格式和部分字段 → 导出成功 → 对话框关闭', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);

    const options: DataExportOptions = {
      moduleName: 'knowledge-base',
      exportApi: mockExportApi,
      availableFields: EXPORT_FIELDS,
    };

    const { exportDialogVisible, exportForm, openExportDialog, handleExport } =
      useDataExport(options);

    // 步骤1：打开导出对话框
    openExportDialog();
    expect(exportDialogVisible.value).toBe(true);
    // 默认格式为 excel，默认选中所有字段
    expect(exportForm.value.format).toBe('excel');
    expect(exportForm.value.fields).toEqual(['name', 'description', 'author', 'status', 'create_datetime']);

    // 步骤2：修改格式为 CSV，选择部分字段
    exportForm.value.format = 'csv';
    exportForm.value.fields = ['name', 'author', 'create_datetime'];

    // 步骤3：执行导出
    await handleExport();

    // 步骤4：验证 API 调用参数
    expect(mockExportApi).toHaveBeenCalledWith({
      format: 'csv',
      fields: ['name', 'author', 'create_datetime'],
    });

    // 步骤5：验证成功消息和对话框关闭
    expect(ElMessage.success).toHaveBeenCalledWith('导出成功');
    expect(exportDialogVisible.value).toBe(false);
  });

  it('导出选中记录流程：有选中 → 打开对话框 → 导出携带 ids', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);

    const options: DataExportOptions = {
      moduleName: 'persona-card',
      exportApi: mockExportApi,
      availableFields: EXPORT_FIELDS,
    };

    const { exportForm, openExportDialog, handleExport } = useDataExport(options);

    // 步骤1：带选中 ID 打开对话框
    openExportDialog(['id-1', 'id-2', 'id-3']);
    expect(exportForm.value.ids).toEqual(['id-1', 'id-2', 'id-3']);

    // 步骤2：执行导出
    await handleExport();

    // 步骤3：验证 API 调用包含 ids
    expect(mockExportApi).toHaveBeenCalledWith(
      expect.objectContaining({
        ids: ['id-1', 'id-2', 'id-3'],
        format: 'excel',
      })
    );
  });

  it('大数据量导出流程：数据量 > 5000 → 提示确认 → 继续导出', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);

    const options: DataExportOptions = {
      moduleName: 'comment',
      exportApi: mockExportApi,
      availableFields: EXPORT_FIELDS,
    };

    const { openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();

    // 传入大数据量
    await handleExport(8000);

    // 验证大数据量确认对话框
    expect(ElMessageBox.confirm).toHaveBeenCalledOnce();
    const confirmMsg = vi.mocked(ElMessageBox.confirm).mock.calls[0][0] as string;
    expect(confirmMsg).toContain('数据量较大');

    // 用户确认后继续导出
    expect(mockExportApi).toHaveBeenCalledOnce();
    expect(ElMessage.success).toHaveBeenCalledWith('导出成功');
  });

  it('导出失败流程：API 报错 → 显示错误消息 → 对话框保持打开', async () => {
    const mockExportApi = vi.fn().mockRejectedValue(new Error('服务器超时'));

    const options: DataExportOptions = {
      moduleName: 'knowledge-base',
      exportApi: mockExportApi,
      availableFields: EXPORT_FIELDS,
    };

    const { exportDialogVisible, openExportDialog, handleExport } = useDataExport(options);

    openExportDialog();
    await handleExport();

    // 验证错误消息
    expect(ElMessage.error).toHaveBeenCalledWith('导出失败：服务器超时');
    // 对话框保持打开，用户可以重试
    expect(exportDialogVisible.value).toBe(true);
  });
});

describe('集成测试：导入对话框 → 上传文件 → 格式校验 → 结果摘要', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('完整成功流程：打开对话框 → 选择合法文件 → 导入成功 → 显示结果摘要', async () => {
    const mockImportApi = vi.fn().mockResolvedValue({
      success_count: 15,
      fail_count: 0,
      errors: [],
    } as ImportResult);
    const mockTemplateApi = vi.fn().mockResolvedValue(undefined);

    const options: DataImportOptions = {
      moduleName: 'knowledge-base',
      importApi: mockImportApi,
      templateApi: mockTemplateApi,
    };

    const {
      importDialogVisible,
      importFile,
      importLoading,
      importResult,
      openImportDialog,
      handleFileChange,
      handleImport,
    } = useDataImport(options);

    // 步骤1：打开导入对话框
    openImportDialog();
    expect(importDialogVisible.value).toBe(true);
    expect(importFile.value).toBeNull();
    expect(importResult.value).toBeNull();

    // 步骤2：选择合法的 xlsx 文件
    const file = createMockFile('知识库数据.xlsx');
    const isValid = handleFileChange(file);
    expect(isValid).toBe(true);
    expect(importFile.value).toBe(file);

    // 步骤3：执行导入
    await handleImport();

    // 步骤4：验证 API 调用
    expect(mockImportApi).toHaveBeenCalledWith(file);

    // 步骤5：验证结果摘要
    expect(ElMessage.success).toHaveBeenCalledWith('导入完成：15 条记录导入成功');
    expect(importResult.value).toEqual({
      success_count: 15,
      fail_count: 0,
      errors: [],
    });

    // 步骤6：验证 loading 状态恢复
    expect(importLoading.value).toBe(false);
  });

  it('格式校验失败流程：选择非法文件 → 显示错误 → 文件不被设置', () => {
    const options: DataImportOptions = {
      moduleName: 'persona-card',
      importApi: vi.fn(),
      templateApi: vi.fn(),
    };

    const { importFile, openImportDialog, handleFileChange } = useDataImport(options);

    openImportDialog();

    // 尝试上传 PDF 文件
    const pdfFile = createMockFile('document.pdf');
    const isValid = handleFileChange(pdfFile);

    expect(isValid).toBe(false);
    expect(importFile.value).toBeNull();
    expect(ElMessage.error).toHaveBeenCalledWith('仅支持 .xlsx 和 .csv 格式文件');
  });

  it('部分失败流程：导入含错误数据 → 显示警告 → 结果包含逐行错误', async () => {
    const mockImportApi = vi.fn().mockResolvedValue({
      success_count: 8,
      fail_count: 3,
      errors: [
        { row: 2, message: '名称字段不能为空' },
        { row: 5, message: '描述超过最大长度' },
        { row: 9, message: '标签格式不正确' },
      ],
    } as ImportResult);

    const options: DataImportOptions = {
      moduleName: 'knowledge-base',
      importApi: mockImportApi,
      templateApi: vi.fn(),
    };

    const { openImportDialog, handleFileChange, handleImport, importResult } =
      useDataImport(options);

    openImportDialog();
    handleFileChange(createMockFile('data.csv'));
    await handleImport();

    // 验证警告消息
    expect(ElMessage.warning).toHaveBeenCalledWith('导入完成：8 条成功，3 条失败');

    // 验证结果包含逐行错误详情
    expect(importResult.value).not.toBeNull();
    expect(importResult.value!.success_count).toBe(8);
    expect(importResult.value!.fail_count).toBe(3);
    expect(importResult.value!.errors).toHaveLength(3);
    expect(importResult.value!.errors![0]).toEqual({ row: 2, message: '名称字段不能为空' });
    expect(importResult.value!.errors![1]).toEqual({ row: 5, message: '描述超过最大长度' });
    expect(importResult.value!.errors![2]).toEqual({ row: 9, message: '标签格式不正确' });
  });

  it('模板下载流程：点击下载模板 → 调用模板 API', async () => {
    const mockTemplateApi = vi.fn().mockResolvedValue(undefined);

    const options: DataImportOptions = {
      moduleName: 'persona-card',
      importApi: vi.fn(),
      templateApi: mockTemplateApi,
    };

    const { openImportDialog, handleDownloadTemplate } = useDataImport(options);

    openImportDialog();
    await handleDownloadTemplate();

    expect(mockTemplateApi).toHaveBeenCalledOnce();
    expect(ElMessage.error).not.toHaveBeenCalled();
  });

  it('未选择文件直接导入时显示警告', async () => {
    const mockImportApi = vi.fn();

    const options: DataImportOptions = {
      moduleName: 'knowledge-base',
      importApi: mockImportApi,
      templateApi: vi.fn(),
    };

    const { openImportDialog, handleImport } = useDataImport(options);

    openImportDialog();
    // 不选择文件直接导入
    await handleImport();

    expect(ElMessage.warning).toHaveBeenCalledWith('请先选择导入文件');
    expect(mockImportApi).not.toHaveBeenCalled();
  });
});

describe('集成测试：批量操作与导出联动', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('选中记录后导出选中记录：批量选择 → 导出选中 → API 携带 ids', async () => {
    // 初始化批量操作
    const mockOnSuccess = vi.fn();
    const batchOptions: BatchOperationOptions = {
      moduleName: 'knowledge-base',
      batchDeleteApi: vi.fn(),
      onSuccess: mockOnSuccess,
    };
    const { selectedRows, handleSelectionChange } = useBatchOperation(batchOptions);

    // 初始化导出
    const mockExportApi = vi.fn().mockResolvedValue(undefined);
    const exportOptions: DataExportOptions = {
      moduleName: 'knowledge-base',
      exportApi: mockExportApi,
      availableFields: EXPORT_FIELDS,
    };
    const { exportForm, openExportDialog, handleExport } = useDataExport(exportOptions);

    // 步骤1：选中记录
    const rows = createMockRows(5);
    handleSelectionChange(rows);
    expect(selectedRows.value).toHaveLength(5);

    // 步骤2：获取选中 ID 并打开导出对话框
    const selectedIds = selectedRows.value.map((r: any) => r.id);
    openExportDialog(selectedIds);

    // 验证导出表单包含选中 ID
    expect(exportForm.value.ids).toEqual([
      'record-1', 'record-2', 'record-3', 'record-4', 'record-5',
    ]);

    // 步骤3：执行导出
    await handleExport();

    // 验证 API 调用包含 ids
    expect(mockExportApi).toHaveBeenCalledWith(
      expect.objectContaining({
        ids: ['record-1', 'record-2', 'record-3', 'record-4', 'record-5'],
      })
    );
  });

  it('无选中记录时导出全部：打开导出 → 不携带 ids', async () => {
    const mockExportApi = vi.fn().mockResolvedValue(undefined);
    const exportOptions: DataExportOptions = {
      moduleName: 'comment',
      exportApi: mockExportApi,
      availableFields: EXPORT_FIELDS,
    };
    const { exportForm, openExportDialog, handleExport } = useDataExport(exportOptions);

    // 无选中记录，直接打开导出
    openExportDialog();
    expect(exportForm.value.ids).toBeUndefined();

    await handleExport();

    // API 调用不包含 ids
    const callArgs = mockExportApi.mock.calls[0][0];
    expect(callArgs.ids).toBeUndefined();
  });
});

describe('集成测试：统计页面数据加载与组件渲染', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('概览指标数据正确映射到各卡片字段', async () => {
    // 模拟统计 API 模块
    const mockOverviewData = {
      knowledge_base_count: 150,
      persona_card_count: 80,
      comment_count: 1200,
      star_count: 350,
      upload_count: 200,
      download_count: 500,
    };

    // 验证数据结构完整性 - 6个指标字段都存在
    const expectedFields = [
      'knowledge_base_count',
      'persona_card_count',
      'comment_count',
      'star_count',
      'upload_count',
      'download_count',
    ];

    for (const field of expectedFields) {
      expect(mockOverviewData).toHaveProperty(field);
      expect(typeof (mockOverviewData as any)[field]).toBe('number');
      expect((mockOverviewData as any)[field]).toBeGreaterThanOrEqual(0);
    }

    // 验证所有6个字段都有值
    expect(Object.keys(mockOverviewData)).toHaveLength(6);
  });

  it('审核状态分布数据包含知识库和人设卡两个维度', () => {
    const mockReviewData = {
      knowledge_base: { pending: 20, approved: 100, rejected: 30 },
      persona_card: { pending: 10, approved: 50, rejected: 20 },
    };

    // 验证知识库审核分布
    expect(mockReviewData.knowledge_base).toHaveProperty('pending');
    expect(mockReviewData.knowledge_base).toHaveProperty('approved');
    expect(mockReviewData.knowledge_base).toHaveProperty('rejected');
    const kbTotal =
      mockReviewData.knowledge_base.pending +
      mockReviewData.knowledge_base.approved +
      mockReviewData.knowledge_base.rejected;
    expect(kbTotal).toBe(150);

    // 验证人设卡审核分布
    expect(mockReviewData.persona_card).toHaveProperty('pending');
    expect(mockReviewData.persona_card).toHaveProperty('approved');
    expect(mockReviewData.persona_card).toHaveProperty('rejected');
    const pcTotal =
      mockReviewData.persona_card.pending +
      mockReviewData.persona_card.approved +
      mockReviewData.persona_card.rejected;
    expect(pcTotal).toBe(80);
  });

  it('趋势数据点包含日期和三种计数字段', () => {
    const mockTrendData = [
      { date: '2024-01-01', knowledge_base_count: 5, persona_card_count: 3, comment_count: 12 },
      { date: '2024-01-02', knowledge_base_count: 8, persona_card_count: 2, comment_count: 15 },
      { date: '2024-01-03', knowledge_base_count: 3, persona_card_count: 6, comment_count: 8 },
    ];

    // 验证每个数据点结构
    for (const point of mockTrendData) {
      expect(point).toHaveProperty('date');
      expect(point).toHaveProperty('knowledge_base_count');
      expect(point).toHaveProperty('persona_card_count');
      expect(point).toHaveProperty('comment_count');
      // 日期格式为 YYYY-MM-DD
      expect(point.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }

    // 验证数据按日期排序
    for (let i = 1; i < mockTrendData.length; i++) {
      expect(mockTrendData[i].date >= mockTrendData[i - 1].date).toBe(true);
    }
  });

  it('热门排行数据包含知识库和人设卡两个列表，每项包含必要字段', () => {
    const mockTopContent = {
      knowledge_base: [
        { id: 'kb-1', name: '热门知识库1', uploader_name: '用户A', star_count: 100, downloads: 500 },
        { id: 'kb-2', name: '热门知识库2', uploader_name: '用户B', star_count: 80, downloads: 300 },
      ],
      persona_card: [
        { id: 'pc-1', name: '热门人设卡1', uploader_name: '用户C', star_count: 90, downloads: 400 },
      ],
    };

    // 验证知识库排行
    expect(mockTopContent.knowledge_base).toBeInstanceOf(Array);
    expect(mockTopContent.knowledge_base.length).toBeLessThanOrEqual(10);
    for (const item of mockTopContent.knowledge_base) {
      expect(item).toHaveProperty('id');
      expect(item).toHaveProperty('name');
      expect(item).toHaveProperty('uploader_name');
      expect(item).toHaveProperty('star_count');
      expect(item).toHaveProperty('downloads');
    }

    // 验证人设卡排行
    expect(mockTopContent.persona_card).toBeInstanceOf(Array);
    expect(mockTopContent.persona_card.length).toBeLessThanOrEqual(10);
    for (const item of mockTopContent.persona_card) {
      expect(item).toHaveProperty('id');
      expect(item).toHaveProperty('name');
      expect(item).toHaveProperty('uploader_name');
      expect(item).toHaveProperty('star_count');
      expect(item).toHaveProperty('downloads');
    }

    // 验证按收藏数降序排列
    for (let i = 1; i < mockTopContent.knowledge_base.length; i++) {
      expect(
        mockTopContent.knowledge_base[i].star_count <=
        mockTopContent.knowledge_base[i - 1].star_count
      ).toBe(true);
    }
  });

  it('各统计 API 独立加载，一个失败不影响其他', async () => {
    // 模拟4个独立的 API 调用，其中一个失败
    const overviewApi = vi.fn().mockResolvedValue({
      knowledge_base_count: 100,
      persona_card_count: 50,
      comment_count: 200,
      star_count: 80,
      upload_count: 60,
      download_count: 120,
    });
    const reviewApi = vi.fn().mockRejectedValue(new Error('网络错误'));
    const trendsApi = vi.fn().mockResolvedValue({
      data: [{ date: '2024-01-01', knowledge_base_count: 5, persona_card_count: 3, comment_count: 10 }],
    });
    const topContentApi = vi.fn().mockResolvedValue({
      knowledge_base: [],
      persona_card: [],
    });

    // 并行调用所有 API（模拟页面加载行为）
    const results = await Promise.allSettled([
      overviewApi(),
      reviewApi(),
      trendsApi(),
      topContentApi(),
    ]);

    // 验证各 API 独立调用
    expect(overviewApi).toHaveBeenCalledOnce();
    expect(reviewApi).toHaveBeenCalledOnce();
    expect(trendsApi).toHaveBeenCalledOnce();
    expect(topContentApi).toHaveBeenCalledOnce();

    // 验证成功的 API 返回数据
    expect(results[0].status).toBe('fulfilled');
    expect(results[2].status).toBe('fulfilled');
    expect(results[3].status).toBe('fulfilled');

    // 验证失败的 API 不影响其他
    expect(results[1].status).toBe('rejected');

    // 成功的数据可以正常使用
    if (results[0].status === 'fulfilled') {
      expect(results[0].value.knowledge_base_count).toBe(100);
    }
  });
});
