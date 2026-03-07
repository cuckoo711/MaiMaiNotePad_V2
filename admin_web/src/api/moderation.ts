import { request, downloadFile } from '/@/utils/service';
import { PageQuery } from '@fast-crud/fast-crud';

/**
 * 禁言记录接口
 */
export interface MuteRecord {
	id: number;
	user: number;
	user_name?: string;
	user_avatar?: string;
	mute_type: 'manual' | 'auto';
	muted_by?: number;
	muted_by_name?: string;
	mute_reason: string;
	muted_until?: string;
	is_active: boolean;
	is_manually_modified: boolean;
	auto_unmute_task_id?: string;
	unmuted_at?: string;
	unmuted_by?: number;
	unmuted_by_name?: string;
	unmute_reason?: string;
	create_datetime: string;
	update_datetime: string;
}

/**
 * 封禁记录接口
 */
export interface BanRecord {
	id: number;
	user_name?: string;
	user_avatar?: string;
	is_active: boolean;
	locked_until?: string;
	ban_reason?: string;
	create_datetime: string;
	update_datetime: string;
}

/**
 * 操作日志接口
 */
export interface ModerationLog {
	id: number;
	operator: number;
	operator_name?: string;
	target_user: number;
	target_user_name?: string;
	operation_type: 'mute' | 'unmute' | 'ban' | 'unban' | 'modify_duration';
	reason: string;
	duration_hours?: number;
	old_duration_hours?: number;
	ip_address: string;
	user_agent: string;
	extra_data?: any;
	create_datetime: string;
}

/**
 * 批量操作响应
 */
export interface BatchOperationResponse {
	total: number;
	success: number;
	failed: number;
	results: Array<{
		user_id: number;
		user_name?: string;
		status: 'success' | 'failed';
		reason?: string;
	}>;
}

export const apiPrefix = '/api/content/moderation/';

// ==================== 禁言管理 API ====================

/**
 * 获取禁言列表
 * @param query 分页查询参数
 */
export function getMuteList(query: PageQuery) {
	return request({
		url: apiPrefix + 'mute-list/',
		method: 'get',
		params: query,
	});
}

/**
 * 禁言用户
 * @param data 禁言参数
 */
export function muteUser(data: {
	user_id: string | number;
	duration: string;
	reason: string;
}) {
	return request({
		url: apiPrefix + 'mute/',
		method: 'post',
		data,
	});
}

/**
 * 解除禁言
 * @param data 解除禁言参数
 */
export function unmuteUser(data: {
	user_id: string | number;
	reason?: string;
}) {
	return request({
		url: apiPrefix + 'unmute/',
		method: 'post',
		data,
	});
}

/**
 * 批量禁言
 * @param data 批量禁言参数
 */
export function batchMute(data: {
	user_ids: number[];
	duration: string;
	reason: string;
}): Promise<BatchOperationResponse> {
	return request({
		url: apiPrefix + 'batch-mute/',
		method: 'post',
		data,
	});
}

/**
 * 批量解除禁言
 * @param data 批量解除参数
 */
export function batchUnmute(data: {
	user_ids: number[];
	reason?: string;
}): Promise<BatchOperationResponse> {
	return request({
		url: apiPrefix + 'batch-unmute/',
		method: 'post',
		data,
	});
}

// ==================== 封禁管理 API ====================

/**
 * 获取封禁列表
 * @param query 分页查询参数
 */
export function getBanList(query: PageQuery) {
	return request({
		url: apiPrefix + 'ban-list/',
		method: 'get',
		params: query,
	});
}

/**
 * 封禁用户
 * @param data 封禁参数
 */
export function banUser(data: {
	user_id: string | number;
	duration: string;
	reason: string;
}) {
	return request({
		url: apiPrefix + 'ban/',
		method: 'post',
		data,
	});
}

/**
 * 解除封禁
 * @param data 解除封禁参数
 */
export function unbanUser(data: {
	user_id: string | number;
	reason?: string;
}) {
	return request({
		url: apiPrefix + 'unban/',
		method: 'post',
		data,
	});
}

/**
 * 批量封禁
 * @param data 批量封禁参数
 */
export function batchBan(data: {
	user_ids: number[];
	duration: string;
	reason: string;
}): Promise<BatchOperationResponse> {
	return request({
		url: apiPrefix + 'batch-ban/',
		method: 'post',
		data,
	});
}

/**
 * 批量解除封禁
 * @param data 批量解除参数
 */
export function batchUnban(data: {
	user_ids: number[];
	reason?: string;
}): Promise<BatchOperationResponse> {
	return request({
		url: apiPrefix + 'batch-unban/',
		method: 'post',
		data,
	});
}

// ==================== AI自动禁言 API ====================

/**
 * 获取AI自动禁言列表
 * @param query 分页查询参数
 */
export function getAutoMuteList(query: PageQuery) {
	return request({
		url: apiPrefix + 'auto-mute-list/',
		method: 'get',
		params: query,
	});
}

// ==================== 通用操作 API ====================

/**
 * 修改时长
 * @param data 修改时长参数
 */
export function modifyDuration(data: {
	user_id: string | number;
	operation_type: 'mute' | 'ban';
	new_duration: string;
	reason: string;
}) {
	return request({
		url: apiPrefix + 'modify-duration/',
		method: 'put',
		data,
	});
}

/**
 * 获取操作日志
 * @param query 查询参数
 */
export function getModerationLogs(query: {
	target_user_id?: string | number;
	operator_id?: string | number;
	operation_type?: string;
	start_date?: string;
	end_date?: string;
	page?: number;
	page_size?: number;
}) {
	return request({
		url: apiPrefix + 'logs/',
		method: 'get',
		params: query,
	});
}

/**
 * 导出数据
 * @param params 导出参数
 */
export function exportData(params: {
	type: 'mute' | 'ban' | 'auto_mute';
	format: 'csv' | 'excel';
	[key: string]: any;
}) {
	return downloadFile({
		url: apiPrefix + 'export/',
		params: params,
		method: 'get',
	});
}
