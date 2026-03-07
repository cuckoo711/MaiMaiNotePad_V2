import { request } from '/@/utils/service';
import {
	dict,
	UserPageQuery,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { commonCrudConfig } from '/@/utils/commonCrud';
import dayjs from 'dayjs';

/**
 * 格式化禁言/封禁截止时间
 */
export function formatUntil(until?: string): string {
	if (!until) return '-';
	return dayjs(until).format('YYYY-MM-DD HH:mm:ss');
}

/**
 * 创建处罚操作 CRUD 配置
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求 - 调用系统用户列表API
	const pageRequest = async (query: UserPageQuery) => {
		return await request({
			url: '/api/system/user/',
			method: 'get',
			params: query,
		});
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
			},
			actionbar: {
				buttons: {
					add: {
						show: false, // 不显示添加按钮
					},
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 240,
			},
			// 搜索区域配置
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
				id: {
					title: '用户ID',
					search: {
						show: true,
						component: {
							name: 'el-input',
							placeholder: '搜索用户ID',
						},
					},
					column: {
						minWidth: 100,
					},
					form: { show: false },
				},
				username: {
					title: '用户名',
					search: {
						show: true,
						component: {
							name: 'el-input',
							placeholder: '搜索用户名',
						},
					},
					column: {
						minWidth: 120,
					},
					form: { show: false },
				},
				name: {
					title: '姓名',
					search: {
						show: true,
						component: {
							name: 'el-input',
							placeholder: '搜索姓名',
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
				email: {
					title: '邮箱',
					column: {
						minWidth: 180,
						showOverflowTooltip: true,
						formatter: ({ value }: any) => {
							return value || '-';
						},
					},
					form: { show: false },
				},
				mobile: {
					title: '手机号',
					column: {
						minWidth: 120,
						formatter: ({ value }: any) => {
							return value || '-';
						},
					},
					form: { show: false },
				},
				is_muted: {
					title: '禁言状态',
					search: {
						show: true,
					},
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '已禁言', value: 'true' },
							{ label: '正常', value: 'false' },
						],
					}),
					column: {
						minWidth: 100,
					},
					form: { show: false },
				},
				muted_until: {
					title: '禁言截止',
					column: {
						minWidth: 160,
						formatter: ({ value }: any) => {
							return formatUntil(value);
						},
					},
					form: { show: false },
				},
				is_active: {
					title: '封禁状态',
					search: {
						show: true,
					},
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '已封禁', value: 'false' },
							{ label: '正常', value: 'true' },
						],
					}),
					column: {
						minWidth: 100,
					},
					form: { show: false },
				},
				locked_until: {
					title: '封禁截止',
					column: {
						minWidth: 160,
						formatter: ({ value }: any) => {
							return formatUntil(value);
						},
					},
					form: { show: false },
				},
				...commonCrudConfig({
					create_datetime: {
						table: true,
						search: false,
					},
					update_datetime: {
						table: false,
					},
				}),
			},
		},
	};
};
