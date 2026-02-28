/**
 * 权限控制按钮显示属性测试
 *
 * Feature: admin-content-enhancement, Property 5: 权限控制按钮显示
 *
 * **Validates: Requirements 2.1, 3.1, 4.1, 5.1, 9.6**
 *
 * 属性描述：
 * 对于任意权限配置和任意模块，批量审核按钮仅在用户具有对应模块的 Approve 权限时显示，
 * 批量删除按钮仅在用户具有 Delete 权限时显示，导出按钮仅在用户具有 Export 权限时显示，
 * 导入按钮仅在用户具有 Create 权限时显示，统计页面入口仅在用户具有 statistics:View 权限时显示。
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  shouldShowButton,
  shouldShowStatisticsEntry,
  getModuleButtonVisibility,
  MODULE_CAPABILITIES,
  BUTTON_PERMISSION_SUFFIX,
  ALL_MODULES,
  type ContentModule,
  type ActionButton,
} from '../permissionControlUtils';

/** 所有操作按钮类型 */
const ALL_BUTTONS: ActionButton[] = ['batchApprove', 'batchDelete', 'export', 'import'];

/**
 * 所有可能的权限字符串列表
 * 包含各模块的各种权限以及统计页面权限
 */
const ALL_POSSIBLE_PERMISSIONS: string[] = [
  ...ALL_MODULES.flatMap((m) => [
    `${m}:Approve`,
    `${m}:Delete`,
    `${m}:Export`,
    `${m}:Create`,
    `${m}:Update`,
    `${m}:List`,
    `${m}:View`,
  ]),
  'statistics:View',
];

/**
 * 生成任意权限子集的 Arbitrary
 * 从所有可能的权限中随机选取一个子集
 */
const permissionSetArbitrary = fc.subarray(ALL_POSSIBLE_PERMISSIONS);

/** 生成任意模块名的 Arbitrary */
const moduleArbitrary = fc.constantFrom(...ALL_MODULES);

/** 生成任意按钮类型的 Arbitrary */
const buttonArbitrary = fc.constantFrom(...ALL_BUTTONS);

describe('Feature: admin-content-enhancement, Property 5: 权限控制按钮显示', () => {
  it('对于任意模块和权限配置，按钮显示当且仅当模块支持该操作且用户拥有对应权限', () => {
    fc.assert(
      fc.property(
        moduleArbitrary,
        buttonArbitrary,
        permissionSetArbitrary,
        (module: ContentModule, button: ActionButton, permissions: string[]) => {
          const visible = shouldShowButton(module, button, permissions);

          // 构造该按钮所需的权限字符串
          const requiredPermission = `${module}:${BUTTON_PERMISSION_SUFFIX[button]}`;
          const moduleSupports = MODULE_CAPABILITIES[module][button];
          const hasPermission = permissions.includes(requiredPermission);

          // 核心属性：按钮可见 ⟺ 模块支持该操作 ∧ 用户拥有权限
          expect(visible).toBe(moduleSupports && hasPermission);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('模块不支持的操作，无论权限如何，按钮都不显示', () => {
    fc.assert(
      fc.property(
        moduleArbitrary,
        buttonArbitrary,
        permissionSetArbitrary,
        (module: ContentModule, button: ActionButton, permissions: string[]) => {
          if (!MODULE_CAPABILITIES[module][button]) {
            // 模块不支持该操作 → 按钮一定不显示
            expect(shouldShowButton(module, button, permissions)).toBe(false);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('用户缺少权限时，即使模块支持该操作，按钮也不显示', () => {
    fc.assert(
      fc.property(
        moduleArbitrary,
        buttonArbitrary,
        (module: ContentModule, button: ActionButton) => {
          // 构造一个不包含所需权限的权限集
          const requiredPermission = `${module}:${BUTTON_PERMISSION_SUFFIX[button]}`;
          const permissionsWithout = ALL_POSSIBLE_PERMISSIONS.filter(
            (p) => p !== requiredPermission,
          );

          if (MODULE_CAPABILITIES[module][button]) {
            // 模块支持但缺少权限 → 不显示
            expect(shouldShowButton(module, button, permissionsWithout)).toBe(false);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('用户拥有权限且模块支持时，按钮应该显示', () => {
    fc.assert(
      fc.property(
        moduleArbitrary,
        buttonArbitrary,
        permissionSetArbitrary,
        (module: ContentModule, button: ActionButton, extraPermissions: string[]) => {
          const requiredPermission = `${module}:${BUTTON_PERMISSION_SUFFIX[button]}`;
          // 确保权限集中包含所需权限
          const permissions = [...new Set([...extraPermissions, requiredPermission])];

          if (MODULE_CAPABILITIES[module][button]) {
            // 模块支持且有权限 → 显示
            expect(shouldShowButton(module, button, permissions)).toBe(true);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('统计页面入口仅在用户具有 statistics:View 权限时显示', () => {
    fc.assert(
      fc.property(permissionSetArbitrary, (permissions: string[]) => {
        const visible = shouldShowStatisticsEntry(permissions);
        const hasStatisticsPermission = permissions.includes('statistics:View');

        // 核心属性：统计入口可见 ⟺ 拥有 statistics:View 权限
        expect(visible).toBe(hasStatisticsPermission);
      }),
      { numRuns: 100 },
    );
  });

  it('getModuleButtonVisibility 返回的所有按钮状态与 shouldShowButton 一致', () => {
    fc.assert(
      fc.property(
        moduleArbitrary,
        permissionSetArbitrary,
        (module: ContentModule, permissions: string[]) => {
          const visibility = getModuleButtonVisibility(module, permissions);

          // 每个按钮的可见性应与 shouldShowButton 结果一致
          for (const button of ALL_BUTTONS) {
            expect(visibility[button]).toBe(shouldShowButton(module, button, permissions));
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('验证模块能力矩阵与设计文档一致', () => {
    // 批量审核：仅 knowledge_base, persona_card, upload_record 支持
    expect(MODULE_CAPABILITIES.knowledge_base.batchApprove).toBe(true);
    expect(MODULE_CAPABILITIES.persona_card.batchApprove).toBe(true);
    expect(MODULE_CAPABILITIES.upload_record.batchApprove).toBe(true);
    expect(MODULE_CAPABILITIES.comment.batchApprove).toBe(false);
    expect(MODULE_CAPABILITIES.star_record.batchApprove).toBe(false);
    expect(MODULE_CAPABILITIES.download_record.batchApprove).toBe(false);

    // 批量删除：仅 knowledge_base, persona_card, comment, star_record 支持
    expect(MODULE_CAPABILITIES.knowledge_base.batchDelete).toBe(true);
    expect(MODULE_CAPABILITIES.persona_card.batchDelete).toBe(true);
    expect(MODULE_CAPABILITIES.comment.batchDelete).toBe(true);
    expect(MODULE_CAPABILITIES.star_record.batchDelete).toBe(true);
    expect(MODULE_CAPABILITIES.upload_record.batchDelete).toBe(false);
    expect(MODULE_CAPABILITIES.download_record.batchDelete).toBe(false);

    // 导出：所有6个模块都支持
    for (const module of ALL_MODULES) {
      expect(MODULE_CAPABILITIES[module].export).toBe(true);
    }

    // 导入：仅 knowledge_base, persona_card 支持
    expect(MODULE_CAPABILITIES.knowledge_base.import).toBe(true);
    expect(MODULE_CAPABILITIES.persona_card.import).toBe(true);
    expect(MODULE_CAPABILITIES.comment.import).toBe(false);
    expect(MODULE_CAPABILITIES.star_record.import).toBe(false);
    expect(MODULE_CAPABILITIES.upload_record.import).toBe(false);
    expect(MODULE_CAPABILITIES.download_record.import).toBe(false);
  });
});
