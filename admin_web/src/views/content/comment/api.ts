import { request, downloadFile } from '/@/utils/service';
import { PageQuery, DelReq, InfoReq } from '@fast-crud/fast-crud';

/**
 * 评论数据接口
 */
export interface Comment {
	id: string; // UUID
	user: number; // 用户 ID
	user_name?: string; // 用户名称
	user_avatar?: string; // 用户头像
	target_id: string; // 目标 ID
	target_type: 'knowledge' | 'persona'; // 目标类型
	parent?: string; // 父评论 ID
	content: string; // 评论内容
	is_deleted: boolean; // 是否已删除
	like_count: number; // 点赞数
	dislike_count: number; // 点踩数
	replies?: Comment[]; // 回复列表
	create_datetime: string; // 创建时间
	update_datetime: string; // 更新时间
}

export const apiPrefix = '/api/content/comments/';

/**
 * 获取管理后台评论列表（包含已删除的评论）
 * @param query 分页查询参数
 */
export function GetList(query: PageQuery) {
	return request({
		url: apiPrefix + 'admin_list/',
		method: 'get',
		params: query,
	});
}

/**
 * 获取评论详情
 * @param id 评论 ID
 */
export function GetObj(id: InfoReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'get',
	});
}

/**
 * 软删除评论（管理后台删除，含级联逻辑）
 * 一级评论：连带删除子评论
 * 二级评论：仅删除自身
 * @param id 评论 ID
 */
export function DelObj(id: DelReq) {
	return request({
		url: apiPrefix + id + '/admin_delete/',
		method: 'post',
	});
}

/**
 * 管理后台删除评论（DelObj 的别名，保持向后兼容）
 * @param id 评论 ID
 */
export function AdminDeleteObj(id: string) {
	return request({
		url: apiPrefix + id + '/admin_delete/',
		method: 'post',
	});
}

/**
 * 获取评论的回复列表
 * @param id 评论 ID
 */
export function GetReplies(id: string) {
	return request({
		url: apiPrefix + 'admin_list/',
		method: 'get',
		params: { parent: id },
	});
}

/**
 * 封禁评论用户
 * @param id 评论 ID
 * @param reason 封禁原因
 * @param durationHours 封禁时长（小时），不传则永久封禁
 */
export function BanUser(id: string, reason: string, durationHours?: number) {
	const data: any = { reason };
	if (durationHours !== undefined && durationHours !== null) {
		data.duration_hours = durationHours;
	}
	return request({
		url: apiPrefix + id + '/ban_user/',
		method: 'post',
		data,
	});
}

/**
 * 恢复已删除的评论
 * @param id 评论 ID
 */
export function RestoreObj(id: string) {
	return request({
		url: apiPrefix + id + '/restore/',
		method: 'post',
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
 * 批量删除评论
 * @param ids 评论 ID 数组
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
 * 导出评论数据（支持格式和字段选择）
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
