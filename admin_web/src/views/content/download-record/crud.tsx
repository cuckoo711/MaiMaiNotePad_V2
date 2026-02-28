import * as api from './api';
import {
	dict,
	UserPageQuery,
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
 * 创建下载记录管理 CRUD 配置
 * 下载记录模块为只读，不支持新增、编辑和删除
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求
	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
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
						show: false, // 下载记录不支持新增
					},
					stats: {
						text: '统计',
						type: 'primary',
						show: auth('download_record:List'),
						icon: 'DataAnalysis',
					},
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 150,
				buttons: {
					view: {
						text: '查看详情',
						type: 'text',
						show: auth('download_record:View'),
					},
					edit: {
						show: false, // 下载记录不支持编辑
					},
					remove: {
						show: false, // 下载记录不支持删除
					},
				},
			},
			columns: {
				// 复选框选择列，用于批量操作
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
