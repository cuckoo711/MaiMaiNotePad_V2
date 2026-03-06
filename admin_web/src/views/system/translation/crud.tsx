import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, compute, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';
import { dictionary } from '/@/utils/dictionary';
import { successMessage, errorMessage, warningMessage } from '/@/utils/message';
import { auth } from '/@/utils/authFunction';
import { ref, nextTick } from 'vue';
import XEUtils from 'xe-utils';

/**
 * 创建翻译管理 CRUD 配置
 * 
 * @param crudExpose CRUD 暴露的方法和属性
 * @param context 上下文对象
 * @returns CRUD 配置对象
 */
export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 记录选中的行
	const selectedRows = ref<any>([]);

	/**
	 * 选择变化回调
	 * 跟踪用户选中的行，支持跨页选择
	 */
	const onSelectionChange = (changed: any) => {
		const tableData = crudExpose.getTableData();
		const unChanged = tableData.filter((row: any) => !changed.includes(row));
		// 添加已选择的行
		XEUtils.arrayEach(changed, (item: any) => {
			const ids = XEUtils.pluck(selectedRows.value, 'id');
			if (!ids.includes(item.id)) {
				selectedRows.value = XEUtils.union(selectedRows.value, [item]);
			}
		});
		// 剔除未选择的行
		XEUtils.arrayEach(unChanged, (unItem: any) => {
			selectedRows.value = XEUtils.remove(selectedRows.value, (item: any) => item.id !== unItem.id);
		});
	};

	/**
	 * 切换行选择状态
	 * 在表格刷新后恢复之前的选中状态
	 */
	const toggleRowSelection = () => {
		const tableRef = crudExpose.getBaseTableRef();
		const tableData = crudExpose.getTableData();
		const selected = XEUtils.filter(tableData, (item: any) => {
			const ids = XEUtils.pluck(selectedRows.value, 'id');
			return ids.includes(item.id);
		});

		nextTick(() => {
			XEUtils.arrayEach(selected, (item) => {
				tableRef.toggleRowSelection(item, true);
			});
		});
	};
	/**
	 * 处理 API 错误响应
	 * 将后端验证错误映射到表单字段，或显示通用错误消息
	 * 
	 * @param error 错误对象
	 * @param formRef 表单引用（可选）
	 */
	const handleApiError = (error: any, formRef?: any) => {
		// 处理网络请求失败
		if (!error.response) {
			if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
				errorMessage('请求超时，请检查网络连接');
			} else if (error.message.includes('Network Error')) {
				errorMessage('网络连接失败，请稍后重试');
			} else {
				errorMessage('网络请求失败，请稍后重试');
			}
			return;
		}

		const status = error.response?.status;
		const data = error.response?.data;

		// 处理不同的 HTTP 状态码
		switch (status) {
			case 400:
				// 处理验证错误 - 尝试映射到表单字段
				if (data?.msg) {
					// 检查是否是唯一性约束错误
					if (data.msg.includes('已存在')) {
						errorMessage(data.msg);
					} else if (formRef && data.errors) {
						// 如果有字段级错误，映射到表单
						Object.keys(data.errors).forEach((field) => {
							if (formRef.setFieldError) {
								formRef.setFieldError(field, data.errors[field]);
							}
						});
						errorMessage('请检查表单输入');
					} else {
						errorMessage(data.msg || '请求参数错误');
					}
				} else {
					errorMessage('请求参数错误');
				}
				break;
			case 403:
				errorMessage('您没有权限执行此操作');
				break;
			case 404:
				errorMessage('请求的资源不存在');
				break;
			case 500:
				errorMessage('服务器错误，请联系管理员');
				break;
			default:
				errorMessage(data?.msg || '操作失败，请稍后重试');
		}
	};

	/**
	 * 分页请求处理器
	 * 获取翻译列表数据，支持分页、搜索和过滤
	 */
	const pageRequest = async (query: UserPageQuery) => {
		try {
			return await api.GetList(query);
		} catch (error: any) {
			handleApiError(error);
			throw error;
		}
	};

	/**
	 * 添加请求处理器
	 * 添加新的翻译记录
	 */
	const addRequest = async ({ form }: AddReq) => {
		try {
			return await api.AddObj(form);
		} catch (error: any) {
			handleApiError(error);
			throw error;
		}
	};

	/**
	 * 编辑请求处理器
	 * 更新现有翻译记录
	 */
	const editRequest = async ({ form, row }: EditReq) => {
		try {
			form.id = row.id;
			return await api.UpdateObj(form);
		} catch (error: any) {
			handleApiError(error);
			throw error;
		}
	};

	/**
	 * 删除请求处理器
	 * 删除指定的翻译记录
	 */
	const delRequest = async ({ row }: DelReq) => {
		try {
			return await api.DelObj(row.id);
		} catch (error: any) {
			// 删除失败时显示具体错误信息
			if (error.response?.data?.msg) {
				errorMessage(error.response.data.msg);
			} else {
				handleApiError(error);
			}
			throw error;
		}
	};

	return {
		selectedRows,
		crudOptions: {
			request: {
				pageRequest,
				addRequest,
				editRequest,
				delRequest,
			},
			table: {
				rowKey: 'id', // 设置主键 ID
				onSelectionChange,
				onRefreshed: () => toggleRowSelection(),
			},
			actionbar: {
				buttons: {
					add: {
						show: auth('translation:Create'),
					},
					batchEnable: {
						text: '批量启用',
						show: true,
						type: 'primary',
						click: async () => {
							try {
								// 获取选中的行
								if (!selectedRows.value || selectedRows.value.length === 0) {
									warningMessage('请先选择要启用的记录');
									return;
								}
								// 提取选中行的 ID
								const ids = selectedRows.value.map((row: any) => row.id);
								// 调用批量更新状态 API
								const res = await api.BatchUpdateStatus(ids, true);
								successMessage(res.msg as string);
								// 清空选中状态
								selectedRows.value = [];
								// 刷新列表
								crudExpose!.doRefresh();
							} catch (error: any) {
								handleApiError(error);
							}
						},
					},
					batchDisable: {
						text: '批量禁用',
						show: true,
						type: 'default',
						click: async () => {
							try {
								// 获取选中的行
								if (!selectedRows.value || selectedRows.value.length === 0) {
									warningMessage('请先选择要禁用的记录');
									return;
								}
								// 提取选中行的 ID
								const ids = selectedRows.value.map((row: any) => row.id);
								// 调用批量更新状态 API
								const res = await api.BatchUpdateStatus(ids, false);
								successMessage(res.msg as string);
								// 清空选中状态
								selectedRows.value = [];
								// 刷新列表
								crudExpose!.doRefresh();
							} catch (error: any) {
								handleApiError(error);
							}
						},
					},
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 200,
				buttons: {
					view: {
						show: false,
					},
					edit: {
						iconRight: 'Edit',
						type: 'text',
						show: auth('translation:Update'),
					},
					remove: {
						iconRight: 'Delete',
						type: 'text',
						show: auth('translation:Delete'),
					},
				},
			},
			columns: {
				_selection: {
					title: '选择',
					form: { show: false },
					column: {
						type: 'selection',
						align: 'center',
						width: '55px',
					},
				},
				_index: {
					title: '序号',
					form: { show: false },
					column: {
						align: 'center',
						width: '70px',
						columnSetDisabled: true, // 禁止在列设置中选择
						formatter: (context) => {
							// 计算序号，支持翻页累加
							let index = context.index ?? 1;
							let pagination = crudExpose!.crudBinding.value.pagination;
							// @ts-ignore
							return ((pagination.currentPage ?? 1) - 1) * pagination.pageSize + index + 1;
						},
					},
				},
				search: {
					title: '关键词',
					column: {
						show: false,
					},
					search: {
						show: true,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请输入关键词搜索原文或译文',
						},
						// 实现搜索防抖（延迟 300ms）
						debounce: 300,
					},
					form: {
						show: false,
					},
				},
				source_text: {
					title: '原文',
					search: {
						show: false,
					},
					type: 'input',
					column: {
						minWidth: 150,
						showOverflowTooltip: true, // 显示省略号和悬浮提示
					},
					form: {
						rules: [
							{ required: true, message: '原文不能为空' },
							{ max: 200, message: '原文长度不能超过 200 个字符' },
						],
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请输入原文（最多 200 个字符）',
						},
						helper: '待翻译的源文本，支持中文、英文、日文等多种语言',
					},
				},
				translated_text: {
					title: '译文',
					search: {
						show: false,
					},
					type: 'input',
					column: {
						minWidth: 150,
						showOverflowTooltip: true, // 显示省略号和悬浮提示
					},
					form: {
						rules: [
							{ required: true, message: '译文不能为空' },
							{ max: 200, message: '译文长度不能超过 200 个字符' },
						],
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请输入译文（最多 200 个字符）',
						},
						helper: '翻译后的目标文本，应准确表达原文含义',
					},
				},
				translation_type: {
					title: '翻译类型',
					search: {
						show: true,
					},
					type: 'dict-select',
					column: {
						minWidth: 100,
						showOverflowTooltip: true, // 显示省略号和悬浮提示
					},
					form: {
						rules: [
							{ required: true, message: '翻译类型不能为空' },
							{ max: 50, message: '翻译类型长度不能超过 50 个字符' },
						],
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请选择翻译类型',
						},
						helper: '用于分类管理不同场景的翻译数据，如 UI 界面文本、API 响应消息等',
					},
					dict: dict({
						url: '/api/system/translation/get_types/',
						value: 'value',
						label: 'label',
						getData: (data: any) => {
							return data.data.translation_types || [];
						},
					}),
				},
				source_language: {
					title: '源语言',
					search: {
						show: true,
					},
					type: 'dict-select',
					column: {
						minWidth: 100,
						showOverflowTooltip: true, // 显示省略号和悬浮提示
					},
					form: {
						rules: [
							{ required: true, message: '源语言不能为空' },
						],
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请选择原文的语言',
						},
					},
					dict: dict({
						url: '/api/system/translation/get_types/',
						value: 'value',
						label: 'label',
						getData: (data: any) => {
							return data.data.source_languages || [];
						},
					}),
				},
				target_language: {
					title: '目标语言',
					search: {
						show: true,
					},
					type: 'dict-select',
					column: {
						minWidth: 100,
						showOverflowTooltip: true, // 显示省略号和悬浮提示
					},
					form: {
						rules: [
							{ required: true, message: '目标语言不能为空' },
						],
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请选择译文的语言',
						},
					},
					dict: dict({
						url: '/api/system/translation/get_types/',
						value: 'value',
						label: 'label',
						getData: (data: any) => {
							return data.data.target_languages || [];
						},
					}),
				},
				sort: {
					title: '排序',
					type: 'number',
					search: {
						show: false,
					},
					column: {
						minWidth: 80,
					},
					form: {
						value: 1,
						component: {
							placeholder: '请输入排序值（数字越小越靠前）',
						},
						helper: '用于控制翻译记录的显示顺序，数值越小排序越靠前',
					},
				},
				status: {
					title: '状态',
					search: {
						show: true,
					},
					type: 'dict-radio',
					column: {
						minWidth: 90,
						component: {
							name: 'fs-dict-switch',
							activeText: '',
							inactiveText: '',
							style: '--el-switch-on-color: var(--el-color-primary); --el-switch-off-color: #dcdfe6',
							onChange: compute((context) => {
								return async () => {
									// 保存原始状态，用于失败时回滚
									const originalStatus = context.row.status;
									try {
										// 调用更新 API
										const res = await api.UpdateObj(context.row);
										successMessage(res.msg as string);
									} catch (error: any) {
										// 更新失败，回滚状态
										context.row.status = originalStatus;
										// 显示错误消息
										if (error.response?.data?.msg) {
											errorMessage(error.response.data.msg);
										} else {
											handleApiError(error);
										}
									}
								};
							}),
						},
					},
					dict: dict({
						data: dictionary('button_status_bool'),
					}),
				},
				create_datetime: {
					title: '创建时间',
					type: 'datetime',
					search: {
						show: false,
					},
					column: {
						minWidth: 160,
						showOverflowTooltip: true, // 显示省略号和悬浮提示
					},
					form: {
						show: false,
					},
				},
				update_datetime: {
					title: '更新时间',
					type: 'datetime',
					search: {
						show: false,
					},
					column: {
						minWidth: 160,
						showOverflowTooltip: true, // 显示省略号和悬浮提示
					},
					form: {
						show: false,
					},
				},
			},
		},
	};
};
