/**
 * 权限控制按钮显示工具函数
 *
 * 定义各模块的功能能力矩阵和权限-按钮映射规则，
 * 用于判断在给定权限配置下各操作按钮的显示/隐藏状态。
 */

/** 内容管理模块名称 */
export type ContentModule =
  | 'knowledge_base'
  | 'persona_card'
  | 'comment'
  | 'star_record'
  | 'upload_record'
  | 'download_record';

/** 操作按钮类型 */
export type ActionButton = 'batchApprove' | 'batchDelete' | 'export' | 'import';

/** 所有内容管理模块列表 */
export const ALL_MODULES: ContentModule[] = [
  'knowledge_base',
  'persona_card',
  'comment',
  'star_record',
  'upload_record',
  'download_record',
];

/**
 * 模块功能能力矩阵
 *
 * 定义每个模块支持哪些操作按钮（与模块业务特性相关，与权限无关）
 */
export const MODULE_CAPABILITIES: Record<ContentModule, Record<ActionButton, boolean>> = {
  knowledge_base: { batchApprove: true, batchDelete: true, export: true, import: true },
  persona_card: { batchApprove: true, batchDelete: true, export: true, import: true },
  comment: { batchApprove: false, batchDelete: true, export: true, import: false },
  star_record: { batchApprove: false, batchDelete: true, export: true, import: false },
  upload_record: { batchApprove: true, batchDelete: false, export: true, import: false },
  download_record: { batchApprove: false, batchDelete: false, export: true, import: false },
};

/**
 * 操作按钮对应的权限后缀映射
 *
 * 每个按钮需要的权限类型
 */
export const BUTTON_PERMISSION_SUFFIX: Record<ActionButton, string> = {
  batchApprove: 'Approve',
  batchDelete: 'Delete',
  export: 'Export',
  import: 'Create',
};

/**
 * 判断指定模块的指定按钮是否应该显示
 *
 * 按钮显示条件：模块支持该操作 AND 用户拥有对应权限
 *
 * @param module - 模块名称
 * @param button - 按钮类型
 * @param userPermissions - 用户拥有的权限列表
 * @returns 按钮是否应该显示
 */
export function shouldShowButton(
  module: ContentModule,
  button: ActionButton,
  userPermissions: string[],
): boolean {
  // 模块不支持该操作 → 不显示
  if (!MODULE_CAPABILITIES[module][button]) {
    return false;
  }

  // 构造所需权限字符串，如 "knowledge_base:Approve"
  const requiredPermission = `${module}:${BUTTON_PERMISSION_SUFFIX[button]}`;

  // 检查用户是否拥有该权限
  return userPermissions.includes(requiredPermission);
}

/**
 * 判断统计页面入口是否应该显示
 *
 * @param userPermissions - 用户拥有的权限列表
 * @returns 统计页面入口是否应该显示
 */
export function shouldShowStatisticsEntry(userPermissions: string[]): boolean {
  return userPermissions.includes('statistics:View');
}

/**
 * 获取指定模块所有按钮的显示状态
 *
 * @param module - 模块名称
 * @param userPermissions - 用户拥有的权限列表
 * @returns 各按钮的显示状态
 */
export function getModuleButtonVisibility(
  module: ContentModule,
  userPermissions: string[],
): Record<ActionButton, boolean> {
  return {
    batchApprove: shouldShowButton(module, 'batchApprove', userPermissions),
    batchDelete: shouldShowButton(module, 'batchDelete', userPermissions),
    export: shouldShowButton(module, 'export', userPermissions),
    import: shouldShowButton(module, 'import', userPermissions),
  };
}
