import * as api from './api';
import {
	dict,
	UserPageQuery,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { ElMessageBox } from 'element-plus';
import { commonCrudConfig } from '/@/utils/commonCrud';

/**
 * 目标类型中文映射
 */
export const TARGET_TYPE_MAP: Record<string, string> = {
	knowledge: '知识库',
	persona: '人设卡',
};

/**
 * 审核状态中文映射及颜色配置
 */
export const STATUS_MAP: Record<string, { label: string; color: string }> = {
	pending: { label: '待审核', color: 'warning' },
	approved: { label: '已通过', color: 'success' },
	rejected: { label: '已拒绝', color: 'danger' },
};

/**
 * 创建上传记录管理 CRUD 配置
 * 上传记录模块为只读，不支持新增、编辑、删除，支持审核操作
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求
	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
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
			request: {
				pageRequest,
			},
			// 搜索区域配置：启用折叠和重置按钮
			search: {
				show: true,
				collapse: true,
				buttons: {
					reset: { show: true },
				},
			},
			actionbar: {
				buttons: {
					add: {
						show: false, // 上传记录不支持新增
					},
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 280,
				buttons: {
					view: {
						text: '查看详情',
						type: 'text',
						show: auth('upload_record:View'),
					},
					edit: {
						show: false, // 上传记录不支持编辑
					},
					remove: {
						show: false, // 上传记录不支持删除
					},
					approve: {
						text: '审核通过',
						type: 'text',
						iconRight: 'Select',
						show: auth('upload_record:Approve'),
						click: (ctx: any) =>
							ElMessageBox.confirm('确定审核通过该上传记录吗？', '提示', {
								confirmButtonText: '确定',
								cancelButtonText: '取消',
								type: 'warning',
							}).then(() => approveRequest(ctx.row)),
					},
					reject: {
						text: '审核拒绝',
						type: 'text',
						iconRight: 'Close',
						show: auth('upload_record:Approve'),
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
				uploader_name: {
					title: '上传者',
					search: {
						show: true,
						component: {
							name: 'input',
							placeholder: '搜索上传者',
						},
					},
					column: {
						minWidth: 100,
						formatter: ({ value }: any) => {
							return value || '-';
						},
					},
					form: { show: false },
				},
				target_type: {
					title: '目标类型',
					search: {
						show: true,
					},
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '知识库', value: 'knowledge' },
							{ label: '人设卡', value: 'persona' },
						],
					}),
					column: {
						minWidth: 100,
						formatter: ({ value }: any) => {
							return TARGET_TYPE_MAP[value] || value;
						},
					},
					form: { show: false },
				},
				name: {
					title: '名称',
					search: {
						show: true,
						component: {
							name: 'input',
							placeholder: '搜索名称',
						},
					},
					column: {
						minWidth: 150,
					},
					form: { show: false },
				},
				description: {
					title: '描述',
					column: {
						minWidth: 200,
						showOverflowTooltip: true,
						formatter: ({ value }: any) => {
							return value || '-';
						},
					},
					form: { show: false },
				},
				status: {
					title: '审核状态',
					search: {
						show: true,
					},
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '待审核', value: 'pending', color: 'warning' },
							{ label: '已通过', value: 'approved', color: 'success' },
							{ label: '已拒绝', value: 'rejected', color: 'danger' },
						],
					}),
					column: {
						minWidth: 100,
						component: {
							name: 'fs-dict-tag',
							color: (context: any) => {
								const { value } = context;
								return STATUS_MAP[value]?.color || 'info';
							},
						},
					},
					form: { show: false },
				},
				...commonCrudConfig({
					create_datetime: {
						table: true,
						search: true,
					},
					update_datetime: {
						table: false,
					},
				}),
			},
		},
	};
};
