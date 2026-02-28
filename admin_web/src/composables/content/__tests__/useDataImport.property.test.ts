/**
 * 数据导入 composable 属性测试
 *
 * 使用 fast-check 验证数据导入相关的正确性属性
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  validateFileFormat,
  parseImportResult,
  type ImportResult,
} from '../dataImportUtils';

describe('Feature: admin-content-enhancement, 属性 7: 导入文件格式验证', () => {
  it('对于 .xlsx 扩展名（不区分大小写），验证应通过', () => {
    fc.assert(
      fc.property(
        fc.stringMatching(/^[a-zA-Z0-9_-]+$/),
        fc.constantFrom('.xlsx', '.XLSX', '.Xlsx', '.xLsX'),
        (baseName, ext) => {
          expect(validateFileFormat(baseName + ext)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('对于 .csv 扩展名（不区分大小写），验证应通过', () => {
    fc.assert(
      fc.property(
        fc.stringMatching(/^[a-zA-Z0-9_-]+$/),
        fc.constantFrom('.csv', '.CSV', '.Csv', '.cSv'),
        (baseName, ext) => {
          expect(validateFileFormat(baseName + ext)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('对于其他扩展名，验证应拒绝', () => {
    fc.assert(
      fc.property(
        fc.stringMatching(/^[a-zA-Z0-9_-]+$/),
        fc.constantFrom('.txt', '.pdf', '.doc', '.xls', '.json', '.xml', '.zip', '.png'),
        (baseName, ext) => {
          expect(validateFileFormat(baseName + ext)).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('无扩展名的文件名应被拒绝', () => {
    fc.assert(
      fc.property(
        fc.stringMatching(/^[a-zA-Z0-9_-]+$/).filter((s) => !s.includes('.')),
        (fileName) => {
          expect(validateFileFormat(fileName)).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Feature: admin-content-enhancement, 属性 8: 导入结果解析正确性', () => {
  it('对于任意 ImportResultResponse，解析应正确提取所有字段', () => {
    fc.assert(
      fc.property(
        fc.nat({ max: 1000 }),
        fc.nat({ max: 1000 }),
        fc.array(
          fc.record({
            row: fc.integer({ min: 1, max: 10000 }),
            message: fc.string({ minLength: 1 }),
          }),
          { maxLength: 50 }
        ),
        (successCount, failCount, errors) => {
          const response: ImportResult = {
            success_count: successCount,
            fail_count: failCount,
            errors,
          };
          const parsed = parseImportResult(response);

          expect(parsed.success_count).toBe(successCount);
          expect(parsed.fail_count).toBe(failCount);
          expect(parsed.errors).toEqual(errors);
          // 每个错误项包含 row 和 message
          parsed.errors!.forEach((err) => {
            expect(err).toHaveProperty('row');
            expect(err).toHaveProperty('message');
            expect(typeof err.row).toBe('number');
            expect(typeof err.message).toBe('string');
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  it('无 errors 字段时解析为空数组', () => {
    fc.assert(
      fc.property(
        fc.nat({ max: 1000 }),
        fc.nat({ max: 1000 }),
        (successCount, failCount) => {
          const response: ImportResult = {
            success_count: successCount,
            fail_count: failCount,
          };
          const parsed = parseImportResult(response);
          expect(parsed.errors).toEqual([]);
        }
      ),
      { numRuns: 100 }
    );
  });
});
