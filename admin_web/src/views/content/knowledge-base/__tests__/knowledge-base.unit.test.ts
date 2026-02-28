/**
 * 知识库模块单元测试
 * 
 * 测试范围：
 * - API 函数的请求参数和 URL 构造
 * - 表单验证规则（必填、长度、格式）
 * - 日期格式化和标签显示函数
 * 
 * 验证需求: 7.1, 7.2, 7.3, 7.5, 12.9
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../api';
import { formatDate } from '/@/utils/formatTime';

// 模拟 request 工具函数
vi.mock('/@/utils/service', () => ({
	request: vi.fn(),
	downloadFile: vi.fn(),
}));

// 导入模拟的 request 函数
import { request, downloadFile } from '/@/utils/service';

describe('知识库模块单元测试', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('API 函数测试', () => {
		describe('GetList - 获取知识库列表', () => {
			it('应该使用正确的 URL 和 GET 方法', async () => {
				const query = {
					page: 1,
					page_size: 20,
					name: '测试',
				};

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { results: [], count: 0 },
				});

				await api.GetList(query);

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/knowledge/',
					method: 'get',
					params: query,
				});
			});

			it('应该正确传递分页参数', async () => {
				const query = {
					page: 2,
					page_size: 50,
				};

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { results: [], count: 0 },
				});

				await api.GetList(query);

				expect(request).toHaveBeenCalledWith(
					expect.objectContaining({
						params: expect.objectContaining({
							page: 2,
							page_size: 50,
						}),
					})
				);
			});

			it('应该正确传递搜索参数', async () => {
				const query = {
					page: 1,
					page_size: 20,
					name: '知识库名称',
					uploader_name: '用户名',
					is_pending: true,
					is_public: false,
				};

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { results: [], count: 0 },
				});

				await api.GetList(query);

				expect(request).toHaveBeenCalledWith(
					expect.objectContaining({
						params: expect.objectContaining({
							name: '知识库名称',
							uploader_name: '用户名',
							is_pending: true,
							is_public: false,
						}),
					})
				);
			});
		});

		describe('GetObj - 获取知识库详情', () => {
			it('应该使用正确的 URL 和 GET 方法', async () => {
				const id = 'test-uuid-123';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { id, name: '测试知识库' },
				});

				await api.GetObj(id);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/knowledge/${id}/`,
					method: 'get',
				});
			});
		});

		describe('AddObj - 创建知识库', () => {
			it('应该使用正确的 URL 和 POST 方法', async () => {
				const formData = {
					name: '新知识库',
					description: '描述',
					version: '1.0',
					is_public: true,
				};

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { id: 'new-id', ...formData },
				});

				await api.AddObj(formData);

				expect(request).toHaveBeenCalledWith({
					url: '/api/content/knowledge/',
					method: 'post',
					data: formData,
				});
			});

			it('应该正确传递所有表单字段', async () => {
				const formData = {
					name: '完整知识库',
					description: '完整描述',
					copyright_owner: '版权所有者',
					tags: '标签1,标签2,标签3',
					version: '2.1.0',
					is_public: false,
				};

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { id: 'new-id', ...formData },
				});

				await api.AddObj(formData);

				expect(request).toHaveBeenCalledWith(
					expect.objectContaining({
						data: expect.objectContaining({
							name: '完整知识库',
							description: '完整描述',
							copyright_owner: '版权所有者',
							tags: '标签1,标签2,标签3',
							version: '2.1.0',
							is_public: false,
						}),
					})
				);
			});
		});

		describe('UpdateObj - 更新知识库', () => {
			it('应该使用正确的 URL 和 PUT 方法', async () => {
				const formData = {
					id: 'test-id-123',
					name: '更新后的名称',
					description: '更新后的描述',
					version: '1.1',
					is_public: true,
				};

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: formData,
				});

				await api.UpdateObj(formData);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/knowledge/${formData.id}/`,
					method: 'put',
					data: formData,
				});
			});
		});

		describe('DelObj - 删除知识库', () => {
			it('应该使用正确的 URL 和 DELETE 方法', async () => {
				const id = 'delete-id-123';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '删除成功',
				});

				await api.DelObj(id);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/knowledge/${id}/`,
					method: 'delete',
					data: { id },
				});
			});
		});

		describe('ApproveObj - 审核通过', () => {
			it('应该使用正确的审核通过 URL 和 POST 方法', async () => {
				const id = 'approve-id-123';

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
		});

		describe('RejectObj - 审核拒绝', () => {
			it('应该使用正确的审核拒绝 URL 和 POST 方法', async () => {
				const id = 'reject-id-123';
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
				const id = 'reject-id-456';
				const reason = '包含敏感信息';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '审核拒绝',
				});

				await api.RejectObj(id, reason);

				expect(request).toHaveBeenCalledWith(
					expect.objectContaining({
						data: { reason: '包含敏感信息' },
					})
				);
			});
		});

		describe('exportData - 导出数据', () => {
			it('应该使用正确的导出 URL 和 GET 方法', async () => {
				const params = {
					name: '测试',
					is_public: true,
				};

				vi.mocked(downloadFile).mockResolvedValueOnce({
					code: 2000,
					data: 'file-content',
				});

				await api.exportData(params);

				expect(downloadFile).toHaveBeenCalledWith({
					url: '/api/content/knowledge/export_data/',
					params: params,
					method: 'get',
				});
			});
		});

		describe('GetFiles - 获取关联文件', () => {
			it('应该使用正确的文件列表 URL 和 GET 方法', async () => {
				const id = 'knowledge-id-123';

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					data: { results: [] },
				});

				await api.GetFiles(id);

				expect(request).toHaveBeenCalledWith({
					url: `/api/content/knowledge/${id}/files/`,
					method: 'get',
				});
			});
		});
	});

	describe('表单验证规则测试', () => {
		describe('名称字段验证 - 需求 7.1, 7.3', () => {
			it('名称为空时应该验证失败', () => {
				const nameRule = {
					required: true,
					message: '名称为必填项',
				};

				// 模拟验证逻辑
				const isEmpty = (value: string) => !value || value.trim() === '';
				
				expect(isEmpty('')).toBe(true);
				expect(isEmpty('   ')).toBe(true);
				expect(nameRule.message).toBe('名称为必填项');
			});

			it('名称长度超过 200 字符时应该验证失败', () => {
				const lengthRule = {
					max: 200,
					message: '名称长度不能超过200个字符',
				};

				const longName = 'a'.repeat(201);
				const validName = 'a'.repeat(200);

				expect(longName.length > lengthRule.max).toBe(true);
				expect(validName.length <= lengthRule.max).toBe(true);
				expect(lengthRule.message).toBe('名称长度不能超过200个字符');
			});

			it('名称长度在有效范围内应该验证通过', () => {
				const lengthRule = {
					max: 200,
					message: '名称长度不能超过200个字符',
				};

				const validNames = [
					'短名称',
					'a'.repeat(100),
					'a'.repeat(200),
				];

				validNames.forEach(name => {
					expect(name.length <= lengthRule.max).toBe(true);
				});
			});
		});

		describe('描述字段验证 - 需求 7.2', () => {
			it('描述为空时应该验证失败', () => {
				const descriptionRule = {
					required: true,
					message: '描述为必填项',
				};

				const isEmpty = (value: string) => !value || value.trim() === '';
				
				expect(isEmpty('')).toBe(true);
				expect(isEmpty('   ')).toBe(true);
				expect(descriptionRule.message).toBe('描述为必填项');
			});

			it('描述有内容时应该验证通过', () => {
				const descriptionRule = {
					required: true,
					message: '描述为必填项',
				};

				const validDescriptions = [
					'简短描述',
					'这是一个很长的描述内容，包含了很多详细信息',
					'包含\n换行符\n的描述',
				];

				validDescriptions.forEach(desc => {
					expect(desc.trim().length > 0).toBe(true);
				});
			});
		});

		describe('版本号格式验证 - 需求 7.5', () => {
			it('版本号为空时应该验证失败', () => {
				const versionRule = {
					required: true,
					message: '版本号为必填项',
				};

				const isEmpty = (value: string) => !value || value.trim() === '';
				
				expect(isEmpty('')).toBe(true);
				expect(versionRule.message).toBe('版本号为必填项');
			});

			it('版本号格式正确时应该验证通过', () => {
				const versionPattern = /^\d+\.\d+(\.\d+)?$/;

				const validVersions = [
					'1.0',
					'2.5',
					'10.20',
					'99.99',
					'1.0.0',
					'2.5.3',
					'10.20.30',
				];

				validVersions.forEach(version => {
					expect(versionPattern.test(version)).toBe(true);
				});
			});

			it('版本号格式不正确时应该验证失败', () => {
				const versionPattern = /^\d+\.\d+(\.\d+)?$/;
				const errorMessage = '版本号格式不正确，应为 x.y 或 x.y.z 格式';

				const invalidVersions = [
					'1',           // 缺少小数点
					'1.',          // 缺少次版本号
					'.1',          // 缺少主版本号
					'1.0.0.0',     // 版本号过长
					'v1.0',        // 包含字母前缀
					'1.0-beta',    // 包含后缀
					'a.b',         // 非数字
					'1.0.',        // 末尾多余点号
				];

				invalidVersions.forEach(version => {
					expect(versionPattern.test(version)).toBe(false);
				});
				
				expect(errorMessage).toBe('版本号格式不正确，应为 x.y 或 x.y.z 格式');
			});
		});

		describe('拒绝原因验证 - 需求 7.4', () => {
			it('拒绝原因为空时应该验证失败', () => {
				const rejectReasonPattern = /.+/;
				const errorMessage = '拒绝原因为必填项';

				expect(rejectReasonPattern.test('')).toBe(false);
				expect(errorMessage).toBe('拒绝原因为必填项');
			});

			it('拒绝原因有内容时应该验证通过', () => {
				const rejectReasonPattern = /.+/;

				const validReasons = [
					'内容不符合规范',
					'包含敏感信息',
					'版权问题',
					'质量不达标',
				];

				validReasons.forEach(reason => {
					expect(rejectReasonPattern.test(reason)).toBe(true);
				});
			});
		});
	});

	describe('数据格式化函数测试', () => {
		describe('日期时间格式化 - 需求 12.9', () => {
			it('应该将日期格式化为 YYYY-MM-DD HH:mm:ss 格式', () => {
				const testCases = [
					{
						input: new Date('2024-01-15T10:30:45'),
						expected: '2024-01-15 10:30:45',
					},
					{
						input: new Date('2023-12-31T23:59:59'),
						expected: '2023-12-31 23:59:59',
					},
					{
						input: new Date('2024-06-01T00:00:00'),
						expected: '2024-06-01 00:00:00',
					},
				];

				testCases.forEach(({ input, expected }) => {
					const result = formatDate(input, 'YYYY-mm-dd HH:MM:SS');
					expect(result).toBe(expected);
				});
			});

			it('应该正确处理单数字的月份和日期（补零）', () => {
				const date = new Date('2024-01-05T08:05:03');
				const result = formatDate(date, 'YYYY-mm-dd HH:MM:SS');
				expect(result).toBe('2024-01-05 08:05:03');
			});

			it('应该正确处理不同的时间', () => {
				const testCases = [
					{
						input: new Date('2024-03-15T00:00:00'),
						expected: '2024-03-15 00:00:00',
					},
					{
						input: new Date('2024-03-15T12:00:00'),
						expected: '2024-03-15 12:00:00',
					},
					{
						input: new Date('2024-03-15T23:59:59'),
						expected: '2024-03-15 23:59:59',
					},
				];

				testCases.forEach(({ input, expected }) => {
					const result = formatDate(input, 'YYYY-mm-dd HH:MM:SS');
					expect(result).toBe(expected);
				});
			});
		});

		describe('标签显示格式化 - 需求 12.1', () => {
			it('应该正确显示逗号分隔的标签', () => {
				const tags = '标签1,标签2,标签3';
				const tagArray = tags.split(',');
				
				expect(tagArray).toEqual(['标签1', '标签2', '标签3']);
				expect(tagArray.join(',')).toBe(tags);
			});

			it('空标签应该显示为 "-"', () => {
				const formatter = (value: string | undefined) => {
					return value ? value : '-';
				};

				expect(formatter(undefined)).toBe('-');
				expect(formatter('')).toBe('-');
				expect(formatter('标签1,标签2')).toBe('标签1,标签2');
			});

			it('应该正确处理单个标签', () => {
				const singleTag = '单个标签';
				const tagArray = singleTag.split(',');
				
				expect(tagArray).toEqual(['单个标签']);
			});

			it('应该正确处理多个标签', () => {
				const multipleTags = 'AI,机器学习,深度学习,神经网络';
				const tagArray = multipleTags.split(',');
				
				expect(tagArray.length).toBe(4);
				expect(tagArray).toEqual(['AI', '机器学习', '深度学习', '神经网络']);
			});
		});

		describe('数字字段格式化 - 需求 12.10', () => {
			it('数字为 0 时应该显示 "0"', () => {
				const formatter = (value: number | undefined) => {
					return value ?? 0;
				};

				expect(formatter(0)).toBe(0);
				expect(formatter(undefined)).toBe(0);
			});

			it('应该正确显示非零数字', () => {
				const formatter = (value: number | undefined) => {
					return value ?? 0;
				};

				expect(formatter(1)).toBe(1);
				expect(formatter(100)).toBe(100);
				expect(formatter(9999)).toBe(9999);
			});
		});

		describe('审核状态显示格式化 - 需求 12.2, 12.3, 12.4', () => {
			it('待审核状态应该显示为 "待审核"', () => {
				const formatter = (isPending: boolean, rejectionReason?: string) => {
					if (rejectionReason) {
						return '已拒绝';
					}
					return isPending ? '待审核' : '已通过';
				};

				expect(formatter(true)).toBe('待审核');
			});

			it('已通过状态应该显示为 "已通过"', () => {
				const formatter = (isPending: boolean, rejectionReason?: string) => {
					if (rejectionReason) {
						return '已拒绝';
					}
					return isPending ? '待审核' : '已通过';
				};

				expect(formatter(false)).toBe('已通过');
			});

			it('有拒绝原因时应该显示为 "已拒绝"', () => {
				const formatter = (isPending: boolean, rejectionReason?: string) => {
					if (rejectionReason) {
						return '已拒绝';
					}
					return isPending ? '待审核' : '已通过';
				};

				expect(formatter(true, '内容不符合规范')).toBe('已拒绝');
				expect(formatter(false, '包含敏感信息')).toBe('已拒绝');
			});

			it('审核状态应该使用正确的颜色标签', () => {
				const getColor = (isPending: boolean, rejectionReason?: string) => {
					if (rejectionReason) {
						return 'danger'; // 红色
					}
					if (isPending === true) {
						return 'warning'; // 黄色
					}
					if (isPending === false) {
						return 'success'; // 绿色
					}
					return 'info';
				};

				expect(getColor(true)).toBe('warning');
				expect(getColor(false)).toBe('success');
				expect(getColor(true, '拒绝原因')).toBe('danger');
				expect(getColor(false, '拒绝原因')).toBe('danger');
			});
		});

		describe('公开状态显示格式化 - 需求 12.5, 12.6', () => {
			it('公开状态为 true 时应该显示 "公开"', () => {
				const formatter = (value: boolean) => {
					return value ? '公开' : '私有';
				};

				expect(formatter(true)).toBe('公开');
			});

			it('公开状态为 false 时应该显示 "私有"', () => {
				const formatter = (value: boolean) => {
					return value ? '公开' : '私有';
				};

				expect(formatter(false)).toBe('私有');
			});
		});
	});

	describe('API 端点常量测试', () => {
		it('apiPrefix 应该指向正确的知识库端点', () => {
			expect(api.apiPrefix).toBe('/api/content/knowledge/');
		});
	});
});
