/**
 * 高级搜索工具函数
 *
 * 提供搜索参数构造和日期范围转换的纯函数
 */

/**
 * 将多个搜索条件合并为查询参数对象
 * 所有非空条件都应出现在结果中（AND 组合）
 * @param conditions 搜索条件键值对
 * @returns 合并后的查询参数对象（过滤掉空值）
 */
export function buildSearchParams(conditions: Record<string, any>): Record<string, any> {
  const params: Record<string, any> = {};
  for (const [key, value] of Object.entries(conditions)) {
    if (value !== undefined && value !== null && value !== '') {
      params[key] = value;
    }
  }
  return params;
}

/**
 * 构造模糊搜索参数
 * 非空关键词作为 search 参数传递，空关键词时不包含 search 参数
 * @param keyword 搜索关键词
 * @returns 包含或不包含 search 参数的对象
 */
export function buildFuzzySearchParam(keyword: string): Record<string, string> {
  const trimmed = keyword.trim();
  if (trimmed.length > 0) {
    return { search: trimmed };
  }
  return {};
}

/**
 * 将日期范围数组转换为 create_datetime_after 和 create_datetime_before 参数
 * @param dateRange 日期范围数组 [startDate, endDate]，可能为 null/undefined
 * @returns 包含 create_datetime_after 和 create_datetime_before 的对象，或空对象
 */
export function resolveDateRange(dateRange: [string, string] | null | undefined): Record<string, string> {
  if (!dateRange || dateRange.length !== 2) {
    return {};
  }
  const [start, end] = dateRange;
  if (!start || !end) {
    return {};
  }
  return {
    create_datetime_after: start,
    create_datetime_before: end,
  };
}
