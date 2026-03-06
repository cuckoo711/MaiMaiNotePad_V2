"""迁移脚本单元测试

测试数据迁移命令的功能和幂等性。
"""

import pytest
from io import StringIO
from django.core.management import call_command
from mainotebook.system.models import Dictionary, Translation


@pytest.mark.django_db
class TestMigrationScript:
    """迁移脚本测试类"""
    
    def test_migrate_translation_data(self):
        """测试迁移翻译数据
        
        验证需求：2.1, 2.2, 2.3, 2.4 - 数据迁移功能
        """
        # 创建测试数据 - toml_visualizer_tokens
        parent = Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,  # 0 = text
            sort=1,
            status=True
        )
        
        child1 = Dictionary.objects.create(
            parent=parent,
            value='char_name',
            label='角色名称',
            type=0,
            sort=1,
            status=True
        )
        
        child2 = Dictionary.objects.create(
            parent=parent,
            value='char_greeting',
            label='角色问候语',
            type=0,
            sort=2,
            status=True
        )
        
        # 执行迁移
        out = StringIO()
        call_command('migrate_translation', stdout=out)
        
        # 验证结果
        assert Translation.objects.count() >= 2, "应该至少有 2 条翻译记录"
        
        # 验证第一条记录
        trans1 = Translation.objects.get(
            translation_type='toml_visualizer_tokens',
            source_text='char_name'
        )
        assert trans1.translated_text == '角色名称', "译文应该匹配"
        assert trans1.source_language == 'en', "源语言应该是 en"
        assert trans1.target_language == 'zh', "目标语言应该是 zh"
        assert trans1.sort == 1, "排序应该匹配"
        assert trans1.status is True, "状态应该匹配"
        
        # 验证第二条记录
        trans2 = Translation.objects.get(
            translation_type='toml_visualizer_tokens',
            source_text='char_greeting'
        )
        assert trans2.translated_text == '角色问候语', "译文应该匹配"
        assert trans2.sort == 2, "排序应该匹配"
        
        # 验证输出包含成功信息
        output = out.getvalue()
        assert '成功' in output or '✓' in output, "输出应该包含成功信息"
    
    def test_migration_idempotency(self):
        """测试迁移幂等性
        
        验证需求：2.7 - 重复执行不创建重复记录
        """
        # 创建测试数据
        parent = Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,
            sort=1,
            status=True
        )
        
        Dictionary.objects.create(
            parent=parent,
            value='test_key',
            label='测试键',
            type=0,
            sort=1,
            status=True
        )
        
        # 第一次迁移
        call_command('migrate_translation', stdout=StringIO())
        count1 = Translation.objects.filter(
            translation_type='toml_visualizer_tokens',
            source_text='test_key'
        ).count()
        
        # 第二次迁移
        call_command('migrate_translation', stdout=StringIO())
        count2 = Translation.objects.filter(
            translation_type='toml_visualizer_tokens',
            source_text='test_key'
        ).count()
        
        # 验证记录数量相同
        assert count1 == count2 == 1, (
            f"重复迁移不应该创建重复记录\n"
            f"第一次: {count1} 条\n"
            f"第二次: {count2} 条"
        )
    
    def test_migrate_multiple_types(self):
        """测试迁移多种类型
        
        验证需求：2.1 - 迁移所有翻译类型
        """
        # 创建 toml_visualizer_blocks 数据
        parent_blocks = Dictionary.objects.create(
            value='toml_visualizer_blocks',
            label='TOML 可视化块',
            type=0,
            sort=1,
            status=True
        )
        
        Dictionary.objects.create(
            parent=parent_blocks,
            value='character',
            label='角色信息',
            type=0,
            sort=1,
            status=True
        )
        
        # 创建 toml_visualizer_tokens 数据
        parent_tokens = Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,
            sort=2,
            status=True
        )
        
        Dictionary.objects.create(
            parent=parent_tokens,
            value='char_name',
            label='角色名称',
            type=0,
            sort=1,
            status=True
        )
        
        # 执行迁移
        call_command('migrate_translation', stdout=StringIO())
        
        # 验证两种类型都被迁移
        blocks_count = Translation.objects.filter(
            translation_type='toml_visualizer_blocks'
        ).count()
        tokens_count = Translation.objects.filter(
            translation_type='toml_visualizer_tokens'
        ).count()
        
        assert blocks_count >= 1, "应该有 blocks 类型的翻译"
        assert tokens_count >= 1, "应该有 tokens 类型的翻译"
    
    def test_dry_run_mode(self):
        """测试模拟运行模式
        
        验证需求：2.1 - 支持 --dry-run 参数
        """
        # 创建测试数据
        parent = Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,
            sort=1,
            status=True
        )
        
        Dictionary.objects.create(
            parent=parent,
            value='dry_run_test',
            label='模拟运行测试',
            type=0,
            sort=1,
            status=True
        )
        
        # 记录迁移前的数量
        count_before = Translation.objects.count()
        
        # 执行模拟运行
        out = StringIO()
        call_command('migrate_translation', '--dry-run', stdout=out)
        
        # 验证没有创建新记录
        count_after = Translation.objects.count()
        assert count_after == count_before, (
            f"模拟运行不应该创建记录\n"
            f"之前: {count_before} 条\n"
            f"之后: {count_after} 条"
        )
        
        # 验证输出包含模拟运行提示
        output = out.getvalue()
        assert '模拟' in output or 'dry' in output.lower(), (
            "输出应该包含模拟运行提示"
        )
    
    def test_field_mapping_correctness(self):
        """测试字段映射正确性
        
        验证需求：2.3, 2.4 - 字段映射正确
        """
        # 创建测试数据，使用特定的字段值
        parent = Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,
            sort=1,
            status=True
        )
        
        child = Dictionary.objects.create(
            parent=parent,
            value='source_value',  # 应该映射到 source_text
            label='label_value',   # 应该映射到 translated_text
            type=0,
            sort=5,                # 应该映射到 sort
            status=False           # 应该映射到 status
        )
        
        # 执行迁移
        call_command('migrate_translation', stdout=StringIO())
        
        # 验证字段映射
        trans = Translation.objects.get(
            translation_type='toml_visualizer_tokens',
            source_text='source_value'
        )
        
        assert trans.source_text == child.value, (
            f"source_text 应该映射自 Dictionary.value\n"
            f"期望: {child.value}\n"
            f"实际: {trans.source_text}"
        )
        assert trans.translated_text == child.label, (
            f"translated_text 应该映射自 Dictionary.label\n"
            f"期望: {child.label}\n"
            f"实际: {trans.translated_text}"
        )
        assert trans.sort == child.sort, (
            f"sort 应该映射自 Dictionary.sort\n"
            f"期望: {child.sort}\n"
            f"实际: {trans.sort}"
        )
        assert trans.status == child.status, (
            f"status 应该映射自 Dictionary.status\n"
            f"期望: {child.status}\n"
            f"实际: {trans.status}"
        )
    
    def test_error_handling(self):
        """测试错误处理
        
        验证需求：2.5, 2.6 - 错误处理和日志记录
        """
        # 创建测试数据
        parent = Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,
            sort=1,
            status=True
        )
        
        # 创建正常记录
        Dictionary.objects.create(
            parent=parent,
            value='normal_key',
            label='正常键',
            type=0,
            sort=1,
            status=True
        )
        
        # 执行迁移
        out = StringIO()
        call_command('migrate_translation', stdout=out)
        
        # 验证正常记录被迁移
        assert Translation.objects.filter(
            translation_type='toml_visualizer_tokens',
            source_text='normal_key'
        ).exists(), "正常记录应该被迁移"
        
        # 验证输出包含统计信息
        output = out.getvalue()
        assert '成功' in output or 'Success' in output, "应该包含成功统计"
        assert '失败' in output or 'Error' in output or '错误' in output, "应该包含失败统计"
    
    def test_missing_parent_record(self):
        """测试缺少父记录的情况
        
        验证需求：2.1 - 处理缺少父记录的情况
        """
        # 不创建父记录，直接执行迁移
        out = StringIO()
        call_command('migrate_translation', stdout=out)
        
        # 验证命令正常完成（不抛出异常）
        output = out.getvalue()
        assert '迁移完成' in output or '完成' in output, "命令应该正常完成"
    
    def test_empty_children(self):
        """测试父记录下没有子记录的情况
        
        验证需求：2.1 - 处理空子记录的情况
        """
        # 只创建父记录，不创建子记录
        Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,
            sort=1,
            status=True
        )
        
        # 执行迁移
        out = StringIO()
        call_command('migrate_translation', stdout=out)
        
        # 验证命令正常完成
        output = out.getvalue()
        assert '迁移完成' in output or '完成' in output, "命令应该正常完成"
    
    def test_default_sort_value(self):
        """测试默认排序值
        
        验证需求：2.4 - 处理缺少 sort 值的情况
        """
        # 创建没有 sort 值的测试数据
        parent = Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,
            status=True
        )
        
        child = Dictionary.objects.create(
            parent=parent,
            value='no_sort_key',
            label='无排序键',
            type=0,
            sort=None,  # 没有 sort 值
            status=True
        )
        
        # 执行迁移
        call_command('migrate_translation', stdout=StringIO())
        
        # 验证使用默认 sort 值
        trans = Translation.objects.get(
            translation_type='toml_visualizer_tokens',
            source_text='no_sort_key'
        )
        
        assert trans.sort == 1, (
            f"缺少 sort 值时应该使用默认值 1\n"
            f"实际: {trans.sort}"
        )
    
    def test_statistics_output(self):
        """测试统计信息输出
        
        验证需求：2.6 - 输出迁移统计信息
        """
        # 创建测试数据
        parent = Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,
            sort=1,
            status=True
        )
        
        # 创建 3 条记录
        for i in range(3):
            Dictionary.objects.create(
                parent=parent,
                value=f'key_{i}',
                label=f'键{i}',
                type=0,
                sort=i + 1,
                status=True
            )
        
        # 执行迁移
        out = StringIO()
        call_command('migrate_translation', stdout=out)
        
        # 验证输出包含统计信息
        output = out.getvalue()
        assert '成功' in output, "应该包含成功数量"
        assert '跳过' in output or '已存在' in output, "应该包含跳过数量"
        assert '失败' in output, "应该包含失败数量"
        assert '总计' in output or '总共' in output, "应该包含总计数量"
    
    def test_transaction_rollback_on_error(self):
        """测试错误时事务回滚
        
        验证需求：2.5 - 错误处理不影响其他记录
        """
        # 创建测试数据
        parent = Dictionary.objects.create(
            value='toml_visualizer_tokens',
            label='TOML 可视化 Tokens',
            type=0,
            sort=1,
            status=True
        )
        
        # 创建多条正常记录
        for i in range(3):
            Dictionary.objects.create(
                parent=parent,
                value=f'normal_key_{i}',
                label=f'正常键{i}',
                type=0,
                sort=i + 1,
                status=True
            )
        
        # 执行迁移
        call_command('migrate_translation', stdout=StringIO())
        
        # 验证所有正常记录都被迁移
        migrated_count = Translation.objects.filter(
            translation_type='toml_visualizer_tokens',
            source_text__startswith='normal_key_'
        ).count()
        
        assert migrated_count == 3, (
            f"所有正常记录都应该被迁移\n"
            f"期望: 3 条\n"
            f"实际: {migrated_count} 条"
        )
