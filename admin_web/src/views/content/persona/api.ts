import { request } from '/@/utils/service';

/**
 * 获取公开人设卡列表
 */
export function getPersonaList(params: any) {
	return request({
		url: '/api/content/persona/',
		method: 'get',
		params: params,
	});
}

/**
 * 获取人设卡详情
 */
export function getPersonaDetail(id: string) {
	return request({
		url: `/api/content/persona/${id}/`,
		method: 'get',
	});
}

/**
 * 收藏人设卡
 */
export function starPersona(id: string) {
	return request({
		url: `/api/content/persona/${id}/star/`,
		method: 'post',
	});
}

/**
 * 取消收藏人设卡
 */
export function unstarPersona(id: string) {
	return request({
		url: `/api/content/persona/${id}/unstar/`,
		method: 'delete',
	});
}

/**
 * 下载人设卡文件
 */
export function downloadPersonaFile(id: string, fileId: string) {
	return request({
		url: `/api/content/persona/${id}/files/${fileId}/`,
		method: 'get',
		responseType: 'blob',
	});
}

/**
 * 预览人设卡文件（获取文本内容）
 */
export function previewPersonaFile(id: string, fileId: string) {
	return request({
		url: `/api/content/persona/${id}/files/${fileId}/`,
		method: 'get',
		responseType: 'blob',
	});
}

/**
 * 解析人设卡 TOML 文件（获取结构化数据）
 */
export function parsePersonaToml(id: string, fileId: string) {
	return request({
		url: `/api/content/persona/${id}/files/${fileId}/parse/`,
		method: 'get',
	});
}

/**
 * 获取热门标签
 */
export function getPopularTags(limit: number = 20, tagType: string = 'persona') {
	return request({
		url: '/api/content/tags/popular/',
		method: 'get',
		params: { limit, tag_type: tagType },
	});
}

/**
 * 获取我的人设卡列表
 */
export function getPersonaCardList(params: any) {
	return request({
		url: '/api/content/persona/my/',
		method: 'get',
		params: params,
	});
}

/**
 * 获取人设卡详情（包含基本信息）
 */
export function getPersonaCardDetail(id: string) {
	return request({
		url: `/api/content/persona/${id}/`,
		method: 'get',
	});
}

/**
 * 获取人设卡配置数据
 */
export function getPersonaCardConfig(id: string) {
	return request({
		url: `/api/content/persona/${id}/config/`,
		method: 'get',
	});
}

/**
 * 更新人设卡基本信息
 */
export function updatePersonaCardBasicInfo(id: string, data: any) {
	return request({
		url: `/api/content/persona/${id}/basic-info/`,
		method: 'put',
		data: data,
	});
}

/**
 * 更新人设卡配置
 */
export function updatePersonaCardConfig(id: string, data: any) {
	return request({
		url: `/api/content/persona/${id}/config/`,
		method: 'put',
		data: data,
	});
}

/**
 * 切换人设卡公开/私有状态
 */
export function togglePersonaCardPublic(id: string) {
	return request({
		url: `/api/content/persona/${id}/toggle-public/`,
		method: 'post',
	});
}

/**
 * 删除人设卡（软删除）
 */
export function deletePersonaCard(id: string) {
	return request({
		url: `/api/content/persona/${id}/`,
		method: 'delete',
	});
}

/**
 * 下载人设卡配置文件
 */
export function downloadPersonaCard(id: string, filename: string) {
	return request({
		url: `/api/content/persona/${id}/download/`,
		method: 'get',
		responseType: 'blob',
	}).then((response: any) => {
		// 确保文件名包含 .toml 后缀
		let downloadFilename = filename || 'bot_config';
		if (!downloadFilename.toLowerCase().endsWith('.toml')) {
			downloadFilename += '.toml';
		}
		
		// 创建下载链接
		const blob = new Blob([response], { type: 'application/toml' });
		const url = window.URL.createObjectURL(blob);
		const link = document.createElement('a');
		link.href = url;
		link.download = downloadFilename;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		window.URL.revokeObjectURL(url);
	});
}
