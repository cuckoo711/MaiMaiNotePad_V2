import { request, downloadFile } from '/@/utils/service';
import { PageQuery, InfoReq } from '@fast-crud/fast-crud';

/**
 * 下载记录数据接口
 */
export interface DownloadRecord {
	id: string; // UUID
	target_id: string; // 目标 ID
	target_type: 'knowledge' | 'persona'; // 目标类型
	create_datetime: string; // 创建时间
}

export const apiPrefix = '/api/content/admin/downloads/';

/**
 * 获取下载记录列表
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
 * 获取下载记录详情
 * @param id 下载记录 ID
 */
export function GetObj(id: InfoReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'get',
	});
}

/**
 * 获取下载统计数据（按目标类型分组）
 */
export function GetStats() {
	return request({
		url: apiPrefix + 'stats/',
		method: 'get',
	});
}


// ==================== 导出 API ====================

/**
 * 导出下载记录数据（增强版，支持格式和字段选择）
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
