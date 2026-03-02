import { request } from '/@/utils/service';

/**
 * 获取平台统计数据
 */
export function getPlatformStats() {
	return request({
		url: '/api/system/home_stats/platform_stats/',
		method: 'get',
	});
}

/**
 * 获取个人统计数据
 */
export function getMyStats() {
	return request({
		url: '/api/system/home_stats/my_stats/',
		method: 'get',
	});
}

/**
 * 获取热门内容
 */
export function getHotContent() {
	return request({
		url: '/api/system/home_stats/hot_content/',
		method: 'get',
	});
}

/**
 * 获取最新内容
 */
export function getRecentContent() {
	return request({
		url: '/api/system/home_stats/recent_content/',
		method: 'get',
	});
}

/**
 * 获取月度趋势数据
 */
export function getMonthlyTrend() {
	return request({
		url: '/api/system/home_stats/monthly_trend/',
		method: 'get',
	});
}
