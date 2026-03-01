import * as api from './api';
import {
	dict,
	UserPageQuery,
	AddReq,
	DelReq,
	EditReq,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { auth } from '/@/utils/authFunction';
import { commonCrudConfig } from '/@/utils/commonCrud';

/**
 * 创建 AI 审核模型管理 CRUD 配置
 */
export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
	};
	const addRequest = async (req: AddReq) => {
		return await api.AddObj(req.form);
	};
	const editRequest = async (req: EditReq) => {
		req.form.id = req.row.id;
		return await api.EditObj(req.form);
	};
	const delRequest = async (req: DelReq) => {
		return await api.DelObj(req.row);
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
				addRequest,
				editRequest,
				delRequest,
			},
			actionbar: {
				buttons: {
					add: { show: auth('aiModel:Create') },
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 200,
				buttons: {
					view: { show: true, type: 'text',},
					edit: { show: auth('aiModel:Update'), type: 'text',},
					remove: { show: auth('aiModel:Delete'), type: 'text', },
				},
			},
			search: {
				show: true,
				collapse: false,
				buttons: { reset: { show: true } },
			},
			columns: {
				_index: {
					title: '序号',
					form: { show: false },
					column: {
						type: 'index',
						align: 'center',
						width: '60px',
					},
				},
				name: {
					title: '模型名称',
					search: {
						show: true,
						component: { placeholder: '搜索模型名称' },
					},
					column: { minWidth: 200, showOverflowTooltip: true },
					form: {
						rules: [{ required: true, message: '请输入模型名称' }],
						component: { placeholder: '如 deepseek-ai/DeepSeek-R1-0528-Qwen3-8B' },
					},
				},
				provider: {
					title: 'API 提供商',
					search: { show: true },
					column: { width: 120, align: 'center' },
					form: {
						value: 'siliconflow',
						component: { placeholder: '如 siliconflow' },
					},
				},
				parameter_size: {
					title: '参数量(B)',
					column: {
						width: 100,
						align: 'center',
						formatter: ({ value }: any) => value ? `${value}B` : '-',
					},
					form: {
						value: 7.0,
						rules: [{ required: true, message: '请输入参数量' }],
						component: { placeholder: '如 7.0' },
						helper: '单位为十亿（B），如 7.0 表示 7B 模型',
					},
				},
				max_context_length: {
					title: '最大上下文',
					column: {
						width: 110,
						align: 'center',
						formatter: ({ value }: any) => value ? `${(value / 1000).toFixed(0)}k` : '-',
					},
					form: {
						value: 32000,
						rules: [{ required: true, message: '请输入最大上下文长度' }],
						component: { placeholder: '如 128000' },
						helper: '单位为 token 数',
					},
				},
				rpm_limit: {
					title: 'RPM 限制',
					column: { width: 100, align: 'center' },
					form: {
						value: 1000,
						component: { placeholder: '每分钟最大请求数' },
						helper: 'Requests Per Minute',
					},
				},
				tpm_limit: {
					title: 'TPM 限制',
					column: {
						width: 110,
						align: 'center',
						formatter: ({ value }: any) => {
							if (!value) return '-';
							return value >= 1000 ? `${(value / 1000).toFixed(0)}k` : value;
						},
					},
					form: {
						value: 50000,
						component: { placeholder: '每分钟最大 Token 数' },
						helper: 'Tokens Per Minute',
					},
				},
				priority: {
					title: '优先级',
					column: { width: 80, align: 'center' },
					form: {
						value: 0,
						component: { placeholder: '数值越小优先级越高' },
						helper: '0 为最高优先级',
					},
				},
				cooldown_seconds: {
					title: '冷却时间(秒)',
					column: { width: 110, align: 'center' },
					form: {
						value: 65,
						component: { placeholder: '触发限速后的冷却时间' },
					},
				},
				is_enabled: {
					title: '启用状态',
					search: { show: true },
					type: 'dict-switch',
					dict: dict({
						data: [
							{ label: '启用', value: true, color: 'success' },
							{ label: '禁用', value: false, color: 'danger' },
						],
					}),
					column: { width: 90, align: 'center' },
					form: { value: true },
				},
				...commonCrudConfig({
					create_datetime: { table: true },
				}),
			},
		},
	};
};
