import { request } from '/@/utils/service';
import { PageQuery } from '@fast-crud/fast-crud';

/**
 * 审核项数据接口
 */
export interface ReviewItem {
	id: string;
	name: string;
	description: string;
	content_type: 'knowledge' | 'persona';
	uploader_id: number;
	uploader_name: string;
	create_datetime: string;
	tags: string;
	file_count: number;
	ai_review_decision: 'auto_approved' | 'auto_rejected' | 'pending_manual' | null;
}

/**
 * 分页响应接口
 */
export interface PaginatedResponse {
	items: ReviewItem[];
	total: number;
	page: number;
	page_size: number;
}

/**
 * 批量操作响应接口
 */
export interface BatchOperationResponse {
	success_count: number;
	fail_count: number;
	failures?: Array<{ id: string; reason: string }>;
}

/**
 * 审核统计数据接口
 */
export interface ReviewStats {
	pending_total: number;
	pending_knowledge: number;
	pending_persona: number;
	approved_today: number;
	rejected_today: number;
	approval_rate: number;
}

export const apiPrefix = '/api/content/review/';

/**
 * 获取待审核列表（分页）
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
 * 获取审核统计数据
 */
export function GetStats(): Promise<ReviewStats> {
	return request({
		url: apiPrefix + 'stats/',
		method: 'get',
	});
}

/**
 * 获取审核历史
 * @param query 分页查询参数
 */
export function GetHistory(query: PageQuery) {
	return request({
		url: apiPrefix + 'history/',
		method: 'get',
		params: query,
	});
}

/**
 * 单条审核通过
 * @param id 内容 ID
 * @param contentType 内容类型
 */
export function approveItem(id: string, contentType: string) {
	return request({
		url: apiPrefix + id + '/approve/',
		method: 'post',
		data: { content_type: contentType },
	});
}

/**
 * 单条审核拒绝
 * @param id 内容 ID
 * @param contentType 内容类型
 * @param reason 拒绝原因
 */
export function rejectItem(id: string, contentType: string, reason: string) {
	return request({
		url: apiPrefix + id + '/reject/',
		method: 'post',
		data: { content_type: contentType, reason },
	});
}

/**
 * 退回内容
 * @param id 内容 ID
 * @param contentType 内容类型
 * @param reason 退回原因
 */
export function returnDraft(id: string, contentType: string, reason?: string) {
	return request({
		url: apiPrefix + id + '/return_draft/',
		method: 'post',
		data: { content_type: contentType, reason: reason || '' },
	});
}

/**
 * 批量审核通过
 * @param ids 内容 ID 数组
 * @param contentType 内容类型
 */
export function batchApprove(ids: string[], contentType: string): Promise<BatchOperationResponse> {
	return request({
		url: apiPrefix + 'batch_approve/',
		method: 'post',
		data: { ids, content_type: contentType },
	});
}

/**
 * 批量审核拒绝
 * @param ids 内容 ID 数组
 * @param contentType 内容类型
 * @param reason 拒绝原因
 */
export function batchReject(ids: string[], contentType: string, reason: string): Promise<BatchOperationResponse> {
	return request({
		url: apiPrefix + 'batch_reject/',
		method: 'post',
		data: { ids, content_type: contentType, reason },
	});
}

/**
 * AI 审核报告分段结果接口
 */
export interface AIReviewPartResult {
	part_name: string;
	part_type: 'text_field' | 'file' | 'segment';
	confidence: number;
	violation_types: string[];
	decision?: string;
	segment_index?: number;
	text_summary?: string;
	segments?: AIReviewPartResult[];
}

/**
 * AI 审核报告接口
 */
export interface AIReviewReport {
	id: string;
	content_id: string;
	content_type: string;
	content_name: string;
	create_datetime: string;
	decision: 'auto_approved' | 'auto_rejected' | 'pending_manual';
	final_confidence: number;
	violation_types: string[];
	report_data: {
		content_name: string;
		content_type: string;
		review_time: string;
		decision: string;
		final_confidence: number;
		violation_types: string[];
		parts: AIReviewPartResult[];
	};
}

/**
 * 触发单条 AI 审核
 * @param id 内容 ID
 * @param contentType 内容类型
 */
export function triggerAIReview(id: string, contentType: string) {
	return request({
		url: apiPrefix + id + '/ai_review/',
		method: 'post',
		data: { content_type: contentType },
	});
}

/**
 * 触发批量 AI 审核
 * @param ids 内容 ID 数组
 * @param contentType 内容类型
 */
export function batchAIReview(ids: string[], contentType: string) {
	return request({
		url: apiPrefix + 'batch_ai_review/',
		method: 'post',
		data: { ids, content_type: contentType },
	});
}

/**
 * 获取 AI 审核报告
 * @param id 内容 ID
 * @param contentType 内容类型
 */
export function getAIReport(id: string, contentType: string): Promise<AIReviewReport> {
	return request({
		url: apiPrefix + id + '/ai_report/',
		method: 'get',
		params: { content_type: contentType },
	});
}
