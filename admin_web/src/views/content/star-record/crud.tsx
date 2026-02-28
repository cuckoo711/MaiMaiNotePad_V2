import * as api from './api';
import {
	dict,
	UserPageQuery,
	DelReq,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { commonCrudConfig } from '/@/utils/commonCrud';

/**
 * 目标类型中文映射
 */
export const TARGET_TYPE_MAP: Record<string, string> = {
	knowledge: '知识库',
	persona: '人设卡',
};

/**
 * 创建收藏记录管理 CRUD 配置
 * 收藏记录模块为只读 + 删除，不支持新增和编辑
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求
	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
	};

	// 删除请求
	const delRequest = async ({ row }: DelReq) => {
		return await api.DelObj(row.id);
	};

	return {
		crudOptions: {
			table: {
				remove: {
					confirmMessage: '确定删除该收藏记录吗？',
				},
			},
			request: {
				pageRequest,
				delRequest,
			},
			actionbar: {
				buttons: {
					add: {
						show: false, // 收藏记录不支持新增
					},
					stats: {
						text: '统计',
						type: 'primary',
						show: auth('star_record:List'),
						icon: 'DataAnalysis',
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
			rowHandle: {
				fixed: 'right',
				width: 200,
				buttons: {
					view: {
						text: '查看详情',
						type: 'text',
						show: auth('star_record:View'),
					},
					edit: {
						show: false, // 收藏记录不支持编辑
					},
					remove: {
						iconRight: 'Delete',
						type: 'text',
						show: auth('star_record:Delete'),
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
				user_name: {
					title: '用户',
					search: {
						show: true,
						component: {
							name: 'input',
							placeholder: '搜索用户',
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
				target_id: {
					title: '目标ID',
					column: {
						minWidth: 120,
						showOverflowTooltip: true,
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
