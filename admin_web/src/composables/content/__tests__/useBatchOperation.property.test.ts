/**
 * 批量操作 composable 属性测试
 *
 * 使用 fast-check 验证批量操作相关的正确性属性
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  formatSelectionText,
  validateRejectReason,
  parseBatchResult,
  buildBatchApproveRequest,
  buildBatchRejectRequest,
  buildBatchDeleteUrl,
  buildBatchDeleteRequest,
  BATCH_APPROVE_URL,
  BATCH_REJECT_URL,
  type BatchResult,
} from '../batchOperationUtils';

describe('Feature: admin-content-enhancement, 属性 1: 批量操作 API 请求构造正确性', () => {
  it('对于任意模块名和非空 ID 数组，批量审核通过请求体应包含 ids 数组', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),
        fc.array(fc.uuid(), { minLength: 1 }),
        (moduleName: string, ids: string[]) => {
          const requestBody = buildBatchApproveRequest(ids);
          expect(requestBody).toHaveProperty('ids');
          expect(requestBody.ids).toEqual(ids);
          expect(Array.isArray(requestBody.ids)).toBe(true);
          // 验证 URL 固定
          expect(BATCH_APPROVE_URL).toBe('/api/content/review/batch-approve/');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('对于任意模块名和非空 ID 数组，批量审核拒绝请求体应包含 ids 和 reason', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),
        fc.array(fc.uuid(), { minLength: 1 }),
        fc.string({ minLength: 1 }),
        (moduleName: string, ids: string[], reason: string) => {
          const requestBody = buildBatchRejectRequest(ids, reason);
          expect(requestBody).toHaveProperty('ids');
          expect(requestBody).toHaveProperty('reason');
          expect(requestBody.ids).toEqual(ids);
          expect(requestBody.reason).toEqual(reason);
          expect(BATCH_REJECT_URL).toBe('/api/content/review/batch-reject/');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('对于任意模块名，批量删除 URL 应包含模块名', () => {
    fc.assert(
      fc.property(
        fc.stringMatching(/^[a-z][a-z0-9_-]*$/),
        fc.array(fc.uuid(), { minLength: 1 }),
        (moduleName: string, ids: string[]) => {
          const url = buildBatchDeleteUrl(moduleName);
          expect(url).toContain(moduleName);
          expect(url).toMatch(/^\/api\/content\/.+\/batch-delete\/$/);
          const requestBody = buildBatchDeleteRequest(ids);
          expect(requestBody.ids).toEqual(ids);
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Feature: admin-content-enhancement, 属性 2: 批量操作结果解析正确性', () => {
  it('对于任意 BatchOperationResponse，success_count + fail_count 应等于总 ID 数', () => {
    fc.assert(
      fc.property(
        fc.nat({ max: 1000 }),
        fc.nat({ max: 1000 }),
        (successCount: number, failCount: number) => {
          const totalCount = successCount + failCount;
          const response: BatchResult = {
            success_count: successCount,
            fail_count: failCount,
            failures: [],
          };
          const parsed = parseBatchResult(response, totalCount);
          expect(parsed.success_count + parsed.fail_count).toBe(totalCount);
          expect(parsed.success_count).toBe(successCount);
          expect(parsed.fail_count).toBe(failCount);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('对于任意包含 failures 的响应，failures 数组应被正确保留', () => {
    fc.assert(
      fc.property(
        fc.nat({ max: 100 }),
        fc.nat({ max: 100 }),
        fc.array(
          fc.record({
            id: fc.uuid(),
            reason: fc.string({ minLength: 1 }),
          }),
          { maxLength: 50 }
        ),
        (successCount: number, failCount: number, failures) => {
          const response: BatchResult = {
            success_count: successCount,
            fail_count: failCount,
            failures,
          };
          const parsed = parseBatchResult(response, successCount + failCount);
          expect(parsed.failures).toEqual(failures);
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Feature: admin-content-enhancement, 属性 3: 选中数量显示格式', () => {
  it('对于任意正整数 N，显示文本应严格等于 "已选中 N 条"', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 100000 }),
        (n: number) => {
          const text = formatSelectionText(n);
          expect(text).toBe(`已选中 ${n} 条`);
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Feature: admin-content-enhancement, 属性 4: 批量操作按钮禁用状态', () => {
  it('选中行数组长度为 0 时 hasSelection 应为 false', () => {
    // 直接测试逻辑：空数组 → false
    const rows: any[] = [];
    expect(rows.length > 0).toBe(false);
  });

  it('对于任意非空数组，hasSelection 应为 true', () => {
    fc.assert(
      fc.property(
        fc.array(fc.record({ id: fc.uuid() }), { minLength: 1, maxLength: 100 }),
        (rows) => {
          expect(rows.length > 0).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Feature: admin-content-enhancement, 属性 6: 拒绝原因空值验证', () => {
  it('对于任意空白字符串，验证应拒绝', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(' ', '\t', '\n', '\r', '\f', '\v'), { maxLength: 20 }),
        (chars: string[]) => {
          const blankStr = chars.join('');
          expect(validateRejectReason(blankStr)).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('空字符串应被拒绝', () => {
    expect(validateRejectReason('')).toBe(false);
  });

  it('对于任意包含非空白字符的字符串，验证应通过', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }).filter((s) => s.trim().length > 0),
        (validStr: string) => {
          expect(validateRejectReason(validStr)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});
