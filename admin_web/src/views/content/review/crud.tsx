import * as api from './api';
import {
	dict,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { commonCrudConfig } from '/@/utils/commonCrud';

/**
 * 内容类型中文映射
 */
const CONTENT_TYPE_MAP: Record<string, string> = {
	knowledge: '知识库',
	persona: '人设卡',
};

/**
 * 截断文本，超过指定长度显示省略号
 * @param text 原始文本
 * @param maxLength 最大长度，默认 80
 */
function truncateText(text: string, maxLength: number = 80): string {
	if (!text) return '-';
	return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

/**
 * 创建审核管理 CRUD 配置
 * 审核模块为只读列表 + 自定义行操作（通过/拒绝/退回），不支持新增和编辑
 */
export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求 — 适配后端 {items, total, page, page_size} 格式
	const pageRequest = async (query: any) => {
		// query 已经过全局 transformQuery 转换为 { page, limit, ...form }
		// 后端使用 page_size 而非 limit，需要转换参数名
		const params: any = { ...query };
		if (params.limit !== undefined) {
			params.page_size = params.limit;
			delete params.limit;
		}
		return await api.GetList(params);
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
				// 覆盖全局 transformRes，适配审核 API 的响应格式
				transformRes: ({ res }: any) => {
					const data = res.data || res;
					return {
						records: data.items || [],
						total: data.total || 0,
						currentPage: data.page || 1,
						pageSize: data.page_size || 10,
					};
				},
			},
			actionbar: {
				buttons: {
					add: { show: false }, // 审核模块不需要新增
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 320,
				buttons: {
					view: { show: false },
					edit: { show: false },
					remove: { show: false },
					approve: {
						text: '通过',
						type: 'text',
						style: { color: '#67c23a' },
						show: auth('review:Approve'),
						click: (ctx: any) => context.handleApprove(ctx.row),
					},
					reject: {
						text: '拒绝',
						type: 'text',
						style: { color: '#f56c6c' },
						show: auth('review:Reject'),
						click: (ctx: any) => context.handleReject(ctx.row),
					},
					return: {
						text: '退回',
						type: 'text',
						style: { color: '#e6a23c' },
						show: auth('review:Return'),
						click: (ctx: any) => context.handleReturn(ctx.row),
					},
					detail: {
						text: '详情',
						type: 'text',
						click: (ctx: any) => context.handleViewDetail(ctx.row),
					},
					aiReview: {
						text: 'AI 审核',
						type: 'text',
						style: { color: '#409eff' },
						show: auth('review:AIReview'),
						// disabled: (ctx: any) => context.aiReviewRowLoading[ctx.row.id],
						// loading: (ctx: any) => context.aiReviewRowLoading[ctx.row.id],
						click: (ctx: any) => context.handleAIReview(ctx.row),
					},
					report: {
						text: '查看报告',
						type: 'text',
						style: { color: '#909399' },
						click: (ctx: any) => context.handleViewReport(ctx.row),
					}
				},
			},
			// 搜索区域配置
			search: {
				show: true,
				collapse: false,
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
					title: '内容名称',
					search: {
						show: true,
						component: {
							name: 'input',
							placeholder: '搜索名称或描述',
						},
						// 将搜索框的值映射到 search 参数
						valueResolve(context: any) {
							const { value } = context;
							if (value) {
								context.form.search = value;
								delete context.form.name;
							}
						},
					},
					column: {
						minWidth: 180,
						showOverflowTooltip: true,
					},
					form: { show: false },
				},
				content_type: {
					title: '内容类型',
					search: { show: true },
					type: 'dict-select',
					dict: dict({
						data: [
							{ label: '知识库', value: 'knowledge' },
							{ label: '人设卡', value: 'persona' },
						],
					}),
					column: {
						width: 100,
						align: 'center',
						formatter: ({ value }: any) => CONTENT_TYPE_MAP[value] || value,
					},
					form: { show: false },
				},
				uploader_name: {
					title: '上传者',
					column: {
						width: 120,
						formatter: ({ value }: any) => value || '-',
					},
					form: { show: false },
				},
				tags: {
					title: '标签',
					column: {
						minWidth: 150,
						showOverflowTooltip: true,
						formatter: ({ value }: any) => value || '-',
					},
					form: { show: false },
				},
				file_count: {
					title: '文件数',
					column: {
						width: 80,
						align: 'center',
						formatter: ({ value }: any) => value ?? 0,
					},
					form: { show: false },
				},
				ai_review_decision: {
					title: 'AI 审核',
					column: {
						width: 110,
						align: 'center',
					},
					form: { show: false },
				},
				...commonCrudConfig({
					create_datetime: {
						table: true,
						search: true,
					},
				}),
			},
		},
	};
};
