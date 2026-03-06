import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

/**
 * 翻译管理 API 接口
 */

// API 基础路径
export const apiPrefix = '/api/system/translation/';

/**
 * 获取翻译列表（支持分页和过滤）
 * 
 * @param query 查询参数，包含分页、搜索和过滤条件
 * @returns Promise<APIResponseData> 翻译列表数据
 */
export function GetList(query: PageQuery) {
    return request({
        url: apiPrefix,
        method: 'get',
        params: query,
    });
}

/**
 * 获取单个翻译记录详情
 * 
 * @param id 翻译记录 ID
 * @returns Promise<APIResponseData> 翻译记录详情
 */
export function GetObj(id: InfoReq) {
    return request({
        url: apiPrefix + id,
        method: 'get',
    });
}

/**
 * 添加新翻译记录
 * 
 * @param obj 翻译记录数据
 * @returns Promise<APIResponseData> 添加结果
 */
export function AddObj(obj: AddReq) {
    return request({
        url: apiPrefix,
        method: 'post',
        data: obj,
    });
}

/**
 * 更新翻译记录
 * 
 * @param obj 翻译记录数据（包含 ID）
 * @returns Promise<APIResponseData> 更新结果
 */
export function UpdateObj(obj: EditReq) {
    return request({
        url: apiPrefix + obj.id + '/',
        method: 'put',
        data: obj,
    });
}

/**
 * 删除翻译记录
 * 
 * @param id 翻译记录 ID
 * @returns Promise<APIResponseData> 删除结果
 */
export function DelObj(id: DelReq) {
    return request({
        url: apiPrefix + id + '/',
        method: 'delete',
        data: { id },
    });
}

/**
 * 批量更新翻译记录状态
 * 
 * @param ids 翻译记录 ID 数组
 * @param status 目标状态（true=启用，false=禁用）
 * @returns Promise<APIResponseData> 批量更新结果
 */
export function BatchUpdateStatus(ids: number[], status: boolean) {
    return request({
        url: apiPrefix + 'batch_update_status/',
        method: 'post',
        data: { ids, status },
    });
}

/**
 * 获取所有翻译类型
 * 
 * @returns Promise<APIResponseData> 翻译类型列表
 */
export function GetTypes() {
    return request({
        url: apiPrefix + 'get_types/',
        method: 'get',
    });
}
