import { request } from '/@/utils/service';
import {
	dict,
	UserPageQuery,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet,
	compute,
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
export const createCrudOptions = function ({ 
	crudExpose,
	onMute,
	onBan,
	onUnmute,
	onUnban,
	onViewDetail,
}: CreateCrudOptionsProps & {
	onMute?: (row: any) => void;
	onBan?: (row: any) => void;
	onUnmute?: (row: any) => void;
	onUnban?: (row: any) => void;
	onViewDetail?: (row: any) => void;
}): CreateCrudOptionsRet {
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
				buttons: {
					view: { show: false },
					edit: { show: false },
					remove: { show: false },
					// 禁言按钮
					mute: {
						text: '禁言',
						type: 'warning',
						size: 'small',
						show: compute(({ row }) => {
							// 系统账号不显示
							if (row.user_type === 2) return false;
							// 已禁言的不显示
							if (row.is_muted) return false;
							return auth('punish:Mute');
						}),
						click: ({ row }: any) => {
							onMute && onMute(row);
						},
					},
					// 解除禁言按钮
					unmute: {
						text: '解禁',
						type: 'warning',
						size: 'small',
						plain: true,
						show: compute(({ row }) => {
							// 系统账号不显示
							if (row.user_type === 2) return false;
							// 只有已禁言的才显示
							if (!row.is_muted) return false;
							// 使用与禁言相同的权限
							return auth('punish:Mute');
						}),
						click: ({ row }: any) => {
							onUnmute && onUnmute(row);
						},
					},
					// 封禁按钮
					ban: {
						text: '封禁',
						type: 'danger',
						size: 'small',
						show: compute(({ row }) => {
							// 系统账号不显示
							if (row.user_type === 2) return false;
							// 已封禁的不显示
							if (!row.is_active) return false;
							return auth('punish:Ban');
						}),
						click: ({ row }: any) => {
							onBan && onBan(row);
						},
					},
					// 解除封禁按钮
					unban: {
						text: '解禁',
						type: 'danger',
						size: 'small',
						plain: true,
						show: compute(({ row }) => {
							// 系统账号不显示
							if (row.user_type === 2) return false;
							// 只有已封禁的才显示
							if (row.is_active) return false;
							// 使用与封禁相同的权限
							return auth('punish:Ban');
						}),
						click: ({ row }: any) => {
							onUnban && onUnban(row);
						},
					},
					// 查看详情按钮
					detail: {
						text: '查看详情',
						type: 'primary',
						size: 'small',
						show: compute(({ row }) => {
							// 系统账号不显示
							if (row.user_type === 2) return false;
							return auth('punish:Detail');
						}),
						click: ({ row }: any) => {
							onViewDetail && onViewDetail(row);
						},
					},
				},
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
						formatter: ({ value, row }: any) => {
							// 如果用户未被禁言，不显示截止时间
							if (!row.is_muted) return '-';
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
						formatter: ({ value, row }: any) => {
							// 如果用户未被封禁（is_active为true），不显示截止时间
							if (row.is_active) return '-';
							return formatUntil(value);
						},
					},
					form: { show: false },
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
						show: false, // 默认隐藏，可在列设置中显示
						minWidth: 280,
					},
					form: { show: false },
				},
				email: {
					title: '邮箱',
					column: {
						show: false, // 默认隐藏，可在列设置中显示
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
						show: false, // 默认隐藏，可在列设置中显示
						minWidth: 120,
						formatter: ({ value }: any) => {
							return value || '-';
						},
					},
					form: { show: false },
				},
				...commonCrudConfig({
					create_datetime: {
						table: false, // 隐藏创建时间
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
