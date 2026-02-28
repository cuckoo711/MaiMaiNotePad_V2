/**
 * 下载记录模块单元测试
 *
 * 测试范围：
 * - GetStats 统计函数
 * - API 函数的请求参数和 URL 构造
 * - TARGET_TYPE_MAP 目标类型映射
 *
 * 验证需求: 6.3
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../api';
import { TARGET_TYPE_MAP } from '../crud';

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

describe('下载记录模块单元测试', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('apiPrefix 常量', () => {
		it('应该指向正确的下载记录端点', () => {
			expect(api.apiPrefix).toBe('/api/content/admin/downloads/');
		});
	});

	describe('TARGET_TYPE_MAP 目标类型映射 - 需求 12.7, 12.8', () => {
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

	describe('GetList - 获取下载记录列表', () => {
		it('应该使用正确的 URL 和 GET 方法', async () => {
			const query = { page: 1, page_size: 20 };

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				data: { results: [], count: 0 },
			});

			await api.GetList(query);

			expect(request).toHaveBeenCalledWith({
				url: '/api/content/admin/downloads/',
				method: 'get',
				params: query,
			});
		});

		it('应该正确传递搜索参数', async () => {
			const query = {
				page: 1,
				page_size: 20,
				target_type: 'knowledge',
			};

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				data: { results: [], count: 0 },
			});

			await api.GetList(query);

			expect(request).toHaveBeenCalledWith(
				expect.objectContaining({
					params: expect.objectContaining({
						target_type: 'knowledge',
					}),
				})
			);
		});
	});

	describe('GetObj - 获取下载记录详情', () => {
		it('应该使用正确的 URL 和 GET 方法', async () => {
			const id = 'download-uuid-123';

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				data: { id, target_type: 'knowledge' },
			});

			await api.GetObj(id);

			expect(request).toHaveBeenCalledWith({
				url: `/api/content/admin/downloads/${id}/`,
				method: 'get',
			});
		});
	});

	describe('GetStats - 获取下载统计数据 - 需求 6.3', () => {
		it('应该使用正确的 stats URL 和 GET 方法', async () => {
			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				data: { knowledge: 100, persona: 50 },
			});

			await api.GetStats();

			expect(request).toHaveBeenCalledWith({
				url: '/api/content/admin/downloads/stats/',
				method: 'get',
			});
		});

		it('应该不传递任何额外参数', async () => {
			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				data: {},
			});

			await api.GetStats();

			expect(request).toHaveBeenCalledTimes(1);
			const callArgs = vi.mocked(request).mock.calls[0][0] as any;
			expect(callArgs).not.toHaveProperty('params');
			expect(callArgs).not.toHaveProperty('data');
		});
	});
});
