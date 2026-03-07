import * as api from '/@/api/moderation';
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
 * 格式化剩余时长
 * @param locked_until 封禁截止时间
 */
export function formatRemaining(locked_until?: string): string {
	if (!locked_until) return '永久';
	
	const now = dayjs();
	const until = dayjs(locked_until);
	const diff = until.diff(now);
	
	if (diff <= 0) return '已过期';
	
	const days = Math.floor(diff / (1000 * 60 * 60 * 24));
	const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
	
	if (days > 0) {
		return `还剩${days}天${hours}小时`;
	}
	return `还剩${hours}小时`;
}

/**
 * 创建封禁管理 CRUD 配置
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求
	const pageRequest = async (query: UserPageQuery) => {
		return await api.getBanList(query);
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
				// 转换后端响应格式为Fast-CRUD期望的格式
				transformRes: ({ res }: any) => {
					// 后端返回: { code, msg, data: { total, page, page_size, results } }
					// Fast-CRUD期望: { currentPage, pageSize, total, records }
					if (res && res.data) {
						const backendData = res.data;
						return {
							currentPage: backendData.page,
							pageSize: backendData.page_size,
							total: backendData.total,
							records: backendData.results || [],
						};
					}
					return res;
				},
			},
			actionbar: {
				buttons: {
					add: {
						show: false, // 移除添加按钮，改到"处罚操作"页面
					},
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 280,
				buttons: {
					view: {
						show: false,
					},
					edit: {
						show: false,
					},
					remove: {
						show: false,
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
				user_name: {
					title: '用户',
					search: {
						show: true,
						component: {
							name: 'el-input',
							placeholder: '搜索用户名',
						},
					},
					column: {
						minWidth: 120,
						formatter: ({ value }: any) => {
							return value || '-';
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
						minWidth: 100,
					},
					form: { show: false },
				},
				ban_reason: {
					title: '封禁原因',
					search: {
						show: true,
						component: {
							name: 'el-input',
							placeholder: '搜索原因关键词',
						},
					},
					column: {
						minWidth: 200,
						showOverflowTooltip: true,
					},
					form: { show: false },
				},
				locked_until: {
					title: '剩余时长',
					column: {
						minWidth: 150,
						formatter: ({ value }: any) => {
							return formatRemaining(value);
						},
					},
					form: { show: false },
				},
				is_active: {
					title: '状态',
					search: {
						show: true,
					},
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '正常', value: 'true' },
							{ label: '封禁中', value: 'false' },
						],
					}),
					column: {
						minWidth: 100,
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
