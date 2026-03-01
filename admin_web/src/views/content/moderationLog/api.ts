import { request } from '/@/utils/service';
import { PageQuery } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/content/moderation-logs/';

/**
 * 获取审核日志列表（分页）
 * @param query 分页查询参数
 */
export function GetList(query: PageQuery) {
	return request({
		url: apiPrefix,
		method: 'get',
		params: query,
	});
}

/**
 * 获取审核日志详情
 * @param id 日志 ID
 */
export function GetObj(id: string) {
	return request({
		url: apiPrefix + id + '/',
		method: 'get',
	});
}

/**
 * 获取审核统计数据
 */
export function GetStats() {
	return request({
		url: apiPrefix + 'stats/',
		method: 'get',
	});
}
