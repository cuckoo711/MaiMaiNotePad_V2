import { request, downloadFile } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

/**
 * 人设卡数据接口
 */
export interface PersonaCard {
	id: string; // UUID
	name: string; // 名称
	description: string; // 描述
	uploader: number; // 上传者 ID
	uploader_name?: string; // 上传者名称（关联查询）
	copyright_owner?: string; // 版权所有者
	content?: string; // 内容
	tags?: string; // 标签（逗号分隔）
	star_count: number; // 收藏数
	downloads: number; // 下载次数
	base_path: string; // 基础路径（JSON 数组）
	is_public: boolean; // 是否公开
	is_pending: boolean; // 是否待审核
	rejection_reason?: string; // 拒绝原因
	version: string; // 版本号
	create_datetime: string; // 创建时间
	update_datetime: string; // 更新时间
}

/**
 * 人设卡文件接口
 */
export interface PersonaCardFile {
	id: string; // UUID
	persona_card: string; // 人设卡 ID
	file_name: string; // 文件名
	file_path: string; // 文件路径
	file_size: number; // 文件大小
	create_datetime: string; // 创建时间
}

export const apiPrefix = '/api/content/persona/';

/**
 * 获取人设卡列表
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
 * 获取人设卡详情
 * @param id 人设卡 ID
 */
export function GetObj(id: InfoReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'get',
	});
}

/**
 * 创建人设卡
 * @param obj 人设卡数据
 */
export function AddObj(obj: AddReq) {
	return request({
		url: apiPrefix,
		method: 'post',
		data: obj,
	});
}

/**
 * 更新人设卡
 * @param obj 人设卡数据
 */
export function UpdateObj(obj: EditReq) {
	return request({
		url: apiPrefix + obj.id + '/',
		method: 'put',
		data: obj,
	});
}

/**
 * 删除人设卡
 * @param id 人设卡 ID
 */
export function DelObj(id: DelReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'delete',
		data: { id },
	});
}

/**
 * 审核通过人设卡
 * @param id 人设卡 ID
 */
export function ApproveObj(id: string) {
	return request({
		url: `/api/content/review/${id}/approve/`,
		method: 'post',
	});
}

/**
 * 审核拒绝人设卡
 * @param id 人设卡 ID
 * @param reason 拒绝原因
 */
export function RejectObj(id: string, reason: string) {
	return request({
		url: `/api/content/review/${id}/reject/`,
		method: 'post',
		data: { reason },
	});
}

/**
 * 导出人设卡数据
 * @param params 查询参数
 */
export function exportData(params: any) {
	return downloadFile({
		url: apiPrefix + 'export_data/',
		params: params,
		method: 'get',
	});
}

/**
 * 获取人设卡关联文件列表
 * @param id 人设卡 ID
 */
export function GetFiles(id: string) {
	return request({
		url: apiPrefix + id + '/files/',
		method: 'get',
	});
}

// ==================== 批量操作和导入导出类型定义 ====================

/** 批量操作响应 */
export interface BatchOperationResponse {
	success_count: number;
	fail_count: number;
	failures?: Array<{ id: string; reason: string }>;
}

/** 导入结果响应 */
export interface ImportResultResponse {
	success_count: number;
	fail_count: number;
	errors?: Array<{ row: number; message: string }>;
}

// ==================== 批量操作 API ====================

/**
 * 批量审核通过
 * @param ids 人设卡 ID 数组
 */
export function batchApprove(ids: string[]): Promise<BatchOperationResponse> {
	return request({
		url: '/api/content/review/batch-approve/',
		method: 'post',
		data: { ids },
	});
}

/**
 * 批量审核拒绝
 * @param ids 人设卡 ID 数组
 * @param reason 拒绝原因
 */
export function batchReject(ids: string[], reason: string): Promise<BatchOperationResponse> {
	return request({
		url: '/api/content/review/batch-reject/',
		method: 'post',
		data: { ids, reason },
	});
}

/**
 * 批量删除人设卡
 * @param ids 人设卡 ID 数组
 */
export function batchDelete(ids: string[]): Promise<BatchOperationResponse> {
	return request({
		url: apiPrefix + 'batch-delete/',
		method: 'post',
		data: { ids },
	});
}

// ==================== 导入导出 API ====================

/**
 * 导出人设卡数据（增强版）
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

/**
 * 导入人设卡数据
 * @param file 导入文件
 */
export function importData(file: File): Promise<ImportResultResponse> {
	const formData = new FormData();
	formData.append('file', file);
	return request({
		url: apiPrefix + 'import_data/',
		method: 'post',
		data: formData,
		headers: { 'Content-Type': 'multipart/form-data' },
	});
}

/**
 * 下载人设卡导入模板
 */
export function downloadImportTemplate() {
	return downloadFile({
		url: apiPrefix + 'import_template/',
		method: 'get',
	});
}
