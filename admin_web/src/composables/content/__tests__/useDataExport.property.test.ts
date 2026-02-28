/**
 * 数据导出 composable 属性测试
 *
 * 使用 fast-check 验证数据导出相关的正确性属性
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  shouldShowLargeDataWarning,
  getExportOptions,
  buildExportApiParams,
  EXPORT_LARGE_DATA_THRESHOLD,
  type ExportParams,
} from '../dataExportUtils';

describe('Feature: admin-content-enhancement, 属性 9: 导出数据量阈值提示', () => {
  it('对于任意正整数 N > 5000，应触发大数据量提示', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: EXPORT_LARGE_DATA_THRESHOLD + 1, max: 1000000 }),
        (n: number) => {
          expect(shouldShowLargeDataWarning(n)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('对于任意正整数 N ≤ 5000，不应触发大数据量提示', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: EXPORT_LARGE_DATA_THRESHOLD }),
        (n: number) => {
          expect(shouldShowLargeDataWarning(n)).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Feature: admin-content-enhancement, 属性 10: 导出选项根据选中状态变化', () => {
  it('选中行数组长度 > 0 时提供两个选项', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10000 }),
        (selectedCount: number) => {
          const options = getExportOptions(selectedCount);
          expect(options).toHaveLength(2);
          expect(options).toContain('导出选中记录');
          expect(options).toContain('导出全部记录');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('选中行数组长度为 0 时仅提供"导出全部"', () => {
    const options = getExportOptions(0);
    expect(options).toHaveLength(1);
    expect(options).toContain('导出全部记录');
  });
});

describe('Feature: admin-content-enhancement, 属性 11: 导出 API 请求参数正确性', () => {
  it('对于任意模块名、格式和字段列表，API 请求参数构造正确', () => {
    fc.assert(
      fc.property(
        fc.stringMatching(/^[a-z][a-z0-9_-]*$/),
        fc.constantFrom('excel' as const, 'csv' as const),
        fc.array(fc.stringMatching(/^[a-z_]+$/), { minLength: 1, maxLength: 20 }),
        (moduleName, format, fields) => {
          const params: ExportParams = { format, fields };
          const result = buildExportApiParams(moduleName, params);

          // 验证 URL 格式
          expect(result.url).toBe(`/api/content/${moduleName}/export_data/`);
          // 验证参数包含 format 和 fields
          expect(result.params.format).toBe(format);
          expect(result.params.fields).toEqual(fields);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('指定选中 ID 时，参数应包含 ids', () => {
    fc.assert(
      fc.property(
        fc.stringMatching(/^[a-z][a-z0-9_-]*$/),
        fc.constantFrom('excel' as const, 'csv' as const),
        fc.array(fc.stringMatching(/^[a-z_]+$/), { minLength: 1, maxLength: 10 }),
        fc.array(fc.uuid(), { minLength: 1, maxLength: 50 }),
        (moduleName, format, fields, ids) => {
          const params: ExportParams = { format, fields, ids };
          const result = buildExportApiParams(moduleName, params);

          expect(result.params.ids).toEqual(ids);
        }
      ),
      { numRuns: 100 }
    );
  });
});
