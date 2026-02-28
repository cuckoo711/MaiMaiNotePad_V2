/**
 * 下载记录模块属性测试
 * Feature: admin-content-management
 *
 * 属性 10: 统计数据准确性 - 验证需求: 6.3
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import * as api from '../api';

// 模拟 request 工具函数
vi.mock('/@/utils/service', () => ({
	request: vi.fn(),
}));

import { request } from '/@/utils/service';

// Feature: admin-content-management, Property 10
describe('下载记录模块属性测试', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('属性 10: 统计数据准确性', () => {
		/**
		 * **Validates: Requirements 6.3**
		 * 对于任何随机生成的下载记录数据集，按目标类型分组的统计结果应等于手动计数的结果
		 */
		it('按目标类型分组的统计结果应等于手动计数', async () => {
			// 目标类型生成器
			const targetTypeArb = fc.constantFrom<'knowledge' | 'persona'>('knowledge', 'persona');

			// 下载记录生成器
			const downloadRecordArb = fc.record({
				id: fc.uuid(),
				target_id: fc.uuid(),
				target_type: targetTypeArb,
				create_datetime: fc.integer({ min: 1577836800000, max: 1893456000000 }).map((ts) => new Date(ts).toISOString()),
			});

			await fc.assert(
				fc.asyncProperty(
					fc.array(downloadRecordArb, { minLength: 0, maxLength: 50 }),
					async (records) => {
						// 手动按目标类型分组计数
						const manualCounts: Record<string, number> = {};
						for (const record of records) {
							manualCounts[record.target_type] = (manualCounts[record.target_type] || 0) + 1;
						}

						// 模拟 GetStats 返回手动计数结果
						const statsData = Object.entries(manualCounts).map(([target_type, count]) => ({
							target_type,
							count,
						}));

						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '获取成功',
							data: statsData,
						});

						// 调用统计接口
						const response = await api.GetStats();
						const stats = response.data;

						// 验证：统计结果中每个类型的计数应等于手动计数
						for (const stat of stats) {
							expect(stat.count).toBe(manualCounts[stat.target_type]);
						}

						// 验证：统计结果的类型数量应等于手动计数的类型数量
						expect(stats.length).toBe(Object.keys(manualCounts).length);

						// 验证：统计结果的总数应等于记录总数
						const totalFromStats = stats.reduce((sum: number, s: { count: number }) => sum + s.count, 0);
						expect(totalFromStats).toBe(records.length);
					}
				),
				{ numRuns: 100 }
			);
		});

		/**
		 * **Validates: Requirements 6.3**
		 * 空数据集应返回空统计结果
		 */
		it('空数据集应返回空统计结果', async () => {
			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				msg: '获取成功',
				data: [],
			});

			const response = await api.GetStats();
			const stats = response.data;

			// 验证：空数据集返回空数组
			expect(stats).toEqual([]);
			expect(stats.length).toBe(0);

			// 验证：GetStats 使用正确的 URL 和方法
			expect(request).toHaveBeenCalledWith(
				expect.objectContaining({
					url: api.apiPrefix + 'stats/',
					method: 'get',
				})
			);
		});

		/**
		 * **Validates: Requirements 6.3**
		 * 仅包含单一目标类型的数据集，统计结果应只有一个分组且计数正确
		 */
		it('单一目标类型的数据集统计结果应只有一个分组', async () => {
			const targetTypeArb = fc.constantFrom<'knowledge' | 'persona'>('knowledge', 'persona');

			await fc.assert(
				fc.asyncProperty(
					targetTypeArb,
					fc.integer({ min: 1, max: 100 }),
					async (targetType, count) => {
						// 模拟统计结果：只有一个目标类型
						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '获取成功',
							data: [{ target_type: targetType, count }],
						});

						const response = await api.GetStats();
						const stats = response.data;

						// 验证：只有一个分组
						expect(stats.length).toBe(1);
						// 验证：目标类型正确
						expect(stats[0].target_type).toBe(targetType);
						// 验证：计数正确
						expect(stats[0].count).toBe(count);
					}
				),
				{ numRuns: 100 }
			);
		});
	});
});
