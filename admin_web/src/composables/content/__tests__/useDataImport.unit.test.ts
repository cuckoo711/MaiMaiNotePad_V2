/**
 * 数据导入 composable 单元测试
 *
 * 测试 useDataImport 的文件格式验证、导入对话框打开/关闭流程、
 * 模板下载流程、导入结果摘要显示、以及导入失败错误处理
 *
 * 验证需求: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// 模拟 element-plus，避免 CJS 兼容性问题
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

import { useDataImport, type DataImportOptions, type ImportResult } from '../useDataImport';
import { validateFileFormat, parseImportResult } from '../dataImportUtils';
import { ElMessage } from 'element-plus';

/** 创建默认的测试选项 */
function createTestOptions(overrides?: Partial<DataImportOptions>): DataImportOptions {
  return {
    moduleName: 'knowledge-base',
    importApi: vi.fn().mockResolvedValue({
      success_count: 5,
      fail_count: 0,
      errors: [],
    }),
    templateApi: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

/** 创建模拟 File 对象 */
function createMockFile(name: string, size = 1024): File {
  const blob = new Blob(['test'], { type: 'application/octet-stream' });
  return new File([blob], name, { type: 'application/octet-stream' });
}

describe('useDataImport - 文件格式验证 - 需求 5.4, 5.5', () => {
  it('.xlsx 文件应该通过验证', () => {
    expect(validateFileFormat('data.xlsx')).toBe(true);
  });

  it('.csv 文件应该通过验证', () => {
    expect(validateFileFormat('data.csv')).toBe(true);
  });

  it('.XLSX 大写扩展名应该通过验证（不区分大小写）', () => {
    expect(validateFileFormat('DATA.XLSX')).toBe(true);
  });

  it('.CSV 大写扩展名应该通过验证（不区分大小写）', () => {
    expect(validateFileFormat('report.CSV')).toBe(true);
  });

  it('.Xlsx 混合大小写应该通过验证', () => {
    expect(validateFileFormat('file.Xlsx')).toBe(true);
  });

  it('.txt 文件应该被拒绝', () => {
    expect(validateFileFormat('notes.txt')).toBe(false);
  });

  it('.pdf 文件应该被拒绝', () => {
    expect(validateFileFormat('document.pdf')).toBe(false);
  });

  it('.xls 文件应该被拒绝（仅支持 .xlsx）', () => {
    expect(validateFileFormat('old_format.xls')).toBe(false);
  });

  it('.json 文件应该被拒绝', () => {
    expect(validateFileFormat('config.json')).toBe(false);
  });

  it('无扩展名文件应该被拒绝', () => {
    expect(validateFileFormat('noextension')).toBe(false);
  });

  it('handleFileChange 对合法文件返回 true 并设置 importFile', () => {
    const options = createTestOptions();
    const { importFile, handleFileChange } = useDataImport(options);

    const file = createMockFile('data.xlsx');
    const result = handleFileChange(file);

    expect(result).toBe(true);
    expect(importFile.value).toBe(file);
  });

  it('handleFileChange 对非法文件返回 false 并显示错误提示', () => {
    const options = createTestOptions();
    const { importFile, handleFileChange } = useDataImport(options);

    const file = createMockFile('document.pdf');
    const result = handleFileChange(file);

    expect(result).toBe(false);
    expect(importFile.value).toBeNull();
    expect(ElMessage.error).toHaveBeenCalledWith('仅支持 .xlsx 和 .csv 格式文件');
  });
});

describe('useDataImport - 导入对话框打开/关闭流程 - 需求 5.2', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('初始状态下对话框不可见', () => {
    const options = createTestOptions();
    const { importDialogVisible } = useDataImport(options);

    expect(importDialogVisible.value).toBe(false);
  });

  it('openImportDialog 打开对话框', () => {
    const options = createTestOptions();
    const { importDialogVisible, openImportDialog } = useDataImport(options);

    openImportDialog();

    expect(importDialogVisible.value).toBe(true);
  });

  it('openImportDialog 重置文件和结果状态', () => {
    const options = createTestOptions();
    const { importFile, importResult, importLoading, openImportDialog, handleFileChange } =
      useDataImport(options);

    // 先设置一些状态
    handleFileChange(createMockFile('data.xlsx'));
    expect(importFile.value).not.toBeNull();

    // 重新打开对话框应重置
    openImportDialog();

    expect(importFile.value).toBeNull();
    expect(importResult.value).toBeNull();
    expect(importLoading.value).toBe(false);
  });

  it('初始状态下 importLoading 为 false', () => {
    const options = createTestOptions();
    const { importLoading } = useDataImport(options);

    expect(importLoading.value).toBe(false);
  });

  it('初始状态下 importFile 为 null', () => {
    const options = createTestOptions();
    const { importFile } = useDataImport(options);

    expect(importFile.value).toBeNull();
  });

  it('初始状态下 importResult 为 null', () => {
    const options = createTestOptions();
    const { importResult } = useDataImport(options);

    expect(importResult.value).toBeNull();
  });
});

describe('useDataImport - 模板下载流程 - 需求 5.3', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('handleDownloadTemplate 调用 templateApi', async () => {
    const mockTemplateApi = vi.fn().mockResolvedValue(undefined);
    const options = createTestOptions({ templateApi: mockTemplateApi });
    const { handleDownloadTemplate } = useDataImport(options);

    await handleDownloadTemplate();

    expect(mockTemplateApi).toHaveBeenCalledOnce();
  });

  it('模板下载失败时显示错误提示', async () => {
    const mockTemplateApi = vi.fn().mockRejectedValue(new Error('网络错误'));
    const options = createTestOptions({ templateApi: mockTemplateApi });
    const { handleDownloadTemplate } = useDataImport(options);

    await handleDownloadTemplate();

    expect(ElMessage.error).toHaveBeenCalledWith('模板下载失败，请稍后重试');
  });

  it('模板下载成功时不显示错误提示', async () => {
    const options = createTestOptions();
    const { handleDownloadTemplate } = useDataImport(options);

    await handleDownloadTemplate();

    expect(ElMessage.error).not.toHaveBeenCalled();
  });
});

describe('useDataImport - 导入结果摘要显示 - 需求 5.7, 5.8', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('全部成功时显示成功消息', async () => {
    const mockImportApi = vi.fn().mockResolvedValue({
      success_count: 10,
      fail_count: 0,
      errors: [],
    });
    const options = createTestOptions({ importApi: mockImportApi });
    const { handleFileChange, handleImport, importResult } = useDataImport(options);

    handleFileChange(createMockFile('data.xlsx'));
    await handleImport();

    expect(ElMessage.success).toHaveBeenCalledWith('导入完成：10 条记录导入成功');
    expect(importResult.value).toEqual({
      success_count: 10,
      fail_count: 0,
      errors: [],
    });
  });

  it('部分失败时显示警告消息', async () => {
    const mockImportApi = vi.fn().mockResolvedValue({
      success_count: 8,
      fail_count: 2,
      errors: [
        { row: 3, message: '名称不能为空' },
        { row: 7, message: '格式不正确' },
      ],
    });
    const options = createTestOptions({ importApi: mockImportApi });
    const { handleFileChange, handleImport, importResult } = useDataImport(options);

    handleFileChange(createMockFile('data.csv'));
    await handleImport();

    expect(ElMessage.warning).toHaveBeenCalledWith(
      '导入完成：8 条成功，2 条失败'
    );
    // 验证结果包含逐行错误信息
    expect(importResult.value?.errors).toHaveLength(2);
    expect(importResult.value?.errors?.[0]).toEqual({ row: 3, message: '名称不能为空' });
    expect(importResult.value?.errors?.[1]).toEqual({ row: 7, message: '格式不正确' });
  });

  it('importApi 传入正确的文件对象', async () => {
    const mockImportApi = vi.fn().mockResolvedValue({
      success_count: 1,
      fail_count: 0,
      errors: [],
    });
    const options = createTestOptions({ importApi: mockImportApi });
    const { handleFileChange, handleImport } = useDataImport(options);

    const file = createMockFile('test.xlsx');
    handleFileChange(file);
    await handleImport();

    expect(mockImportApi).toHaveBeenCalledWith(file);
  });

  it('导入完成后 importLoading 恢复为 false', async () => {
    const options = createTestOptions();
    const { handleFileChange, handleImport, importLoading } = useDataImport(options);

    handleFileChange(createMockFile('data.xlsx'));
    await handleImport();

    expect(importLoading.value).toBe(false);
  });

  it('parseImportResult 正确解析响应（含 errors 字段）', () => {
    const response: ImportResult = {
      success_count: 5,
      fail_count: 3,
      errors: [
        { row: 1, message: '字段缺失' },
        { row: 4, message: '数据重复' },
        { row: 6, message: '格式错误' },
      ],
    };

    const parsed = parseImportResult(response);

    expect(parsed.success_count).toBe(5);
    expect(parsed.fail_count).toBe(3);
    expect(parsed.errors).toHaveLength(3);
    expect(parsed.errors?.[0]).toEqual({ row: 1, message: '字段缺失' });
  });

  it('parseImportResult 响应无 errors 字段时默认为空数组', () => {
    const response = {
      success_count: 10,
      fail_count: 0,
    } as ImportResult;

    const parsed = parseImportResult(response);

    expect(parsed.errors).toEqual([]);
  });
});

describe('useDataImport - 导入失败错误处理 - 需求 5.6', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('未选择文件时显示警告提示', async () => {
    const options = createTestOptions();
    const { handleImport } = useDataImport(options);

    await handleImport();

    expect(ElMessage.warning).toHaveBeenCalledWith('请先选择导入文件');
    expect(options.importApi).not.toHaveBeenCalled();
  });

  it('导入 API 失败时显示错误消息', async () => {
    const mockImportApi = vi.fn().mockRejectedValue(new Error('服务器内部错误'));
    const options = createTestOptions({ importApi: mockImportApi });
    const { handleFileChange, handleImport } = useDataImport(options);

    handleFileChange(createMockFile('data.xlsx'));
    await handleImport();

    expect(ElMessage.error).toHaveBeenCalledWith('导入失败：服务器内部错误');
  });

  it('错误无 message 属性时显示"未知错误"', async () => {
    const mockImportApi = vi.fn().mockRejectedValue({});
    const options = createTestOptions({ importApi: mockImportApi });
    const { handleFileChange, handleImport } = useDataImport(options);

    handleFileChange(createMockFile('data.csv'));
    await handleImport();

    expect(ElMessage.error).toHaveBeenCalledWith('导入失败：未知错误');
  });

  it('导入失败后 importLoading 恢复为 false', async () => {
    const mockImportApi = vi.fn().mockRejectedValue(new Error('网络错误'));
    const options = createTestOptions({ importApi: mockImportApi });
    const { handleFileChange, handleImport, importLoading } = useDataImport(options);

    handleFileChange(createMockFile('data.xlsx'));
    await handleImport();

    expect(importLoading.value).toBe(false);
  });

  it('导入失败后 importResult 保持为 null', async () => {
    const mockImportApi = vi.fn().mockRejectedValue(new Error('失败'));
    const options = createTestOptions({ importApi: mockImportApi });
    const { handleFileChange, handleImport, importResult } = useDataImport(options);

    handleFileChange(createMockFile('data.xlsx'));
    await handleImport();

    expect(importResult.value).toBeNull();
  });
});
