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
const TARGET_TYPE_MAP: Record<string, string> = {
	knowledge: '知识库',
	persona: '人设卡',
};

/**
 * 截断文本，超过指定长度显示省略号
 * @param text 原始文本
 * @param maxLength 最大长度，默认50
 */
export function truncateText(text: string, maxLength: number = 50): string {
	if (!text) return '-';
	return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

/**
 * 创建评论管理 CRUD 配置
 * 评论模块为只读 + 删除，不支持新增和编辑
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求
	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
	};

	// 删除请求（管理后台软删除）
	const delRequest = async ({ row }: DelReq) => {
		return await api.AdminDeleteObj(row.id);
	};

	return {
		crudOptions: {
			table: {
				remove: {
					confirmMessage: '确定删除该评论吗？一级评论将连带删除其子评论。',
				},
			},
			request: {
				pageRequest,
				delRequest,
			},
			actionbar: {
				buttons: {
					add: {
						show: false, // 管理后台不需要新增评论
					},
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 250,
				buttons: {
					view: {
						text: '查看详情',
						type: 'text',
						show: auth('comment:View'),
					},
					edit: {
						show: false, // 评论不支持编辑
					},
					replies: {
						text: '查看回复',
						type: 'text',
						show: auth('comment:View'),
					},
					remove: {
						iconRight: 'Delete',
						type: 'text',
						show: auth('comment:Delete'),
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
				user_name: {
					title: '评论用户',
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
				content: {
					title: '评论内容',
					search: {
						show: true,
						component: {
							name: 'input',
							placeholder: '搜索评论内容',
						},
					},
					type: 'input',
					column: {
						minWidth: 200,
						showOverflowTooltip: true,
						formatter: ({ value }: any) => {
							return truncateText(value, 50);
						},
					},
					form: { show: false },
				},
				parent: {
					title: '父评论',
					column: {
						minWidth: 100,
						formatter: ({ value }: any) => {
							return value ? '二级评论' : '一级评论';
						},
					},
					form: { show: false },
				},
				like_count: {
					title: '点赞数',
					type: 'number',
					column: {
						minWidth: 80,
						align: 'right',
						formatter: ({ value }: any) => {
							return value ?? 0;
						},
					},
					form: { show: false },
				},
				dislike_count: {
					title: '点踩数',
					type: 'number',
					column: {
						minWidth: 80,
						align: 'right',
						formatter: ({ value }: any) => {
							return value ?? 0;
						},
					},
					form: { show: false },
				},
				is_deleted: {
					title: '删除状态',
					search: {
						show: true,
					},
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '正常', value: 'false' },
							{ label: '已删除', value: 'true' },
						],
					}),
					column: {
						minWidth: 80,
						formatter: ({ value }: any) => {
							return value ? '已删除' : '正常';
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
