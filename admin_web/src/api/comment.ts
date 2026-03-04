import { request } from '/@/utils/service';

/**
 * 获取评论列表
 */
export function getComments(targetId: string, targetType: string) {
	return request({
		url: '/api/content/comments/',
		method: 'get',
		params: {
			target_id: targetId,
			target_type: targetType
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
