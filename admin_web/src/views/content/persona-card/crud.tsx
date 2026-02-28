import * as api from './api';
import {
	dict,
	UserPageQuery,
	AddReq,
	DelReq,
	EditReq,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { ElMessageBox } from 'element-plus';
import { commonCrudConfig } from '/@/utils/commonCrud';

/**
 * 创建人设卡管理 CRUD 配置
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求
	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
	};

	// 编辑请求
	const editRequest = async ({ form, row }: EditReq) => {
		form.id = row.id;
		return await api.UpdateObj(form);
	};

	// 删除请求
	const delRequest = async ({ row }: DelReq) => {
		return await api.DelObj(row.id);
	};

	// 新增请求
	const addRequest = async ({ form }: AddReq) => {
		return await api.AddObj(form);
	};

	// 导出请求
	const exportRequest = async (query: UserPageQuery) => {
		return await api.exportData(query);
	};

	// 审核通过请求
	const approveRequest = async (row: any) => {
		await api.ApproveObj(row.id);
	};

	// 审核拒绝请求
	const rejectRequest = async (row: any, reason: string) => {
		await api.RejectObj(row.id, reason);
	};

	return {
		crudOptions: {
			table: {
				remove: {
					confirmMessage: '是否删除该人设卡？',
				},
			},
			request: {
				pageRequest,
				addRequest,
				editRequest,
				delRequest,
			},
			actionbar: {
				buttons: {
					add: {
						show: auth('persona_card:Create'),
					},
					export: {
						text: '导出',
						title: '导出',
						show: auth('persona_card:Export'),
						click: (ctx: any) =>
							ElMessageBox.confirm('确定导出数据吗？', '提示', {
								confirmButtonText: '确定',
								cancelButtonText: '取消',
								type: 'warning',
							}).then(() => exportRequest(ctx.row)),
					},
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 300,
				buttons: {
					view: {
						show: false,
					},
					edit: {
						iconRight: 'Edit',
						type: 'text',
						show: auth('persona_card:Update'),
					},
					remove: {
						iconRight: 'Delete',
						type: 'text',
						show: auth('persona_card:Delete'),
					},
					approve: {
						text: '审核通过',
						type: 'text',
						iconRight: 'Select',
						show: auth('persona_card:Approve'),
						click: (ctx: any) =>
							ElMessageBox.confirm('确定审核通过该人设卡吗？', '提示', {
								confirmButtonText: '确定',
								cancelButtonText: '取消',
								type: 'warning',
							}).then(() => approveRequest(ctx.row)),
					},
					reject: {
						text: '审核拒绝',
						type: 'text',
						iconRight: 'Close',
						show: auth('persona_card:Approve'),
						click: (ctx: any) =>
							ElMessageBox.prompt('请输入拒绝原因', '审核拒绝', {
								confirmButtonText: '确定',
								cancelButtonText: '取消',
								inputPattern: /.+/,
								inputErrorMessage: '拒绝原因为必填项',
							}).then(({ value }) => rejectRequest(ctx.row, value)),
					},
				},
			},
			// 搜索区域配置：启用折叠和重置按钮
			search: {
				show: true,
				collapse: true,
				buttons: {
					reset: { show: true },
				},
			},
			columns: {
				// 复选框选择列
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
						type: 'index',
						align: 'center',
						width: '70px',
						columnSetDisabled: true,
					},
				},
				name: {
					title: '名称',
					search: {
						show: true,
					},
					type: 'input',
					column: {
						minWidth: 150,
					},
					form: {
						rules: [
							{
								required: true,
								message: '名称为必填项',
							},
							{
								max: 200,
								message: '名称长度不能超过200个字符',
							},
						],
						component: {
							placeholder: '请输入名称',
						},
					},
				},
				description: {
					title: '描述',
					type: 'textarea',
					column: {
						minWidth: 200,
						showOverflowTooltip: true,
					},
					form: {
						rules: [
							{
								required: true,
								message: '描述为必填项',
							},
						],
						component: {
							placeholder: '请输入描述',
							rows: 4,
						},
					},
				},
				uploader_name: {
					title: '上传者',
					search: {
						show: true,
						component: {
							name: 'input',
							placeholder: '请输入上传者',
						},
					},
					column: {
						minWidth: 100,
					},
					form: {
						show: false,
					},
				},
				copyright_owner: {
					title: '版权所有者',
					search: {
						show: true,
						component: {
							name: 'input',
							placeholder: '搜索版权所有者',
						},
					},
					type: 'input',
					column: {
						minWidth: 120,
					},
					form: {
						component: {
							placeholder: '请输入版权所有者',
						},
					},
				},
				tags: {
					title: '标签',
					search: {
						show: true,
						component: {
							name: 'input',
							placeholder: '搜索标签',
						},
					},
					type: 'input',
					column: {
						minWidth: 150,
						formatter: ({ value }) => {
							return value ? value : '-';
						},
					},
					form: {
						component: {
							placeholder: '请输入标签，多个标签用逗号分隔',
						},
						helper: '多个标签用逗号分隔',
					},
				},
				star_count: {
					title: '收藏数',
					type: 'number',
					column: {
						minWidth: 100,
						align: 'right',
						formatter: ({ value }) => {
							return value ?? 0;
						},
					},
					form: {
						show: false,
					},
				},
				downloads: {
					title: '下载次数',
					type: 'number',
					column: {
						minWidth: 100,
						align: 'right',
						formatter: ({ value }) => {
							return value ?? 0;
						},
					},
					form: {
						show: false,
					},
				},
				is_public: {
					title: '公开状态',
					search: {
						show: true,
					},
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '公开', value: true },
							{ label: '私有', value: false },
						],
					}),
					column: {
						minWidth: 100,
						formatter: ({ value }) => {
							return value ? '公开' : '私有';
						},
					},
					form: {
						value: true,
						component: {
							placeholder: '请选择公开状态',
						},
					},
				},
				is_pending: {
					title: '审核状态',
					search: {
						show: true,
					},
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '待审核', value: true, color: 'warning' },
							{ label: '已通过', value: false, color: 'success' },
						],
					}),
					column: {
						minWidth: 100,
						component: {
							name: 'fs-dict-tag',
							color: (context: any) => {
								const { value } = context;
								if (value === true) return 'warning';
								if (value === false) return 'success';
								return 'info';
							},
						},
						formatter: ({ value, row }) => {
							// 如果有拒绝原因，说明是已拒绝状态
							if (row.rejection_reason) {
								return '已拒绝';
							}
							return value ? '待审核' : '已通过';
						},
					},
					form: {
						show: false,
					},
				},
				rejection_reason: {
					title: '拒绝原因',
					type: 'textarea',
					column: {
						minWidth: 150,
						showOverflowTooltip: true,
						formatter: ({ value }) => {
							return value ? value : '-';
						},
					},
					form: {
						show: false,
					},
				},
				version: {
					title: '版本号',
					type: 'input',
					column: {
						minWidth: 100,
					},
					form: {
						rules: [
							{
								required: true,
								message: '版本号为必填项',
							},
							{
								pattern: /^\d+\.\d+(\.\d+)?$/,
								message: '版本号格式不正确，应为 x.y 或 x.y.z 格式',
							},
						],
						component: {
							placeholder: '请输入版本号（如：1.0 或 1.0.0）',
						},
					},
				},
				...commonCrudConfig({
					create_datetime: {
						table: true,
						search: true,
					},
					update_datetime: {
						table: true,
					},
				}),
			},
		},
	};
};
