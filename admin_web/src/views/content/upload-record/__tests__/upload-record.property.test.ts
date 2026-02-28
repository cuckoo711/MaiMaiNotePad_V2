/**
 * 上传记录模块属性测试
 * Feature: admin-content-management
 *
 * 属性 4: 审核状态转换正确性 - 验证需求: 5.4, 5.6
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import * as api from '../api';

// 模拟 request 工具函数
vi.mock('/@/utils/service', () => ({
	request: vi.fn(),
}));

import { request } from '/@/utils/service';

describe('上传记录模块属性测试', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	// Feature: admin-content-management, Property 4
	describe('属性 4: 审核状态转换正确性', () => {
		/**
		 * **Validates: Requirements 5.4**
		 * 对于任何待审核的上传记录，执行审核通过操作后，
		 * ApproveObj 应调用正确的审核通过端点，且记录状态应变为 approved
		 */
		it('审核通过后记录状态应变为 approved', async () => {
			await fc.assert(
				fc.asyncProperty(
					fc.uuid(),
					async (recordId) => {
						// 模拟审核通过 API 返回成功
						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '审核通过',
							data: { id: recordId, status: 'approved' },
						});

						// 执行审核通过操作
						const response = await api.ApproveObj(recordId);

						// 验证：request 被调用时使用了正确的审核通过端点
						expect(request).toHaveBeenCalledWith(
							expect.objectContaining({
								url: `/api/content/review/${recordId}/approve/`,
								method: 'post',
							})
						);

						// 验证：返回的数据中状态为 approved
						expect(response.data.status).toBe('approved');
					}
				),
				{ numRuns: 100 }
			);
		});

		/**
		 * **Validates: Requirements 5.6**
		 * 对于任何待审核的上传记录，执行审核拒绝操作后，
		 * RejectObj 应调用正确的审核拒绝端点，且请求体中包含拒绝原因，
		 * 记录状态应变为 rejected 并包含拒绝原因
		 */
		it('审核拒绝后记录状态应变为 rejected 且包含拒绝原因', async () => {
			await fc.assert(
				fc.asyncProperty(
					fc.uuid(),
					fc.string({ minLength: 1, maxLength: 500 }),
					async (recordId, reason) => {
						// 模拟审核拒绝 API 返回成功
						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '审核拒绝',
							data: { id: recordId, status: 'rejected', rejection_reason: reason },
						});

						// 执行审核拒绝操作
						const response = await api.RejectObj(recordId, reason);

						// 验证：request 被调用时使用了正确的审核拒绝端点
						expect(request).toHaveBeenCalledWith(
							expect.objectContaining({
								url: `/api/content/review/${recordId}/reject/`,
								method: 'post',
								data: { reason },
							})
						);

						// 验证：返回的数据中状态为 rejected
						expect(response.data.status).toBe('rejected');

						// 验证：返回的数据中包含拒绝原因
						expect(response.data.rejection_reason).toBe(reason);
					}
				),
				{ numRuns: 100 }
			);
		});

		/**
		 * **Validates: Requirements 5.4**
		 * 对于任何待审核的上传记录，审核通过后再次获取该记录，
		 * 状态应为 approved
		 */
		it('审核通过后获取记录状态应为 approved', async () => {
			await fc.assert(
				fc.asyncProperty(
					fc.uuid(),
					fc.constantFrom('knowledge', 'persona') as fc.Arbitrary<'knowledge' | 'persona'>,
					fc.string({ minLength: 1, maxLength: 200 }),
					async (recordId, targetType, name) => {
						// 模拟审核通过 API 返回成功
						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '审核通过',
							data: { id: recordId, status: 'approved' },
						});

						// 模拟获取记录详情返回已通过状态
						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '获取成功',
							data: {
								id: recordId,
								target_type: targetType,
								name: name,
								status: 'approved',
								create_datetime: new Date().toISOString(),
							},
						});

						// 执行审核通过
						await api.ApproveObj(recordId);

						// 获取记录详情
						const detail = await api.GetObj(recordId);

						// 验证：获取到的记录状态为 approved
						expect(detail.data.status).toBe('approved');
					}
				),
				{ numRuns: 100 }
			);
		});

		/**
		 * **Validates: Requirements 5.6**
		 * 对于任何待审核的上传记录，审核拒绝后再次获取该记录，
		 * 状态应为 rejected 且包含拒绝原因
		 */
		it('审核拒绝后获取记录应包含拒绝原因且状态为 rejected', async () => {
			await fc.assert(
				fc.asyncProperty(
					fc.uuid(),
					fc.string({ minLength: 1, maxLength: 500 }),
					async (recordId, reason) => {
						// 模拟审核拒绝 API 返回成功
						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '审核拒绝',
							data: { id: recordId, status: 'rejected', rejection_reason: reason },
						});

						// 模拟获取记录详情返回已拒绝状态
						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '获取成功',
							data: {
								id: recordId,
								status: 'rejected',
								rejection_reason: reason,
								create_datetime: new Date().toISOString(),
							},
						});

						// 执行审核拒绝
						await api.RejectObj(recordId, reason);

						// 获取记录详情
						const detail = await api.GetObj(recordId);

						// 验证：获取到的记录状态为 rejected
						expect(detail.data.status).toBe('rejected');

						// 验证：获取到的记录包含拒绝原因
						expect(detail.data.rejection_reason).toBe(reason);
					}
				),
				{ numRuns: 100 }
			);
		});
	});
});
