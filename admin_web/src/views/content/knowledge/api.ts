import { request } from '/@/utils/service';

/**
 * 获取公开知识库列表
 */
export function getKnowledgeList(params: any) {
	return request({
		url: '/api/content/knowledge/',
		method: 'get',
		params: params,
	});
}

/**
 * 获取知识库详情
 */
export function getKnowledgeDetail(id: string) {
	return request({
		url: `/api/content/knowledge/${id}/`,
		method: 'get',
	});
}

/**
 * 收藏知识库
 */
export function starKnowledge(id: string) {
	return request({
		url: `/api/content/knowledge/${id}/star/`,
		method: 'post',
	});
}

/**
 * 取消收藏知识库
 */
export function unstarKnowledge(id: string) {
	return request({
		url: `/api/content/knowledge/${id}/unstar/`,
		method: 'delete',
	});
}

/**
 * 下载知识库文件
 */
export function downloadKnowledgeFile(id: string, fileId: string) {
	return request({
		url: `/api/content/knowledge/${id}/files/${fileId}/`,
		method: 'get',
		responseType: 'blob',
	});
}

/**
 * 获取热门标签
 */
export function getPopularTags(limit: number = 20, tagType: string = 'knowledge') {
	return request({
		url: '/api/content/tags/popular/',
		method: 'get',
		params: { limit, tag_type: tagType },
	});
}
