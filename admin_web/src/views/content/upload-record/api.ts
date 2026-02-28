import { request, downloadFile } from '/@/utils/service';
import { PageQuery, InfoReq } from '@fast-crud/fast-crud';

/**
 * 上传记录数据接口
 */
export interface UploadRecord {
	id: string; // UUID
	uploader: number; // 上传者 ID
	uploader_name?: string; // 上传者名称（关联查询）
	target_id: string; // 目标 ID
	target_type: 'knowledge' | 'persona'; // 目标类型
	name: string; // 名称
	description?: string; // 描述
	status: 'pending' | 'approved' | 'rejected'; // 审核状态
	create_datetime: string; // 创建时间
}

export const apiPrefix = '/api/content/users/uploads/';

/**
 * 获取上传记录列表
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
 * 获取上传记录详情
 * @param id 上传记录 ID
 */
export function GetObj(id: InfoReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'get',
	});
}

/**
 * 审核通过上传记录
 * @param id 上传记录 ID
 */
export function ApproveObj(id: string) {
	return request({
		url: `/api/content/review/${id}/approve/`,
		method: 'post',
	});
}

/**
 * 审核拒绝上传记录
 * @param id 上传记录 ID
 * @param reason 拒绝原因
 */
export function RejectObj(id: string, reason: string) {
	return request({
		url: `/api/content/review/${id}/reject/`,
		method: 'post',
		data: { reason },
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
 * 批量审核通过上传记录
 * @param ids 上传记录 ID 数组
 */
export function batchApprove(ids: string[]): Promise<BatchOperationResponse> {
	return request({
		url: '/api/content/review/batch-approve/',
		method: 'post',
		data: { ids },
	});
}

/**
 * 批量审核拒绝上传记录
 * @param ids 上传记录 ID 数组
 * @param reason 拒绝原因
 */
export function batchReject(ids: string[], reason: string): Promise<BatchOperationResponse> {
	return request({
		url: '/api/content/review/batch-reject/',
		method: 'post',
		data: { ids, reason },
	});
}

// ==================== 导出 API ====================

/**
 * 导出上传记录数据（支持格式和字段选择）
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
