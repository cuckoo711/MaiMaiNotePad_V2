/**
 * 统计仪表盘纯工具函数
 *
 * 不依赖 UI 框架和 ECharts，可在测试中直接导入
 */
import type { StatisticsOverview, TopContentItem } from './api';

// ==================== 接口定义 ====================

/** 概览卡片数据 */
export interface OverviewCardData {
	/** 对应 StatisticsOverview 的字段名 */
	field: string;
	/** 卡片标题 */
	title: string;
	/** 卡片数值 */
	value: number;
}

/** 饼图扇区数据 */
export interface PieChartSector {
	/** 状态名称（中文） */
	name: string;
	/** 数量 */
	value: number;
	/** 颜色 */
	color: string;
	/** 百分比（0-100） */
	percentage: number;
}

// ==================== 常量 ====================

/** 审核状态颜色方案 */
export const STATUS_COLORS: Record<string, string> = {
	pending: '#E6A23C',
	approved: '#67C23A',
	rejected: '#F56C6C',
};

/** 审核状态中文标签 */
export const STATUS_LABELS: Record<string, string> = {
	pending: '待审核',
	approved: '已通过',
	rejected: '已拒绝',
};

/** 概览卡片字段定义（固定6个） */
const OVERVIEW_CARD_DEFINITIONS: Array<{ field: keyof StatisticsOverview; title: string }> = [
	{ field: 'knowledge_base_count', title: '知识库总数' },
	{ field: 'persona_card_count', title: '人设卡总数' },
	{ field: 'comment_count', title: '评论总数' },
	{ field: 'star_count', title: '收藏总数' },
	{ field: 'upload_count', title: '上传总数' },
	{ field: 'download_count', title: '下载总数' },
];

/** 有效的时间范围天数 */
export const VALID_DAYS = [7, 30, 90] as const;

/** 有效的排序方式 */
export const VALID_ORDER_BY = ['star_count', 'downloads'] as const;

/** 排行榜最大条目数 */
export const TOP_CONTENT_MAX_ITEMS = 10;

// ==================== 工具函数 ====================

/**
 * 将 StatisticsOverview 映射为6个卡片数据
 *
 * @param data 概览指标数据
 * @returns 6个卡片数据数组，每个卡片包含字段名、标题和数值
 */
export function mapOverviewToCards(data: StatisticsOverview): OverviewCardData[] {
	return OVERVIEW_CARD_DEFINITIONS.map((def) => ({
		field: def.field,
		title: def.title,
		value: data[def.field] ?? 0,
	}));
}

/**
 * 构建饼图扇区数据（含百分比计算）
 *
 * @param distribution 审核状态分布数据（pending、approved、rejected）
 * @returns 3个扇区数据，包含名称、数量、颜色和百分比
 */
export function buildPieChartSectors(distribution: {
	pending: number;
	approved: number;
	rejected: number;
}): PieChartSector[] {
	const total = distribution.pending + distribution.approved + distribution.rejected;

	const statuses: Array<'pending' | 'approved' | 'rejected'> = ['pending', 'approved', 'rejected'];

	return statuses.map((status) => ({
		name: STATUS_LABELS[status],
		value: distribution[status],
		color: STATUS_COLORS[status],
		percentage: total === 0 ? 0 : (distribution[status] / total) * 100,
	}));
}

/**
 * 处理排行榜数据，确保最多10条
 *
 * @param items 热门内容项数组
 * @returns 截取后的数组，最多包含10条记录
 */
export function processTopContentList(items: TopContentItem[]): TopContentItem[] {
	return items.slice(0, TOP_CONTENT_MAX_ITEMS);
}

/**
 * 验证并映射时间范围参数
 *
 * 仅接受 7、30、90 三个有效值，无效值默认返回 30
 *
 * @param days 时间范围天数
 * @returns 有效的天数参数
 */
export function mapDaysToApiParam(days: number): number {
	if ((VALID_DAYS as readonly number[]).includes(days)) {
		return days;
	}
	// 无效值默认返回 30
	return 30;
}

/**
 * 验证并映射排序方式参数
 *
 * 仅接受 'star_count' 和 'downloads' 两个有效值，无效值默认返回 'star_count'
 *
 * @param orderBy 排序方式
 * @returns 有效的排序方式参数
 */
export function mapOrderByToApiParam(orderBy: string): string {
	if ((VALID_ORDER_BY as readonly string[]).includes(orderBy)) {
		return orderBy;
	}
	// 无效值默认返回 'star_count'
	return 'star_count';
}
