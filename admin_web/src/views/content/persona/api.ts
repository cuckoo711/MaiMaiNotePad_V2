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
