/**
 * 数据导入纯工具函数
 *
 * 不依赖 UI 框架，可在测试中直接导入
 */

/**
 * 导入结果接口
 */
export interface ImportResult {
  success_count: number;
  fail_count: number;
  errors?: Array<{ row: number; message: string }>;
}

/** 允许的导入文件扩展名 */
export const ALLOWED_IMPORT_EXTENSIONS = ['.xlsx', '.csv'];

/**
 * 验证文件格式是否合法
 * 仅接受 .xlsx 和 .csv 格式（不区分大小写）
 * @param fileName 文件名
 */
export function validateFileFormat(fileName: string): boolean {
  const lowerName = fileName.toLowerCase();
  return ALLOWED_IMPORT_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
}

/**
 * 解析导入结果响应
 * @param response 导入 API 响应
 */
export function parseImportResult(response: ImportResult): ImportResult {
  return {
    success_count: response.success_count,
    fail_count: response.fail_count,
    errors: response.errors || [],
  };
}

/**
 * 构造导入 API URL
 * @param moduleName 模块名
 */
export function buildImportUrl(moduleName: string): string {
  return `/api/content/${moduleName}/import_data/`;
}

/**
 * 构造模板下载 API URL
 * @param moduleName 模块名
 */
export function buildTemplateUrl(moduleName: string): string {
  return `/api/content/${moduleName}/import_template/`;
}
