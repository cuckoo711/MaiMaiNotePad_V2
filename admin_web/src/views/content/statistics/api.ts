/**
 * 数据统计 API 接口
 *
 * 提供概览指标、审核状态分布、趋势数据、热门内容排行等统计数据的 API 调用
 */
import { request } from '/@/utils/service';

/** API 前缀 */
const apiPrefix = '/api/content/statistics/';

// ==================== 类型定义 ====================

/** 概览指标 */
export interface StatisticsOverview {
	knowledge_base_count: number;
	persona_card_count: number;
	comment_count: number;
	star_count: number;
	upload_count: number;
	download_count: number;
}

/** 审核状态分布 */
export interface ReviewDistribution {
	knowledge_base: {
		pending: number;
		approved: number;
		rejected: number;
	};
	persona_card: {
		pending: number;
		approved: number;
		rejected: number;
	};
}

/** 趋势数据点 */
export interface TrendDataPoint {
	date: string; // YYYY-MM-DD
	knowledge_base_count: number;
	persona_card_count: number;
	comment_count: number;
}

/** 趋势数据响应 */
export interface TrendResponse {
	data: TrendDataPoint[];
}

/** 热门内容项 */
export interface TopContentItem {
	id: string;
	name: string;
	uploader_name: string;
	star_count: number;
	downloads: number;
}

/** 热门内容响应 */
export interface TopContentResponse {
	knowledge_base: TopContentItem[];
	persona_card: TopContentItem[];
}

// ==================== API 函数 ====================

/**
 * 获取概览指标数据
 */
export function getOverview(): Promise<StatisticsOverview> {
	return request({
		url: apiPrefix + 'overview/',
		method: 'get',
	});
}

/**
 * 获取审核状态分布数据
 */
export function getReviewDistribution(): Promise<ReviewDistribution> {
	return request({
		url: apiPrefix + 'review-distribution/',
		method: 'get',
	});
}

/**
 * 获取趋势数据
 * @param days 时间范围（天数），如 7、30、90
 */
export function getTrends(days?: number): Promise<TrendResponse> {
	return request({
		url: apiPrefix + 'trends/',
		method: 'get',
		params: days !== undefined ? { days } : {},
	});
}

/**
 * 获取热门内容排行数据
 * @param orderBy 排序方式：star_count（按收藏数）或 downloads（按下载次数）
 * @param limit 返回数量限制
 */
export function getTopContent(orderBy?: string, limit?: number): Promise<TopContentResponse> {
	const params: Record<string, any> = {};
	if (orderBy !== undefined) {
		params.order_by = orderBy;
	}
	if (limit !== undefined) {
		params.limit = limit;
	}
	return request({
		url: apiPrefix + 'top-content/',
		method: 'get',
		params,
	});
}
