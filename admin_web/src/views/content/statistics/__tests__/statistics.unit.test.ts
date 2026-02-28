/**
 * 统计仪表盘单元测试
 *
 * 测试范围：
 * - 统计 API 函数的 URL 和参数构造
 * - 概览指标卡片的数据渲染和加载失败状态
 * - 饼图颜色映射和百分比计算
 * - 折线图时间范围切换
 * - 排行榜排序切换和数据显示
 * - 各组件独立加载和错误处理
 *
 * 验证需求: 9.2, 9.3, 9.4, 9.5, 10.1, 10.3, 10.4, 11.1, 11.4, 11.5,
 *           12.1, 12.2, 12.4, 12.5, 15.1, 15.2, 15.3, 15.4, 15.5
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../api';
import {
	mapOverviewToCards,
	buildPieChartSectors,
	processTopContentList,
	mapDaysToApiParam,
	mapOrderByToApiParam,
	STATUS_COLORS,
	STATUS_LABELS,
	TOP_CONTENT_MAX_ITEMS,
} from '../statisticsUtils';
import type { StatisticsOverview, TopContentItem } from '../api';

// 模拟 request 工具函数
vi.mock('/@/utils/service', () => ({
	request: vi.fn(),
}));

import { request } from '/@/utils/service';

describe('统计仪表盘单元测试', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	// ==================== 1. API 函数测试 ====================

	describe('API 函数 - URL 和参数构造', () => {
		describe('getOverview - 需求 15.1', () => {
			it('应该调用 GET /api/content/statistics/overview/', async () => {
				vi.mocked(request).mockResolvedValueOnce({
					knowledge_base_count: 100,
					persona_card_count: 50,
					comment_count: 200,
					star_count: 300,
					upload_count: 80,
					download_count: 150,
				});

				await api.getOverview();

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/statistics/overview/',
					method: 'get',
				});
			});
		});

		describe('getReviewDistribution - 需求 15.2', () => {
			it('应该调用 GET /api/content/statistics/review-distribution/', async () => {
				vi.mocked(request).mockResolvedValueOnce({
					knowledge_base: { pending: 10, approved: 80, rejected: 10 },
					persona_card: { pending: 5, approved: 40, rejected: 5 },
				});

				await api.getReviewDistribution();

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/statistics/review-distribution/',
					method: 'get',
				});
			});
		});

		describe('getTrends - 需求 15.3', () => {
			it('传入 days=30 时应该携带 params { days: 30 }', async () => {
				vi.mocked(request).mockResolvedValueOnce({ data: [] });

				await api.getTrends(30);

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/statistics/trends/',
					method: 'get',
					params: { days: 30 },
				});
			});

			it('不传 days 参数时 params 应为空对象', async () => {
				vi.mocked(request).mockResolvedValueOnce({ data: [] });

				await api.getTrends();

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/statistics/trends/',
					method: 'get',
					params: {},
				});
			});
		});

		describe('getTopContent - 需求 15.4, 15.5', () => {
			it("传入 orderBy='star_count', limit=10 时应该携带对应 params", async () => {
				vi.mocked(request).mockResolvedValueOnce({
					knowledge_base: [],
					persona_card: [],
				});

				await api.getTopContent('star_count', 10);

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/statistics/top-content/',
					method: 'get',
					params: { order_by: 'star_count', limit: 10 },
				});
			});

			it('不传参数时 params 应为空对象', async () => {
				vi.mocked(request).mockResolvedValueOnce({
					knowledge_base: [],
					persona_card: [],
				});

				await api.getTopContent();

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/statistics/top-content/',
					method: 'get',
					params: {},
				});
			});
		});

		describe('API 错误传播 - 需求 15.5', () => {
			it('getOverview 应该正确传播错误', async () => {
				vi.mocked(request).mockRejectedValueOnce(new Error('网络错误'));

				await expect(api.getOverview()).rejects.toThrow('网络错误');
			});

			it('getReviewDistribution 应该正确传播错误', async () => {
				vi.mocked(request).mockRejectedValueOnce(new Error('服务器错误'));

				await expect(api.getReviewDistribution()).rejects.toThrow('服务器错误');
			});

			it('getTrends 应该正确传播错误', async () => {
				vi.mocked(request).mockRejectedValueOnce(new Error('超时'));

				await expect(api.getTrends(7)).rejects.toThrow('超时');
			});

			it('getTopContent 应该正确传播错误', async () => {
				vi.mocked(request).mockRejectedValueOnce(new Error('权限不足'));

				await expect(api.getTopContent('star_count', 10)).rejects.toThrow('权限不足');
			});
		});
	});

	// ==================== 2. 工具函数测试 ====================

	describe('mapOverviewToCards - 需求 9.2, 9.3, 9.4, 9.5', () => {
		it('传入具体数据时应返回正确的卡片值', () => {
			const data: StatisticsOverview = {
				knowledge_base_count: 120,
				persona_card_count: 45,
				comment_count: 300,
				star_count: 500,
				upload_count: 88,
				download_count: 200,
			};

			const cards = mapOverviewToCards(data);

			expect(cards).toHaveLength(6);
			expect(cards.find((c) => c.field === 'knowledge_base_count')?.value).toBe(120);
			expect(cards.find((c) => c.field === 'persona_card_count')?.value).toBe(45);
			expect(cards.find((c) => c.field === 'comment_count')?.value).toBe(300);
			expect(cards.find((c) => c.field === 'star_count')?.value).toBe(500);
			expect(cards.find((c) => c.field === 'upload_count')?.value).toBe(88);
			expect(cards.find((c) => c.field === 'download_count')?.value).toBe(200);
		});

		it('所有值为 0 时应返回 value 为 0 的卡片', () => {
			const data: StatisticsOverview = {
				knowledge_base_count: 0,
				persona_card_count: 0,
				comment_count: 0,
				star_count: 0,
				upload_count: 0,
				download_count: 0,
			};

			const cards = mapOverviewToCards(data);

			expect(cards).toHaveLength(6);
			for (const card of cards) {
				expect(card.value).toBe(0);
			}
		});

		it('每个卡片应包含中文标题', () => {
			const data: StatisticsOverview = {
				knowledge_base_count: 1,
				persona_card_count: 1,
				comment_count: 1,
				star_count: 1,
				upload_count: 1,
				download_count: 1,
			};

			const cards = mapOverviewToCards(data);
			const titles = cards.map((c) => c.title);

			expect(titles).toContain('知识库总数');
			expect(titles).toContain('人设卡总数');
			expect(titles).toContain('评论总数');
			expect(titles).toContain('收藏总数');
			expect(titles).toContain('上传总数');
			expect(titles).toContain('下载总数');
		});
	});

	describe('buildPieChartSectors - 需求 10.1, 10.3, 10.4', () => {
		it('传入 {pending: 50, approved: 30, rejected: 20} 应返回正确百分比', () => {
			const sectors = buildPieChartSectors({ pending: 50, approved: 30, rejected: 20 });

			expect(sectors).toHaveLength(3);

			const pendingSector = sectors.find((s) => s.name === STATUS_LABELS.pending)!;
			const approvedSector = sectors.find((s) => s.name === STATUS_LABELS.approved)!;
			const rejectedSector = sectors.find((s) => s.name === STATUS_LABELS.rejected)!;

			expect(pendingSector.percentage).toBe(50);
			expect(approvedSector.percentage).toBe(30);
			expect(rejectedSector.percentage).toBe(20);
		});

		it('颜色映射应正确：待审核黄色、已通过绿色、已拒绝红色', () => {
			const sectors = buildPieChartSectors({ pending: 10, approved: 20, rejected: 30 });

			const pendingSector = sectors.find((s) => s.name === STATUS_LABELS.pending)!;
			const approvedSector = sectors.find((s) => s.name === STATUS_LABELS.approved)!;
			const rejectedSector = sectors.find((s) => s.name === STATUS_LABELS.rejected)!;

			expect(pendingSector.color).toBe('#E6A23C');
			expect(approvedSector.color).toBe('#67C23A');
			expect(rejectedSector.color).toBe('#F56C6C');
		});

		it('所有值为 0 时百分比应全部为 0', () => {
			const sectors = buildPieChartSectors({ pending: 0, approved: 0, rejected: 0 });

			for (const sector of sectors) {
				expect(sector.percentage).toBe(0);
			}
		});

		it('只有一个状态有值时该状态百分比应为 100', () => {
			const sectors = buildPieChartSectors({ pending: 0, approved: 100, rejected: 0 });

			const approvedSector = sectors.find((s) => s.name === STATUS_LABELS.approved)!;
			expect(approvedSector.percentage).toBe(100);

			const pendingSector = sectors.find((s) => s.name === STATUS_LABELS.pending)!;
			const rejectedSector = sectors.find((s) => s.name === STATUS_LABELS.rejected)!;
			expect(pendingSector.percentage).toBe(0);
			expect(rejectedSector.percentage).toBe(0);
		});
	});

	describe('processTopContentList - 需求 12.1, 12.2', () => {
		// 辅助函数：生成测试用的 TopContentItem
		const makeItem = (index: number): TopContentItem => ({
			id: `id-${index}`,
			name: `内容-${index}`,
			uploader_name: `用户-${index}`,
			star_count: 100 - index,
			downloads: 200 - index,
		});

		it('传入 15 条数据应只返回 10 条', () => {
			const items = Array.from({ length: 15 }, (_, i) => makeItem(i));
			const result = processTopContentList(items);

			expect(result).toHaveLength(TOP_CONTENT_MAX_ITEMS);
		});

		it('传入 5 条数据应全部返回', () => {
			const items = Array.from({ length: 5 }, (_, i) => makeItem(i));
			const result = processTopContentList(items);

			expect(result).toHaveLength(5);
			expect(result).toEqual(items);
		});

		it('传入空数组应返回空数组', () => {
			const result = processTopContentList([]);

			expect(result).toHaveLength(0);
			expect(result).toEqual([]);
		});
	});

	describe('mapDaysToApiParam - 需求 11.4, 11.5', () => {
		it('mapDaysToApiParam(7) 应返回 7', () => {
			expect(mapDaysToApiParam(7)).toBe(7);
		});

		it('mapDaysToApiParam(30) 应返回 30', () => {
			expect(mapDaysToApiParam(30)).toBe(30);
		});

		it('mapDaysToApiParam(90) 应返回 90', () => {
			expect(mapDaysToApiParam(90)).toBe(90);
		});

		it('mapDaysToApiParam(15) 应返回默认值 30', () => {
			expect(mapDaysToApiParam(15)).toBe(30);
		});
	});

	describe('mapOrderByToApiParam - 需求 12.4, 12.5', () => {
		it("mapOrderByToApiParam('star_count') 应返回 'star_count'", () => {
			expect(mapOrderByToApiParam('star_count')).toBe('star_count');
		});

		it("mapOrderByToApiParam('downloads') 应返回 'downloads'", () => {
			expect(mapOrderByToApiParam('downloads')).toBe('downloads');
		});

		it("mapOrderByToApiParam('invalid') 应返回默认值 'star_count'", () => {
			expect(mapOrderByToApiParam('invalid')).toBe('star_count');
		});
	});
});
