import { request } from '/@/utils/service';

/**
 * 获取评论列表（支持分页）
 */
export function getComments(targetId: string, targetType: string, page: number = 1, pageSize: number = 10) {
	return request({
		url: '/api/content/comments/',
		method: 'get',
		params: {
			target_id: targetId,
			target_type: targetType,
			page,
			page_size: pageSize
		}
	});
}

/**
 * 获取指定评论的二级回复（分页）
 */
export function getReplies(commentId: string, page: number = 1, pageSize: number = 10) {
	return request({
		url: `/api/content/comments/${commentId}/replies/`,
		method: 'get',
		params: {
			page,
			page_size: pageSize
		}
	});
}

/**
 * 发表评论
 */
export function createComment(data: {
	target_id: string;
	target_type: string;
	content: string;
	parent?: string;
	reply_to?: string;
}) {
	return request({
		url: '/api/content/comments/',
		method: 'post',
		data
	});
}

/**
 * 删除评论
 */
export function deleteComment(commentId: string) {
	return request({
		url: `/api/content/comments/${commentId}/`,
		method: 'delete'
	});
}

/**
 * 评论反应（点赞/点踩/取消）
 */
export function reactComment(commentId: string, action: 'like' | 'dislike' | 'clear') {
	return request({
		url: `/api/content/comments/${commentId}/react/`,
		method: 'post',
		data: { action }
	});
}
