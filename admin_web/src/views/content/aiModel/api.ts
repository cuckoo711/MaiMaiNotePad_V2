import { request } from '/@/utils/service';
import { AddReq, DelReq, EditReq, InfoReq, PageQuery } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/content/ai-models/';

/**
 * 获取 AI 模型列表（分页）
 */
export function GetList(query: PageQuery) {
	return request({ url: apiPrefix, method: 'get', params: query });
}

/**
 * 新增 AI 模型
 */
export function AddObj(obj: AddReq) {
	return request({ url: apiPrefix, method: 'post', data: obj });
}

/**
 * 更新 AI 模型
 */
export function EditObj(obj: EditReq) {
	return request({ url: apiPrefix + obj.id + '/', method: 'put', data: obj });
}

/**
 * 删除 AI 模型
 */
export function DelObj(obj: DelReq) {
	return request({ url: apiPrefix + obj.id + '/', method: 'delete' });
}

/**
 * 获取 AI 模型详情
 */
export function GetObj(obj: InfoReq) {
	return request({ url: apiPrefix + obj.id + '/', method: 'get' });
}
