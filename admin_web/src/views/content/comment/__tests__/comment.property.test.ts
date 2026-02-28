/**
 * 评论模块属性测试
 * Feature: admin-content-management
 *
 * 属性 8: 长文本截断一致性 - 验证需求: 3.7
 * 属性 9: 嵌套评论查询正确性 - 验证需求: 3.6
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import { truncateText } from '../crud';
import * as api from '../api';

// 模拟 request 工具函数
vi.mock('/@/utils/service', () => ({
	request: vi.fn(),
}));

import { request } from '/@/utils/service';

describe('评论模块属性测试', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	// Feature: admin-content-management, Property 8
	describe('属性 8: 长文本截断一致性', () => {
		/**
		 * **Validates: Requirements 3.7**
		 * 对于超过 50 字符的文本，截断后长度应不超过 53（50 + '...'）
		 */
		it('超过 maxLength 的文本截断后长度不超过 maxLength + 3', () => {
			fc.assert(
				fc.property(
					fc.string({ minLength: 51, maxLength: 500 }),
					(text) => {
						const result = truncateText(text, 50);
						// 截断后长度应为 50 + '...' = 53
						expect(result.length).toBeLessThanOrEqual(53);
					}
				),
				{ numRuns: 100 }
			);
		});

		/**
		 * **Validates: Requirements 3.7**
		 * 对于 50 字符或更短的文本，应返回原始文本不变
		 */
		it('不超过 maxLength 的文本应返回原始文本', () => {
			fc.assert(
				fc.property(
					fc.string({ minLength: 1, maxLength: 50 }),
					(text) => {
						const result = truncateText(text, 50);
						expect(result).toBe(text);
					}
				),
				{ numRuns: 100 }
			);
		});

		/**
		 * **Validates: Requirements 3.7**
		 * 对于空字符串或 falsy 值，应返回 '-'
		 */
		it('空字符串应返回占位符 "-"', () => {
			expect(truncateText('', 50)).toBe('-');
			expect(truncateText(null as any, 50)).toBe('-');
			expect(truncateText(undefined as any, 50)).toBe('-');
		});

		/**
		 * **Validates: Requirements 3.7**
		 * 截断后的文本应以原始文本的前 maxLength 个字符开头
		 */
		it('截断结果应以原始文本的前 maxLength 个字符开头', () => {
			fc.assert(
				fc.property(
					fc.string({ minLength: 51, maxLength: 500 }),
					fc.integer({ min: 10, max: 100 }),
					(text, maxLength) => {
						const result = truncateText(text, maxLength);
						if (text.length > maxLength) {
							// 截断后应以原始文本的前 maxLength 个字符开头
							expect(result.startsWith(text.substring(0, maxLength))).toBe(true);
							// 截断后应以 '...' 结尾
							expect(result.endsWith('...')).toBe(true);
						} else {
							expect(result).toBe(text);
						}
					}
				),
				{ numRuns: 100 }
			);
		});
	});

	// Feature: admin-content-management, Property 9
	describe('属性 9: 嵌套评论查询正确性', () => {
		/**
		 * **Validates: Requirements 3.6**
		 * 对于任何评论 ID，GetReplies 应使用 parent 参数查询
		 */
		it('GetReplies 应使用 parent 参数查询指定评论的回复', async () => {
			await fc.assert(
				fc.asyncProperty(
					fc.uuid(),
					async (commentId) => {
						// 模拟返回的回复列表，所有回复的 parent 都指向查询的评论 ID
						const mockReplies = Array.from({ length: 3 }, (_, i) => ({
							id: fc.sample(fc.uuid(), 1)[0],
							user: i + 1,
							target_id: fc.sample(fc.uuid(), 1)[0],
							target_type: 'knowledge' as const,
							parent: commentId,
							content: `回复内容 ${i}`,
							is_deleted: false,
							like_count: 0,
							dislike_count: 0,
							create_datetime: new Date().toISOString(),
							update_datetime: new Date().toISOString(),
						}));

						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '获取成功',
							data: { results: mockReplies, count: mockReplies.length },
						});

						// 执行查询
						const response = await api.GetReplies(commentId);
						const replies = response.data.results;

						// 验证：request 被调用时 params 包含 parent 参数
						expect(request).toHaveBeenCalledWith(
							expect.objectContaining({
								params: { parent: commentId },
							})
						);

						// 验证：所有返回的回复的 parent 字段都指向查询的评论 ID
						for (const reply of replies) {
							expect(reply.parent).toBe(commentId);
						}
					}
				),
				{ numRuns: 100 }
			);
		});
	});
});
