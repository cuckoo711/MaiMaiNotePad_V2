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
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 分页查询请求 — 适配后端 {items, total, page, page_size} 格式
	const pageRequest = async (query: UserPageQuery) => {
		const res = await api.GetList(query);
		// Fast-CRUD 需要 { records, total, currentPage, pageSize }
		const data = res.data || res;
		return {
			records: data.items || [],
			total: data.total || 0,
			currentPage: data.page || 1,
			pageSize: data.page_size || 10,
		};
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
			},
			actionbar: {
				buttons: {
					add: { show: false }, // 审核模块不需要新增
				},
			},
			rowHandle: {
				show: false, // 使用自定义行操作模板
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
				description: {
					title: '描述',
					column: {
						minWidth: 200,
						showOverflowTooltip: true,
						formatter: ({ value }: any) => truncateText(value, 60),
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
