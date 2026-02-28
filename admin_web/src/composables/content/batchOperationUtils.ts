/**
 * 批量操作纯工具函数
 *
 * 不依赖 UI 框架（Element Plus），可在测试中直接导入
 */

/**
 * 批量操作结果接口
 */
export interface BatchResult {
  success_count: number;
  fail_count: number;
  failures?: Array<{ id: string; reason: string }>;
}

/**
 * 格式化选中数量显示文本
 * @param count 选中数量
 */
export function formatSelectionText(count: number): string {
  return `已选中 ${count} 条`;
}

/**
 * 验证拒绝原因是否为空白
 * @param reason 拒绝原因
 * @returns 是否有效（非空白）
 */
export function validateRejectReason(reason: string): boolean {
  return reason.trim().length > 0;
}

/**
 * 解析批量操作结果
 * @param result 批量操作响应
 * @param totalCount 请求的 ID 总数
 */
export function parseBatchResult(result: BatchResult, totalCount: number): BatchResult {
  return {
    success_count: result.success_count,
    fail_count: result.fail_count,
    failures: result.failures || [],
  };
}

/**
 * 构造批量审核通过请求体
 * @param ids ID 数组
 */
export function buildBatchApproveRequest(ids: string[]): { ids: string[] } {
  return { ids };
}

/**
 * 构造批量审核拒绝请求体
 * @param ids ID 数组
 * @param reason 拒绝原因
 */
export function buildBatchRejectRequest(ids: string[], reason: string): { ids: string[]; reason: string } {
  return { ids, reason };
}

/**
 * 构造批量删除请求 URL
 * @param moduleName 模块名称
 */
export function buildBatchDeleteUrl(moduleName: string): string {
  return `/api/content/${moduleName}/batch-delete/`;
}

/**
 * 构造批量删除请求体
 * @param ids ID 数组
 */
export function buildBatchDeleteRequest(ids: string[]): { ids: string[] } {
  return { ids };
}

/** 批量审核通过 API 端点 */
export const BATCH_APPROVE_URL = '/api/content/review/batch-approve/';

/** 批量审核拒绝 API 端点 */
export const BATCH_REJECT_URL = '/api/content/review/batch-reject/';
