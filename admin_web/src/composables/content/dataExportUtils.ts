/**
 * 数据导出纯工具函数
 *
 * 不依赖 UI 框架，可在测试中直接导入
 */

/**
 * 导出参数接口
 */
export interface ExportParams {
  /** 导出格式 */
  format: 'excel' | 'csv';
  /** 导出字段列表 */
  fields: string[];
  /** 导出选中记录的 ID（可选） */
  ids?: string[];
  /** 其他筛选条件 */
  [key: string]: any;
}

/**
 * 可导出字段定义
 */
export interface ExportField {
  key: string;
  label: string;
}

/** 大数据量阈值 */
export const EXPORT_LARGE_DATA_THRESHOLD = 5000;

/**
 * 判断是否需要大数据量提示
 * @param count 数据量
 */
export function shouldShowLargeDataWarning(count: number): boolean {
  return count > EXPORT_LARGE_DATA_THRESHOLD;
}

/**
 * 获取导出选项列表
 * @param selectedCount 选中记录数量
 * @returns 导出选项（"导出全部记录" 或 "导出选中记录"/"导出全部记录"）
 */
export function getExportOptions(selectedCount: number): string[] {
  if (selectedCount > 0) {
    return ['导出选中记录', '导出全部记录'];
  }
  return ['导出全部记录'];
}

/**
 * 构造导出 API 请求参数
 * @param moduleName 模块名
 * @param params 导出参数
 */
export function buildExportApiParams(
  moduleName: string,
  params: ExportParams
): { url: string; params: ExportParams } {
  return {
    url: `/api/content/${moduleName}/export_data/`,
    params,
  };
}
