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
 * 格式化剩余时长（带倒计时）
 * @param muted_until 禁言截止时间
 */
export function formatRemainingWithCountdown(muted_until?: string): string {
	if (!muted_until) return '永久';
	
	const now = dayjs();
	const until = dayjs(muted_until);
	const diff = until.diff(now);
	
	if (diff <= 0) return '已过期';
	
	const days = Math.floor(diff / (1000 * 60 * 60 * 24));
	const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
	const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
	
	if (days > 0) {
		return `还剩${days}天${hours}小时${minutes}分钟`;
	}
	if (hours > 0) {
		return `还剩${hours}小时${minutes}分钟`;
	}
	return `还剩${minutes}分钟`;
}

/**
 * 获取自动解封状态
 * @param row 数据行
 */
export function getAutoUnmuteStatus(row: any): string {
	if (!row.is_active) {
		return '已解封';
	}
	if (row.is_manually_modified) {
		return '已被人工修改';
	}
	if (row.muted_until) {
		const now = dayjs();
		const until = dayjs(row.muted_until);
		if (until.diff(now) <= 0) {
			return '已过期';
		}
		return '等待中';
	}
	return '永久';
}

/**
 * 创建AI自动禁言 CRUD 配置
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求
	const pageRequest = async (query: UserPageQuery) => {
		return await api.getAutoMuteList(query);
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
						show: false, // AI自动禁言不支持手动添加
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
				user: {
					title: '用户ID',
					column: {
						minWidth: 100,
					},
					form: { show: false },
				},
				mute_reason: {
					title: '禁言原因',
					column: {
						minWidth: 200,
						showOverflowTooltip: true,
					},
					form: { show: false },
				},
				muted_until: {
					title: '剩余时长',
					column: {
						minWidth: 180,
						formatter: ({ value, row }: any) => {
							if (!row.is_active) return '已解除';
							if (row.is_manually_modified) return '已被人工修改';
							return formatRemainingWithCountdown(value);
						},
					},
					form: { show: false },
				},
				auto_unmute_status: {
					title: '自动解封状态',
					search: {
						show: true,
					},
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '等待中', value: 'pending' },
							{ label: '已解封', value: 'completed' },
							{ label: '已被人工修改', value: 'modified' },
						],
					}),
					column: {
						minWidth: 120,
						formatter: ({ row }: any) => {
							return getAutoUnmuteStatus(row);
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
