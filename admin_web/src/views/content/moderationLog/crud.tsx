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
 * 截断文本，超过指定长度显示省略号
 */
function truncateText(text: string, maxLength: number = 60): string {
	if (!text) return '-';
	return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

/**
 * 创建 AI 审核日志 CRUD 配置
 * 审核日志为只读模块，不支持新增、编辑和删除
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
			},
			actionbar: {
				buttons: {
					add: { show: false },
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 100,
				buttons: {
					edit: { show: false },
					remove: { show: false },
					view: {
						text: '详情',
						type: 'text',
						show: auth('moderationLog:View'),
					},
				},
			},
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
					},
				},
				source: {
					title: '审核来源',
					search: { show: true },
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '评论审核', value: 'comment' },
							{ label: '知识库审核', value: 'knowledge' },
							{ label: '人设卡审核', value: 'persona' },
							{ label: '知识库文件审核', value: 'knowledge_file' },
						],
					}),
					column: {
						minWidth: 120,
						align: 'center',
					},
					form: { show: false },
				},
				decision: {
					title: '审核决策',
					search: { show: true },
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '通过', value: 'true', color: 'success' },
							{ label: '拒绝', value: 'false', color: 'danger' },
							{ label: '不确定', value: 'unknown', color: 'warning' },
							{ label: '调用异常', value: 'error', color: 'info' },
						],
					}),
					column: {
						minWidth: 100,
						align: 'center',
					},
					form: { show: false },
				},
				input_text: {
					title: '审核文本',
					search: {
						show: true,
						component: {
							name: 'input',
							placeholder: '搜索审核文本',
						},
					},
					column: {
						minWidth: 260,
						showOverflowTooltip: true,
						formatter: ({ value }: any) => truncateText(value, 60),
					},
					form: { show: false },
				},
				user_name: {
					title: '触发用户',
					column: {
						minWidth: 110,
						formatter: ({ value }: any) => value || '-',
					},
					form: { show: false },
				},
				model_name: {
					title: '模型',
					search: { show: true },
					column: {
						minWidth: 160,
						showOverflowTooltip: true,
					},
					form: { show: false },
				},
				total_tokens: {
					title: 'Token 消耗',
					column: {
						minWidth: 110,
						align: 'right',
						formatter: ({ value }: any) => value ?? 0,
					},
					form: { show: false },
				},
				latency_ms: {
					title: '耗时(ms)',
					column: {
						minWidth: 100,
						align: 'right',
						formatter: ({ value }: any) => value ?? 0,
					},
					form: { show: false },
				},
				is_success: {
					title: '调用状态',
					search: { show: true },
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '成功', value: true, color: 'success' },
							{ label: '失败', value: false, color: 'danger' },
						],
					}),
					column: {
						minWidth: 90,
						align: 'center',
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
