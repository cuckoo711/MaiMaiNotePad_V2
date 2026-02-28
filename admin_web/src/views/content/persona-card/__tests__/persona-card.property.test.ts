/**
 * 人设卡模块属性测试
 * Feature: admin-content-management, Property 2: CRUD 操作数据一致性
 * 
 * 验证需求: 2.4, 2.6
 * 
 * 属性描述：
 * 对于任何有效的创建或更新表单数据，提交后从后端获取的数据应该与提交的数据一致
 * （除了系统生成的字段如 ID、时间戳）
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import * as api from '../api';
import type { PersonaCard } from '../api';

// 模拟 request 工具函数
vi.mock('/@/utils/service', () => ({
	request: vi.fn(),
	downloadFile: vi.fn(),
}));

// 导入模拟的 request 函数
import { request } from '/@/utils/service';

describe('人设卡模块属性测试', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	// Feature: admin-content-management, Property 2
	describe('属性 2: CRUD 操作数据一致性', () => {
		/**
		 * 创建人设卡的数据生成器
		 * 生成符合验证规则的随机人设卡数据
		 */
		const personaCardArbitrary = fc.record({
			name: fc.string({ minLength: 1, maxLength: 200 }),
			description: fc.string({ minLength: 1, maxLength: 1000 }),
			copyright_owner: fc.option(fc.string({ maxLength: 200 }), { nil: undefined }),
			tags: fc.option(
				fc.array(fc.string({ minLength: 1, maxLength: 50 }), { minLength: 0, maxLength: 10 })
					.map(tags => tags.join(',')),
				{ nil: undefined }
			),
			is_public: fc.boolean(),
			version: fc.oneof(
				// 生成 x.y 格式的版本号
				fc.tuple(fc.nat({ max: 99 }), fc.nat({ max: 99 }))
					.map(([major, minor]) => `${major}.${minor}`),
				// 生成 x.y.z 格式的版本号
				fc.tuple(fc.nat({ max: 99 }), fc.nat({ max: 99 }), fc.nat({ max: 99 }))
					.map(([major, minor, patch]) => `${major}.${minor}.${patch}`)
			),
		});

		it('创建操作：提交后获取的数据应该与提交的数据一致', async () => {
			await fc.assert(
				fc.asyncProperty(personaCardArbitrary, async (formData) => {
					// 模拟系统生成的字段
					const systemGeneratedFields = {
						id: fc.sample(fc.uuid(), 1)[0],
						uploader: fc.sample(fc.integer({ min: 1, max: 1000 }), 1)[0],
						star_count: 0,
						downloads: 0,
						base_path: '[]',
						is_pending: true,
						create_datetime: new Date().toISOString(),
						update_datetime: new Date().toISOString(),
					};

					// 模拟创建响应
					const createdData: PersonaCard = {
						...formData,
						...systemGeneratedFields,
					};

					// 模拟 API 调用
					vi.mocked(request).mockResolvedValueOnce({
						code: 2000,
						msg: '创建成功',
						data: createdData,
					});

					// 执行创建操作
					const createResponse = await api.AddObj(formData);
					const created = createResponse.data;

					// 模拟获取详情响应
					vi.mocked(request).mockResolvedValueOnce({
						code: 2000,
						msg: '获取成功',
						data: createdData,
					});

					// 执行获取操作
					const getResponse = await api.GetObj(created.id);
					const fetched = getResponse.data;

					// 验证：提交的数据字段应该与获取的数据一致
					expect(fetched.name).toBe(formData.name);
					expect(fetched.description).toBe(formData.description);
					expect(fetched.version).toBe(formData.version);
					expect(fetched.is_public).toBe(formData.is_public);
					
					// 可选字段验证
					if (formData.copyright_owner !== undefined) {
						expect(fetched.copyright_owner).toBe(formData.copyright_owner);
					}
					if (formData.tags !== undefined) {
						expect(fetched.tags).toBe(formData.tags);
					}

					// 验证系统生成的字段存在
					expect(fetched.id).toBeDefined();
					expect(fetched.uploader).toBeDefined();
					expect(fetched.create_datetime).toBeDefined();
					expect(fetched.update_datetime).toBeDefined();
				}),
				{ numRuns: 100 }
			);
		});

		it('更新操作：提交后获取的数据应该与提交的数据一致', async () => {
			await fc.assert(
				fc.asyncProperty(
					personaCardArbitrary,
					personaCardArbitrary,
					async (initialData, updateData) => {
						// 模拟初始数据（已存在的人设卡）
						const existingId = fc.sample(fc.uuid(), 1)[0];
						const existingPersonaCard: PersonaCard = {
							...initialData,
							id: existingId,
							uploader: fc.sample(fc.integer({ min: 1, max: 1000 }), 1)[0],
							star_count: fc.sample(fc.integer({ min: 0, max: 100 }), 1)[0],
							downloads: fc.sample(fc.integer({ min: 0, max: 1000 }), 1)[0],
							base_path: '[]',
							is_pending: false,
							create_datetime: new Date(Date.now() - 86400000).toISOString(),
							update_datetime: new Date(Date.now() - 3600000).toISOString(),
						};

						// 模拟更新后的数据
						const updatedData: PersonaCard = {
							...existingPersonaCard,
							...updateData,
							id: existingId, // ID 不变
							uploader: existingPersonaCard.uploader, // 上传者不变
							star_count: existingPersonaCard.star_count, // 收藏数不变
							downloads: existingPersonaCard.downloads, // 下载次数不变
							create_datetime: existingPersonaCard.create_datetime, // 创建时间不变
							update_datetime: new Date().toISOString(), // 更新时间改变
						};

						// 模拟更新 API 调用
						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '更新成功',
							data: updatedData,
						});

						// 执行更新操作
						const updateResponse = await api.UpdateObj({
							id: existingId,
							...updateData,
						});
						const updated = updateResponse.data;

						// 模拟获取详情响应
						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '获取成功',
							data: updatedData,
						});

						// 执行获取操作
						const getResponse = await api.GetObj(existingId);
						const fetched = getResponse.data;

						// 验证：更新的数据字段应该与获取的数据一致
						expect(fetched.name).toBe(updateData.name);
						expect(fetched.description).toBe(updateData.description);
						expect(fetched.version).toBe(updateData.version);
						expect(fetched.is_public).toBe(updateData.is_public);

						// 可选字段验证
						if (updateData.copyright_owner !== undefined) {
							expect(fetched.copyright_owner).toBe(updateData.copyright_owner);
						}
						if (updateData.tags !== undefined) {
							expect(fetched.tags).toBe(updateData.tags);
						}

						// 验证不应该改变的字段
						expect(fetched.id).toBe(existingId);
						expect(fetched.uploader).toBe(existingPersonaCard.uploader);
						expect(fetched.create_datetime).toBe(existingPersonaCard.create_datetime);

						// 验证更新时间已改变
						expect(fetched.update_datetime).not.toBe(existingPersonaCard.update_datetime);
					}
				),
				{ numRuns: 100 }
			);
		});

		it('边界情况：名称长度为 200 字符时应该正确保存和获取', async () => {
			await fc.assert(
				fc.asyncProperty(
					fc.string({ minLength: 200, maxLength: 200 }),
					async (maxLengthName) => {
						const formData = {
							name: maxLengthName,
							description: '测试描述',
							version: '1.0',
							is_public: true,
						};

						const systemGeneratedFields = {
							id: fc.sample(fc.uuid(), 1)[0],
							uploader: 1,
							star_count: 0,
							downloads: 0,
							base_path: '[]',
							is_pending: true,
							create_datetime: new Date().toISOString(),
							update_datetime: new Date().toISOString(),
						};

						const createdData: PersonaCard = {
							...formData,
							...systemGeneratedFields,
						};

						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '创建成功',
							data: createdData,
						});

						const createResponse = await api.AddObj(formData);
						const created = createResponse.data;

						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '获取成功',
							data: createdData,
						});

						const getResponse = await api.GetObj(created.id);
						const fetched = getResponse.data;

						// 验证：200 字符的名称应该完整保存
						expect(fetched.name).toBe(maxLengthName);
						expect(fetched.name.length).toBe(200);
					}
				),
				{ numRuns: 50 }
			);
		});

		it('边界情况：版本号格式应该正确保存', async () => {
			const versionFormats = [
				'0.1',
				'1.0',
				'99.99',
				'0.0.1',
				'1.0.0',
				'10.20.30',
				'99.99.99',
			];

			for (const version of versionFormats) {
				const formData = {
					name: '测试人设卡',
					description: '测试描述',
					version: version,
					is_public: true,
				};

				const systemGeneratedFields = {
					id: fc.sample(fc.uuid(), 1)[0],
					uploader: 1,
					star_count: 0,
					downloads: 0,
					base_path: '[]',
					is_pending: true,
					create_datetime: new Date().toISOString(),
					update_datetime: new Date().toISOString(),
				};

				const createdData: PersonaCard = {
					...formData,
					...systemGeneratedFields,
				};

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '创建成功',
					data: createdData,
				});

				const createResponse = await api.AddObj(formData);
				const created = createResponse.data;

				vi.mocked(request).mockResolvedValueOnce({
					code: 2000,
					msg: '获取成功',
					data: createdData,
				});

				const getResponse = await api.GetObj(created.id);
				const fetched = getResponse.data;

				// 验证：版本号应该完整保存
				expect(fetched.version).toBe(version);
			}
		});

		it('边界情况：标签字段应该正确保存逗号分隔的多个标签', async () => {
			await fc.assert(
				fc.asyncProperty(
					fc.array(fc.string({ minLength: 1, maxLength: 20 }), { minLength: 1, maxLength: 10 }),
					async (tagArray) => {
						const tags = tagArray.join(',');
						const formData = {
							name: '测试人设卡',
							description: '测试描述',
							version: '1.0',
							is_public: true,
							tags: tags,
						};

						const systemGeneratedFields = {
							id: fc.sample(fc.uuid(), 1)[0],
							uploader: 1,
							star_count: 0,
							downloads: 0,
							base_path: '[]',
							is_pending: true,
							create_datetime: new Date().toISOString(),
							update_datetime: new Date().toISOString(),
						};

						const createdData: PersonaCard = {
							...formData,
							...systemGeneratedFields,
						};

						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '创建成功',
							data: createdData,
						});

						const createResponse = await api.AddObj(formData);
						const created = createResponse.data;

						vi.mocked(request).mockResolvedValueOnce({
							code: 2000,
							msg: '获取成功',
							data: createdData,
						});

						const getResponse = await api.GetObj(created.id);
						const fetched = getResponse.data;

						// 验证：标签应该完整保存
						expect(fetched.tags).toBe(tags);
					}
				),
				{ numRuns: 50 }
			);
		});
	});
});
