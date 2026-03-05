import { request, downloadFile } from '/@/utils/service';

/**
 * 解析 TOML 文件
 * @param file TOML 文件对象
 */
export function parseToml(file: File) {
	const formData = new FormData();
	formData.append('file', file);
	
	return request({
		url: '/api/content/persona/parse-toml/',
		method: 'post',
		data: formData,
		headers: {
			'Content-Type': 'multipart/form-data',
		},
	});
}

/**
 * 创建人设卡及配置
 * @param data 人设卡数据（包含基本信息、配置项和敏感信息确认）
 */
export function createPersonaCardWithConfig(data: {
	name: string;
	description: string;
	copyright_owner?: string;
	tags?: string[];
	is_public: boolean;
	configs: any[];
	sensitive_confirmation?: {
		text: string;
		locations: any[];
	};
}) {
	return request({
		url: '/api/content/persona/create-with-config/',
		method: 'post',
		data,
	});
}

/**
 * 确认敏感信息
 * @param id 人设卡 ID
 * @param data 确认数据（包含确认声明、敏感信息位置和验证码）
 */
export function confirmSensitive(id: string, data: {
	confirmation_text: string;
	sensitive_locations: any[];
	captcha_key: string;
	captcha_value: string;
}) {
	return request({
		url: `/api/content/persona/${id}/confirm-sensitive/`,
		method: 'post',
		data,
	});
}

/**
 * 获取配置项
 * @param id 人设卡 ID
 */
export function getConfig(id: string) {
	return request({
		url: `/api/content/persona/${id}/config/`,
		method: 'get',
	});
}

/**
 * 更新配置项
 * @param id 人设卡 ID
 * @param data 更新数据（包含配置项更新和删除的配置块）
 */
export function updateConfig(id: string, data: {
	updates: Array<{
		section: string;
		key: string;
		value: string;
		comment?: string;
	}>;
	deleted_sections?: string[];
}) {
	return request({
		url: `/api/content/persona/${id}/config/`,
		method: 'put',
		data,
	});
}

/**
 * 导出 TOML 文件
 * @param id 人设卡 ID
 */
export function exportToml(id: string) {
	return request({
		url: `/api/content/persona/${id}/export-toml/`,
		method: 'post',
	});
}

/**
 * 下载人设卡（导出为 TOML 文件并下载）
 * @param id 人设卡 ID
 * @param filename 文件名（可选，默认为 bot_config.toml）
 */
export function downloadPersonaCard(id: string, filename: string = 'bot_config.toml') {
	downloadFile({
		url: `/api/content/persona/${id}/download/`,
		method: 'get',
		params: {},
		filename,
	});
}

/**
 * 切换公开/私有状态
 * @param id 人设卡 ID
 */
export function togglePublic(id: string) {
	return request({
		url: `/api/content/persona/${id}/toggle-public/`,
		method: 'post',
	});
}

/**
 * 获取人设卡列表（支持分页和筛选）
 * @param params 查询参数
 */
export function getPersonaCards(params?: {
	page?: number;
	page_size?: number;
	is_public?: boolean;
	is_pending?: boolean;
	search?: string;
}) {
	return request({
		url: '/api/content/persona/',
		method: 'get',
		params,
	});
}

/**
 * 获取人设卡详情
 * @param id 人设卡 ID
 */
export function getPersonaCard(id: string) {
	return request({
		url: `/api/content/persona/${id}/`,
		method: 'get',
	});
}

/**
 * 删除人设卡（软删除）
 * @param id 人设卡 ID
 */
export function deletePersonaCard(id: string) {
	return request({
		url: `/api/content/persona/${id}/`,
		method: 'delete',
	});
}
