/**
 * 统计仪表盘属性测试
 *
 * 使用 fast-check 验证统计仪表盘相关的正确性属性（Properties 15-19）
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
	mapOverviewToCards,
	buildPieChartSectors,
	processTopContentList,
	mapDaysToApiParam,
	mapOrderByToApiParam,
	STATUS_COLORS,
	STATUS_LABELS,
	VALID_DAYS,
	VALID_ORDER_BY,
	TOP_CONTENT_MAX_ITEMS,
} from '../statisticsUtils';
import type { StatisticsOverview, TopContentItem } from '../api';

// ==================== 生成器 ====================

/** 生成任意 StatisticsOverview 数据 */
const statisticsOverviewArb = fc.record({
	knowledge_base_count: fc.nat({ max: 1000000 }),
	persona_card_count: fc.nat({ max: 1000000 }),
	comment_count: fc.nat({ max: 1000000 }),
	star_count: fc.nat({ max: 1000000 }),
	upload_count: fc.nat({ max: 1000000 }),
	download_count: fc.nat({ max: 1000000 }),
});

/** 生成任意审核状态分布数据 */
const distributionArb = fc.record({
	pending: fc.nat({ max: 100000 }),
	approved: fc.nat({ max: 100000 }),
	rejected: fc.nat({ max: 100000 }),
});

/** 生成任意 TopContentItem */
const topContentItemArb = fc.record({
	id: fc.uuid(),
	name: fc.string({ minLength: 1, maxLength: 50 }),
	uploader_name: fc.string({ minLength: 1, maxLength: 20 }),
	star_count: fc.nat({ max: 100000 }),
	downloads: fc.nat({ max: 100000 }),
});

// ==================== 属性 15 ====================

describe('Feature: admin-content-enhancement, Property 15: 概览指标卡片渲染完整性', () => {
	/**
	 * Validates: Requirements 9.2
	 *
	 * 对于任意 StatisticsOverview 数据，mapOverviewToCards 应始终返回6个卡片，
	 * 且每个卡片的数值与对应字段的值一致
	 */
	it('mapOverviewToCards 始终返回6个卡片，数值与字段一致', () => {
		fc.assert(
			fc.property(statisticsOverviewArb, (data: StatisticsOverview) => {
				const cards = mapOverviewToCards(data);

				// 始终返回6个卡片
				expect(cards).toHaveLength(6);

				// 每个卡片都有 field、title 和 value
				for (const card of cards) {
					expect(card).toHaveProperty('field');
					expect(card).toHaveProperty('title');
					expect(card).toHaveProperty('value');
					expect(typeof card.field).toBe('string');
					expect(typeof card.title).toBe('string');
					expect(typeof card.value).toBe('number');
				}

				// 验证每个卡片的数值与对应字段一致
				const fieldValueMap: Record<string, number> = {
					knowledge_base_count: data.knowledge_base_count,
					persona_card_count: data.persona_card_count,
					comment_count: data.comment_count,
					star_count: data.star_count,
					upload_count: data.upload_count,
					download_count: data.download_count,
				};

				for (const card of cards) {
					expect(card.value).toBe(fieldValueMap[card.field]);
				}
			}),
			{ numRuns: 100 }
		);
	});


	it('mapOverviewToCards 返回的卡片覆盖所有6个字段', () => {
		fc.assert(
			fc.property(statisticsOverviewArb, (data: StatisticsOverview) => {
				const cards = mapOverviewToCards(data);
				const fields = cards.map((c) => c.field);

				// 验证覆盖所有6个字段
				expect(fields).toContain('knowledge_base_count');
				expect(fields).toContain('persona_card_count');
				expect(fields).toContain('comment_count');
				expect(fields).toContain('star_count');
				expect(fields).toContain('upload_count');
				expect(fields).toContain('download_count');
			}),
			{ numRuns: 100 }
		);
	});
});

// ==================== 属性 16 ====================

describe('Feature: admin-content-enhancement, Property 16: 审核状态饼图数据与颜色一致性', () => {
	/**
	 * Validates: Requirements 10.1, 10.3, 10.4
	 *
	 * 对于任意 ReviewDistribution 数据，饼图应包含3个扇区，
	 * 颜色分别为待审核黄色、已通过绿色、已拒绝红色，
	 * 百分比之和约等于100（总数为0时百分比均为0）
	 */
	it('buildPieChartSectors 返回3个扇区，颜色正确', () => {
		fc.assert(
			fc.property(distributionArb, (dist) => {
				const sectors = buildPieChartSectors(dist);

				// 始终返回3个扇区
				expect(sectors).toHaveLength(3);

				// 验证颜色与状态对应
				const pendingSector = sectors.find((s) => s.name === STATUS_LABELS.pending);
				const approvedSector = sectors.find((s) => s.name === STATUS_LABELS.approved);
				const rejectedSector = sectors.find((s) => s.name === STATUS_LABELS.rejected);

				expect(pendingSector).toBeDefined();
				expect(approvedSector).toBeDefined();
				expect(rejectedSector).toBeDefined();

				expect(pendingSector!.color).toBe(STATUS_COLORS.pending); // #E6A23C
				expect(approvedSector!.color).toBe(STATUS_COLORS.approved); // #67C23A
				expect(rejectedSector!.color).toBe(STATUS_COLORS.rejected); // #F56C6C
			}),
			{ numRuns: 100 }
		);
	});

	it('buildPieChartSectors 百分比之和约等于100（总数非0时）', () => {
		fc.assert(
			fc.property(
				// 确保至少有一个非零值
				fc.record({
					pending: fc.nat({ max: 100000 }),
					approved: fc.nat({ max: 100000 }),
					rejected: fc.nat({ max: 100000 }),
				}).filter((d) => d.pending + d.approved + d.rejected > 0),
				(dist) => {
					const sectors = buildPieChartSectors(dist);
					const totalPercentage = sectors.reduce((sum, s) => sum + s.percentage, 0);

					// 百分比之和应约等于100（浮点精度容差）
					expect(totalPercentage).toBeCloseTo(100, 5);
				}
			),
			{ numRuns: 100 }
		);
	});

	it('buildPieChartSectors 总数为0时所有百分比均为0', () => {
		const dist = { pending: 0, approved: 0, rejected: 0 };
		const sectors = buildPieChartSectors(dist);

		for (const sector of sectors) {
			expect(sector.percentage).toBe(0);
		}
	});

	it('buildPieChartSectors 每个扇区百分比等于该状态数量除以总数乘以100', () => {
		fc.assert(
			fc.property(
				distributionArb.filter((d) => d.pending + d.approved + d.rejected > 0),
				(dist) => {
					const sectors = buildPieChartSectors(dist);
					const total = dist.pending + dist.approved + dist.rejected;

					for (const sector of sectors) {
						const expectedPercentage = (sector.value / total) * 100;
						expect(sector.percentage).toBeCloseTo(expectedPercentage, 10);
					}
				}
			),
			{ numRuns: 100 }
		);
	});
});

// ==================== 属性 17 ====================

describe('Feature: admin-content-enhancement, Property 17: 趋势图时间范围参数', () => {
	/**
	 * Validates: Requirements 11.4, 15.3
	 *
	 * 对于有效时间范围选择（7、30、90天），mapDaysToApiParam 应返回相同的值
	 */
	it('mapDaysToApiParam(7|30|90) 返回相同的值', () => {
		fc.assert(
			fc.property(
				fc.constantFrom(...VALID_DAYS),
				(days: number) => {
					const result = mapDaysToApiParam(days);
					expect(result).toBe(days);
				}
			),
			{ numRuns: 100 }
		);
	});

	it('mapDaysToApiParam 对无效天数返回默认值30', () => {
		fc.assert(
			fc.property(
				fc.integer({ min: -1000, max: 1000 }).filter((d) => !(VALID_DAYS as readonly number[]).includes(d)),
				(days: number) => {
					const result = mapDaysToApiParam(days);
					expect(result).toBe(30);
				}
			),
			{ numRuns: 100 }
		);
	});
});

// ==================== 属性 18 ====================

describe('Feature: admin-content-enhancement, Property 18: 热门排行榜数据完整性', () => {
	/**
	 * Validates: Requirements 12.1, 12.2
	 *
	 * 对于任意 TopContentItem 数组，processTopContentList 应最多返回10条记录，
	 * 每条记录包含所有必要字段
	 */
	it('processTopContentList 返回最多10条记录', () => {
		fc.assert(
			fc.property(
				fc.array(topContentItemArb, { minLength: 0, maxLength: 30 }),
				(items: TopContentItem[]) => {
					const result = processTopContentList(items);

					// 最多10条
					expect(result.length).toBeLessThanOrEqual(TOP_CONTENT_MAX_ITEMS);

					// 如果原始数据不超过10条，应全部返回
					if (items.length <= TOP_CONTENT_MAX_ITEMS) {
						expect(result.length).toBe(items.length);
					} else {
						expect(result.length).toBe(TOP_CONTENT_MAX_ITEMS);
					}
				}
			),
			{ numRuns: 100 }
		);
	});

	it('processTopContentList 返回的每条记录包含所有必要字段', () => {
		fc.assert(
			fc.property(
				fc.array(topContentItemArb, { minLength: 1, maxLength: 20 }),
				(items: TopContentItem[]) => {
					const result = processTopContentList(items);

					for (const item of result) {
						// 验证所有必要字段存在
						expect(item).toHaveProperty('id');
						expect(item).toHaveProperty('name');
						expect(item).toHaveProperty('uploader_name');
						expect(item).toHaveProperty('star_count');
						expect(item).toHaveProperty('downloads');

						// 验证字段类型
						expect(typeof item.id).toBe('string');
						expect(typeof item.name).toBe('string');
						expect(typeof item.uploader_name).toBe('string');
						expect(typeof item.star_count).toBe('number');
						expect(typeof item.downloads).toBe('number');
					}
				}
			),
			{ numRuns: 100 }
		);
	});

	it('processTopContentList 保持原始顺序（取前10条）', () => {
		fc.assert(
			fc.property(
				fc.array(topContentItemArb, { minLength: 1, maxLength: 20 }),
				(items: TopContentItem[]) => {
					const result = processTopContentList(items);

					// 验证返回的记录与原始数组前 N 条一致
					for (let i = 0; i < result.length; i++) {
						expect(result[i]).toEqual(items[i]);
					}
				}
			),
			{ numRuns: 100 }
		);
	});
});

// ==================== 属性 19 ====================

describe('Feature: admin-content-enhancement, Property 19: 排行榜排序方式参数', () => {
	/**
	 * Validates: Requirements 12.5, 15.4
	 *
	 * 对于有效排序方式选择（star_count/downloads），mapOrderByToApiParam 应返回相同的值
	 */
	it("mapOrderByToApiParam('star_count'|'downloads') 返回相同的值", () => {
		fc.assert(
			fc.property(
				fc.constantFrom(...VALID_ORDER_BY),
				(orderBy: string) => {
					const result = mapOrderByToApiParam(orderBy);
					expect(result).toBe(orderBy);
				}
			),
			{ numRuns: 100 }
		);
	});

	it('mapOrderByToApiParam 对无效排序方式返回默认值 star_count', () => {
		fc.assert(
			fc.property(
				fc.string({ minLength: 1, maxLength: 30 }).filter(
					(s) => !(VALID_ORDER_BY as readonly string[]).includes(s)
				),
				(orderBy: string) => {
					const result = mapOrderByToApiParam(orderBy);
					expect(result).toBe('star_count');
				}
			),
			{ numRuns: 100 }
		);
	});
});
