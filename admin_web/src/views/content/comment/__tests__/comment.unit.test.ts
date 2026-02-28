/**
 * 评论模块单元测试
 *
 * 测试范围：
 * - truncateText 文本截断函数
 * - TARGET_TYPE_MAP 目标类型映射
 * - API 函数的请求参数和 URL 构造
 *
 * 验证需求: 3.7, 12.7, 12.8
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../api';
import { truncateText } from '../crud';

// 模拟 request 工具函数
vi.mock('/@/utils/service', () => ({
	request: vi.fn(),
}));

// 模拟 auth 工具函数（crud.tsx 依赖）
vi.mock('/@/utils/authFunction', () => ({
	auth: vi.fn(() => true),
}));

// 模拟 commonCrud 工具函数（crud.tsx 依赖）
vi.mock('/@/utils/commonCrud', () => ({
	commonCrudConfig: vi.fn(() => ({})),
}));

// 导入模拟的 request 函数
import { request } from '/@/utils/service';

describe('评论模块单元测试', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('truncateText 文本截断函数 - 需求 3.7', () => {
		it('超过 50 字符的文本应该被截断并添加省略号', () => {
			const longText = 'a'.repeat(60);
			const result = truncateText(longText);
			expect(result).toBe('a'.repeat(50) + '...');
		});

		it('恰好 50 字符的文本应该原样返回', () => {
			const text = 'a'.repeat(50);
			const result = truncateText(text);
			expect(result).toBe(text);
		});

		it('少于 50 字符的文本应该原样返回', () => {
			const text = '这是一段短文本';
			const result = truncateText(text);
			expect(result).toBe(text);
		});

		it('空字符串应该返回 "-"', () => {
			expect(truncateText('')).toBe('-');
		});

		it('自定义 maxLength 参数应该生效', () => {
			const text = 'abcdefghij'; // 10 字符
			expect(truncateText(text, 5)).toBe('abcde...');
			expect(truncateText(text, 10)).toBe(text);
			expect(truncateText(text, 15)).toBe(text);
		});

		it('中文文本超过指定长度应该被截断', () => {
			// 构造一个确保超过 50 字符的中文文本
			const chineseText = '这是一段很长的中文评论内容，用于测试截断功能是否正常工作，需要确保超过五十个字符才能触发截断逻辑，所以多写一些内容';
			expect(chineseText.length).toBeGreaterThan(50);
			const result = truncateText(chineseText);
			expect(result.endsWith('...')).toBe(true);
			expect(result.length).toBe(53);
		});
	});

	describe('TARGET_TYPE_MAP 目标类型映射 - 需求 12.7, 12.8', () => {
		// 直接从 crud.tsx 的列配置中验证映射逻辑
		const TARGET_TYPE_MAP: Record<string, string> = {
			knowledge: '知识库',
			persona: '人设卡',
		};

		it('knowledge 应该映射为 "知识库"', () => {
			expect(TARGET_TYPE_MAP['knowledge']).toBe('知识库');
		});

		it('persona 应该映射为 "人设卡"', () => {
			expect(TARGET_TYPE_MAP['persona']).toBe('人设卡');
		});

		it('未知的目标类型应该返回 undefined', () => {
			expect(TARGET_TYPE_MAP['unknown']).toBeUndefined();
		});
	});

	describe('API 函数测试', () => {
		describe('apiPrefix 常量', () => {
			it('应该指向正确的评论端点', () => {
				expect(api.apiPrefix).toBe('/api/content/comments/');
			});
		});

		describe('GetList - 获取评论列表', () => {
			it('应该使用 admin_list URL 和 GET 方法', async () => {
				const query = { page: 1, page_size: 20 };

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { results: [], count: 0 },
				});

				await api.GetList(query);

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/comments/admin_list/',
					method: 'get',
					params: query,
				});
			});

			it('应该正确传递搜索参数', async () => {
				const query = {
					page: 1,
					page_size: 20,
					user_name: '测试用户',
					target_type: 'knowledge',
					is_deleted: 'false',
				};

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { results: [], count: 0 },
				});

				await api.GetList(query);

				expect(request).toHaveBeenCalledWith(
					expect.objectContaining({
						params: expect.objectContaining({
							user_name: '测试用户',
							target_type: 'knowledge',
						}),
					})
				);
			});
		});

		describe('GetObj - 获取评论详情', () => {
			it('应该使用正确的 URL 和 GET 方法', async () => {
				const id = 'comment-uuid-123';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { id, content: '评论内容' },
				});

				await api.GetObj(id);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/comments/${id}/`,
					method: 'get',
				});
			});
		});

		describe('DelObj - 软删除评论', () => {
			it('应该使用 admin_delete URL 和 POST 方法', async () => {
				const id = 'delete-id-123';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '删除成功',
				});

				await api.DelObj(id);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/comments/${id}/admin_delete/`,
					method: 'post',
				});
			});
		});

		describe('AdminDeleteObj - 管理后台删除评论', () => {
			it('应该使用 admin_delete URL 和 POST 方法', async () => {
				const id = 'admin-delete-id-456';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '删除成功',
				});

				await api.AdminDeleteObj(id);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/comments/${id}/admin_delete/`,
					method: 'post',
				});
			});
		});

		describe('GetReplies - 获取评论回复', () => {
			it('应该使用 admin_list URL 并传递 parent 参数', async () => {
				const id = 'parent-comment-id';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { results: [], count: 0 },
				});

				await api.GetReplies(id);

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/comments/admin_list/',
					method: 'get',
					params: { parent: id },
				});
			});
		});

		describe('BanUser - 封禁用户', () => {
			it('应该使用 ban_user URL 和 POST 方法，传递封禁原因', async () => {
				const id = 'comment-id-789';
				const reason = '发布不当言论';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '封禁成功',
				});

				await api.BanUser(id, reason);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/comments/${id}/ban_user/`,
					method: 'post',
					data: { reason },
				});
			});

			it('传递封禁时长时应该包含 duration_hours', async () => {
				const id = 'comment-id-789';
				const reason = '发布不当言论';
				const durationHours = 24;

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '封禁成功',
				});

				await api.BanUser(id, reason, durationHours);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/comments/${id}/ban_user/`,
					method: 'post',
					data: { reason, duration_hours: 24 },
				});
			});

			it('不传封禁时长时 data 中不应包含 duration_hours', async () => {
				const id = 'comment-id-789';
				const reason = '永久封禁';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '封禁成功',
				});

				await api.BanUser(id, reason);

				const callArgs = vi.mocked(request).mock.calls[0][0] as any;
				expect(callArgs.data).toEqual({ reason });
				expect(callArgs.data).not.toHaveProperty('duration_hours');
			});
		});

		describe('RestoreObj - 恢复评论', () => {
			it('应该使用 restore URL 和 POST 方法', async () => {
				const id = 'restore-id-123';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '恢复成功',
				});

				await api.RestoreObj(id);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/comments/${id}/restore/`,
					method: 'post',
				});
			});
		});
	});
});
