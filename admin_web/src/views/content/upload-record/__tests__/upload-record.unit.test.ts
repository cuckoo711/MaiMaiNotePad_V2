/**
 * 上传记录模块单元测试
 *
 * 测试范围：
 * - 审核函数（ApproveObj、RejectObj）
 * - API 函数的请求参数和 URL 构造
 * - TARGET_TYPE_MAP 目标类型映射
 * - STATUS_MAP 审核状态映射
 *
 * 验证需求: 5.4, 5.6
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../api';
import { TARGET_TYPE_MAP, STATUS_MAP } from '../crud';

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

// 模拟 element-plus（crud.tsx 依赖 ElMessageBox）
vi.mock('element-plus', () => ({
	ElMessageBox: {
		confirm: vi.fn(),
		prompt: vi.fn(),
	},
}));

// 导入模拟的 request 函数
import { request } from '/@/utils/service';

describe('上传记录模块单元测试', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('apiPrefix 常量', () => {
		it('应该指向正确的上传记录端点', () => {
			expect(api.apiPrefix).toBe('/api/content/users/uploads/');
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

	describe('STATUS_MAP 审核状态映射 - 需求 12.2, 12.3, 12.4', () => {
		it('pending 应该映射为待审核（warning）', () => {
			expect(STATUS_MAP['pending']).toEqual({ label: '待审核', color: 'warning' });
		});

		it('approved 应该映射为已通过（success）', () => {
			expect(STATUS_MAP['approved']).toEqual({ label: '已通过', color: 'success' });
		});

		it('rejected 应该映射为已拒绝（danger）', () => {
			expect(STATUS_MAP['rejected']).toEqual({ label: '已拒绝', color: 'danger' });
		});

		it('未知的审核状态应该返回 undefined', () => {
			expect(STATUS_MAP['unknown']).toBeUndefined();
		});
	});

	describe('GetList - 获取上传记录列表', () => {
		it('应该使用正确的 URL 和 GET 方法', async () => {
			const query = { page: 1, page_size: 20 };

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				data: { results: [], count: 0 },
			});

			await api.GetList(query);

			expect(request).toHaveBeenCalledWith({
				url: '/api/content/users/uploads/',
				method: 'get',
				params: query,
			});
		});

		it('应该正确传递搜索参数', async () => {
			const query = {
				page: 1,
				page_size: 20,
				uploader_name: '测试用户',
				target_type: 'knowledge',
				status: 'pending',
			};

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				data: { results: [], count: 0 },
			});

			await api.GetList(query);

			expect(request).toHaveBeenCalledWith(
				expect.objectContaining({
					params: expect.objectContaining({
						uploader_name: '测试用户',
						target_type: 'knowledge',
						status: 'pending',
					}),
				})
			);
		});
	});

	describe('GetObj - 获取上传记录详情', () => {
		it('应该使用正确的 URL 和 GET 方法', async () => {
			const id = 'upload-uuid-123';

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				data: { id, target_type: 'knowledge', status: 'pending' },
			});

			await api.GetObj(id);

			expect(request).toHaveBeenCalledWith({
				url: `/api/content/users/uploads/${id}/`,
				method: 'get',
			});
		});
	});

	describe('ApproveObj - 审核通过 - 需求 5.4', () => {
		it('应该使用正确的审核通过 URL 和 POST 方法', async () => {
			const id = 'approve-id-789';

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				msg: '审核通过',
			});

			await api.ApproveObj(id);

			expect(request).toHaveBeenCalledWith({
				url: `/api/content/review/${id}/approve/`,
				method: 'post',
			});
		});

		it('不应该传递 data 参数', async () => {
			const id = 'approve-no-data';

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				msg: '审核通过',
			});

			await api.ApproveObj(id);

			const callArgs = vi.mocked(request).mock.calls[0][0] as any;
			expect(callArgs).not.toHaveProperty('data');
		});
	});

	describe('RejectObj - 审核拒绝 - 需求 5.6', () => {
		it('应该使用正确的审核拒绝 URL 和 POST 方法', async () => {
			const id = 'reject-id-456';
			const reason = '内容不符合规范';

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				msg: '审核拒绝',
			});

			await api.RejectObj(id, reason);

			expect(request).toHaveBeenCalledWith({
				url: `/api/content/review/${id}/reject/`,
				method: 'post',
				data: { reason },
			});
		});

		it('应该正确传递拒绝原因', async () => {
			const id = 'reject-reason-test';
			const reason = '包含违规内容，请修改后重新提交';

			vi.mocked(request).mockResolvedValueOnce({
				code: 2000,
				msg: '审核拒绝',
			});

			await api.RejectObj(id, reason);

			const callArgs = vi.mocked(request).mock.calls[0][0] as any;
			expect(callArgs.data).toEqual({ reason: '包含违规内容，请修改后重新提交' });
		});
	});
});
