/**
 * 高级搜索属性测试
 *
 * 使用 fast-check 验证搜索参数构造的正确性属性
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  buildSearchParams,
  buildFuzzySearchParam,
  resolveDateRange,
} from '../searchUtils';

describe('Feature: admin-content-enhancement, 属性 12: 搜索条件 AND 组合', () => {
  /**
   * Validates: Requirements 7.6
   */
  it('对于任意多个非空搜索条件，所有条件都应出现在查询参数中', () => {
    fc.assert(
      fc.property(
        fc.dictionary(
          // 排除 JavaScript 原型链特殊属性名，这些不是有效的搜索参数键
          fc.stringMatching(/^[a-z_]{1,20}$/).filter((s) => s !== '__proto__' && s !== 'constructor' && s !== 'prototype'),
          fc.string({ minLength: 1, maxLength: 50 }),
          { minKeys: 1, maxKeys: 10 }
        ),
        (conditions: Record<string, string>) => {
          const params = buildSearchParams(conditions);
          // 所有非空条件都应出现在结果中
          for (const [key, value] of Object.entries(conditions)) {
            if (value !== '') {
              expect(params).toHaveProperty(key, value);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('空值条件应被过滤掉', () => {
    fc.assert(
      fc.property(
        fc.stringMatching(/^[a-z_]{1,20}$/),
        fc.constantFrom(undefined, null, ''),
        (key: string, emptyValue: any) => {
          const params = buildSearchParams({ [key]: emptyValue });
          expect(Object.keys(params)).not.toContain(key);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('混合非空和空值条件时，仅保留非空条件', () => {
    fc.assert(
      fc.property(
        fc.record({
          name: fc.string({ minLength: 1 }),
          empty_field: fc.constant(''),
          null_field: fc.constant(null),
          status: fc.string({ minLength: 1 }),
        }),
        (conditions) => {
          const params = buildSearchParams(conditions as any);
          expect(params).toHaveProperty('name');
          expect(params).toHaveProperty('status');
          expect(params).not.toHaveProperty('empty_field');
          expect(params).not.toHaveProperty('null_field');
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Feature: admin-content-enhancement, 属性 13: 模糊搜索参数传递', () => {
  /**
   * Validates: Requirements 8.1, 8.2, 8.3, 8.4
   */
  it('对于任意非空关键词，search 参数应包含该关键词', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }).filter((s) => s.trim().length > 0),
        (keyword: string) => {
          const params = buildFuzzySearchParam(keyword);
          expect(params).toHaveProperty('search');
          expect(params.search).toBe(keyword.trim());
        }
      ),
      { numRuns: 100 }
    );
  });

  it('对于空关键词，search 参数不应出现', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(' ', '\t', '\n', '\r'), { maxLength: 20 }),
        (chars: string[]) => {
          const blankStr = chars.join('');
          const params = buildFuzzySearchParam(blankStr);
          expect(params).not.toHaveProperty('search');
          expect(Object.keys(params).length).toBe(0);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('空字符串不应产生 search 参数', () => {
    const params = buildFuzzySearchParam('');
    expect(params).not.toHaveProperty('search');
  });
});

describe('Feature: admin-content-enhancement, 属性 14: 日期范围参数转换', () => {
  /**
   * Validates: Requirements 6.2
   */
  it('对于任意有效日期范围，应正确转换为 after/before 参数', () => {
    // 使用整数时间戳生成有效日期，避免 NaN 日期问题
    const validDateArb = fc
      .integer({
        min: new Date('2020-01-01').getTime(),
        max: new Date('2030-12-31').getTime(),
      })
      .map((ts) => new Date(ts));

    fc.assert(
      fc.property(
        fc.tuple(validDateArb, validDateArb),
        ([startDate, endDate]) => {
          const startStr = startDate.toISOString().slice(0, 19).replace('T', ' ');
          const endStr = endDate.toISOString().slice(0, 19).replace('T', ' ');
          const result = resolveDateRange([startStr, endStr]);
          expect(result).toHaveProperty('create_datetime_after', startStr);
          expect(result).toHaveProperty('create_datetime_before', endStr);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('null 日期范围应返回空对象', () => {
    const result = resolveDateRange(null);
    expect(Object.keys(result).length).toBe(0);
  });

  it('undefined 日期范围应返回空对象', () => {
    const result = resolveDateRange(undefined);
    expect(Object.keys(result).length).toBe(0);
  });
});
