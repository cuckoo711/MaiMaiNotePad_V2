import { request, downloadFile } from '/@/utils/service';
import { PageQuery, DelReq, InfoReq } from '@fast-crud/fast-crud';

/**
 * 收藏记录数据接口
 */
export interface StarRecord {
	id: string; // UUID
	user: number; // 用户 ID
	user_name?: string; // 用户名称（关联查询）
	target_id: string; // 目标 ID
	target_type: 'knowledge' | 'persona'; // 目标类型
	create_datetime: string; // 创建时间
}

export const apiPrefix = '/api/content/users/stars/';

/**
 * 获取收藏记录列表
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
 * 获取收藏记录详情
 * @param id 收藏记录 ID
 */
export function GetObj(id: InfoReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'get',
	});
}

/**
 * 删除收藏记录
 * @param id 收藏记录 ID
 */
export function DelObj(id: DelReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'delete',
		data: { id },
	});
}

/**
 * 获取收藏统计数据（按目标类型分组）
 */
export function GetStats() {
	return request({
		url: apiPrefix + 'stats/',
		method: 'get',
	});
}

// ==================== 批量操作类型定义 ====================

/** 批量操作响应 */
export interface BatchOperationResponse {
	success_count: number;
	fail_count: number;
	failures?: Array<{ id: string; reason: string }>;
}

// ==================== 批量操作 API ====================

/**
 * 批量删除收藏记录
 * @param ids 收藏记录 ID 数组
 */
export function batchDelete(ids: string[]): Promise<BatchOperationResponse> {
	return request({
		url: apiPrefix + 'batch-delete/',
		method: 'post',
		data: { ids },
	});
}

// ==================== 导出 API ====================

/**
 * 导出收藏记录数据（支持格式和字段选择）
 * @param params 导出参数
 */
export function exportDataAdvanced(params: {
	format: string;
	fields: string[];
	ids?: string[];
	[key: string]: any;
}) {
	return downloadFile({
		url: apiPrefix + 'export_data/',
		params: params,
		method: 'get',
	});
}
