"""Translation 模型单元测试

测试 Translation 模型的基本功能和约束。
"""

import pytest
from django.db import IntegrityError
from mainotebook.system.models import Translation


@pytest.mark.django_db
class TestTranslationModel:
    """Translation 模型测试类"""
    
    def test_create_translation(self):
        """测试创建翻译记录
        
        验证需求：1.1 - Translation 模型包含所有必需字段
        """
        translation = Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type',
            source_language='en',
            target_language='zh',
            sort=1,
            status=True
        )
        
        assert translation.id is not None, "翻译记录应该有 ID"
        assert translation.source_text == 'test', "原文应该匹配"
        assert translation.translated_text == '测试', "译文应该匹配"
        assert translation.translation_type == 'test_type', "翻译类型应该匹配"
        assert translation.source_language == 'en', "源语言应该匹配"
        assert translation.target_language == 'zh', "目标语言应该匹配"
        assert translation.sort == 1, "排序应该匹配"
        assert translation.status is True, "状态应该匹配"
    
    def test_unique_constraint(self):
        """测试唯一性约束
        
        验证需求：1.3 - translation_type 和 source_text 的唯一约束
        """
        # 创建第一条记录
        Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type',
            source_language='en',
            target_language='zh'
        )
        
        # 尝试创建重复记录应该失败
        with pytest.raises(IntegrityError):
            Translation.objects.create(
                source_text='test',
                translated_text='测试2',
                translation_type='test_type',
                source_language='en',
                target_language='zh'
            )
    
    def test_str_representation(self):
        """测试字符串表示
        
        验证需求：1.5 - __str__ 方法返回正确格式
        """
        translation = Translation(
            source_text='hello',
            translated_text='你好',
            translation_type='greeting',
            source_language='en',
            target_language='zh'
        )
        
        expected = 'greeting: hello -> 你好'
        actual = str(translation)
        
        assert actual == expected, (
            f"字符串表示格式不正确\n"
            f"期望: {expected}\n"
            f"实际: {actual}"
        )
    
    def test_default_values(self):
        """测试默认值
        
        验证需求：1.2 - 字段默认值正确
        """
        translation = Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type'
        )
        
        assert translation.source_language == 'en', "默认源语言应该是 en"
        assert translation.target_language == 'zh', "默认目标语言应该是 zh"
        assert translation.sort == 1, "默认排序应该是 1"
        assert translation.status is True, "默认状态应该是 True"
    
    def test_ordering(self):
        """测试排序
        
        验证需求：1.4 - 默认按 sort 字段排序
        """
        # 创建多个翻译，使用不同的 sort 值
        Translation.objects.create(
            source_text='third',
            translated_text='第三',
            translation_type='test_type',
            sort=3
        )
        Translation.objects.create(
            source_text='first',
            translated_text='第一',
            translation_type='test_type',
            sort=1
        )
        Translation.objects.create(
            source_text='second',
            translated_text='第二',
            translation_type='test_type',
            sort=2
        )
        
        # 查询所有记录
        translations = list(Translation.objects.filter(
            translation_type='test_type'
        ))
        
        # 验证按 sort 升序排列
        assert len(translations) == 3, "应该有 3 条记录"
        assert translations[0].source_text == 'first', "第一条应该是 sort=1"
        assert translations[1].source_text == 'second', "第二条应该是 sort=2"
        assert translations[2].source_text == 'third', "第三条应该是 sort=3"
    
    def test_update_translation(self):
        """测试更新翻译记录
        
        验证需求：1.1 - 翻译记录可以更新
        """
        translation = Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type'
        )
        
        # 更新译文
        translation.translated_text = '测试更新'
        translation.save()
        
        # 重新查询验证
        updated = Translation.objects.get(id=translation.id)
        assert updated.translated_text == '测试更新', "译文应该已更新"
    
    def test_delete_translation(self):
        """测试删除翻译记录
        
        验证需求：1.1 - 翻译记录可以删除
        """
        translation = Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type'
        )
        
        translation_id = translation.id
        translation.delete()
        
        # 验证记录已删除
        assert not Translation.objects.filter(id=translation_id).exists(), (
            "翻译记录应该已删除"
        )
    
    def test_filter_by_translation_type(self):
        """测试按翻译类型过滤
        
        验证需求：1.4 - 支持按 translation_type 过滤
        """
        Translation.objects.create(
            source_text='block1',
            translated_text='块1',
            translation_type='toml_visualizer_blocks',
            sort=1
        )
        Translation.objects.create(
            source_text='token1',
            translated_text='令牌1',
            translation_type='toml_visualizer_tokens',
            sort=1
        )
        
        # 按类型过滤
        blocks = Translation.objects.filter(
            translation_type='toml_visualizer_blocks'
        )
        tokens = Translation.objects.filter(
            translation_type='toml_visualizer_tokens'
        )
        
        assert blocks.count() == 1, "应该有 1 个块翻译"
        assert tokens.count() == 1, "应该有 1 个令牌翻译"
        assert blocks.first().source_text == 'block1', "块翻译内容应该匹配"
        assert tokens.first().source_text == 'token1', "令牌翻译内容应该匹配"
    
    def test_filter_by_status(self):
        """测试按状态过滤
        
        验证需求：1.2 - 支持按 status 过滤
        """
        Translation.objects.create(
            source_text='enabled',
            translated_text='启用',
            translation_type='test_type',
            status=True,
            sort=1
        )
        Translation.objects.create(
            source_text='disabled',
            translated_text='禁用',
            translation_type='test_type',
            status=False,
            sort=2
        )
        
        # 只查询启用的翻译
        enabled = Translation.objects.filter(
            translation_type='test_type',
            status=True
        )
        
        assert enabled.count() == 1, "应该只有 1 条启用的翻译"
        assert enabled.first().source_text == 'enabled', "应该是启用的翻译"
    
    def test_max_length_constraints(self):
        """测试字段长度约束
        
        验证需求：5.2, 5.3, 5.4 - 字段长度限制
        """
        # 测试正常长度
        translation = Translation.objects.create(
            source_text='a' * 200,  # 最大长度
            translated_text='b' * 200,  # 最大长度
            translation_type='c' * 50,  # 最大长度
            source_language='d' * 10,  # 最大长度
            target_language='e' * 10  # 最大长度
        )
        
        assert translation.id is not None, "应该能创建最大长度的记录"
        
        # 注意：超长字段会被数据库截断或抛出错误，具体行为取决于数据库配置
        # 这里主要测试正常长度可以正常工作
    
    def test_inherits_from_core_model(self):
        """测试继承 CoreModel
        
        验证需求：1.2 - 继承 CoreModel 基类
        """
        translation = Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type'
        )
        
        # 验证 CoreModel 提供的字段存在
        assert hasattr(translation, 'create_datetime'), "应该有 create_datetime 字段"
        assert hasattr(translation, 'update_datetime'), "应该有 update_datetime 字段"
        assert translation.create_datetime is not None, "create_datetime 应该有值"
        assert translation.update_datetime is not None, "update_datetime 应该有值"
