"""TranslationSerializer 单元测试

测试翻译序列化器的验证逻辑和数据转换。
"""

import pytest
from mainotebook.system.models import Translation
from mainotebook.system.views.translation import TranslationSerializer


@pytest.mark.django_db
class TestTranslationSerializer:
    """TranslationSerializer 测试类"""
    
    def test_valid_data(self):
        """测试有效数据验证
        
        验证需求：5.2, 5.3, 5.4 - 有效数据应该通过验证
        """
        data = {
            'source_text': 'test',
            'translated_text': '测试',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh',
            'sort': 1,
            'status': True
        }
        
        serializer = TranslationSerializer(data=data)
        assert serializer.is_valid(), (
            f"有效数据应该通过验证\n"
            f"错误: {serializer.errors}"
        )
        
        # 保存并验证
        translation = serializer.save()
        assert translation.source_text == 'test', "原文应该匹配"
        assert translation.translated_text == '测试', "译文应该匹配"
    
    def test_empty_source_text(self):
        """测试空原文验证
        
        验证需求：5.2 - 原文不能为空
        """
        data = {
            'source_text': '',
            'translated_text': '测试',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "空原文应该验证失败"
        assert 'source_text' in serializer.errors or '原文' in str(serializer.errors), (
            f"应该包含 source_text 错误\n"
            f"实际错误: {serializer.errors}"
        )
    
    def test_whitespace_only_source_text(self):
        """测试只包含空白字符的原文
        
        验证需求：5.2 - 原文不能为空（包括只有空白字符）
        """
        data = {
            'source_text': '   ',
            'translated_text': '测试',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "只包含空白字符的原文应该验证失败"
    
    def test_empty_translated_text(self):
        """测试空译文验证
        
        验证需求：5.3 - 译文不能为空
        """
        data = {
            'source_text': 'test',
            'translated_text': '',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "空译文应该验证失败"
        assert 'translated_text' in serializer.errors or '译文' in str(serializer.errors), (
            f"应该包含 translated_text 错误\n"
            f"实际错误: {serializer.errors}"
        )
    
    def test_whitespace_only_translated_text(self):
        """测试只包含空白字符的译文
        
        验证需求：5.3 - 译文不能为空（包括只有空白字符）
        """
        data = {
            'source_text': 'test',
            'translated_text': '   ',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "只包含空白字符的译文应该验证失败"
    
    def test_empty_translation_type(self):
        """测试空翻译类型验证
        
        验证需求：5.4 - 翻译类型不能为空
        """
        data = {
            'source_text': 'test',
            'translated_text': '测试',
            'translation_type': '',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "空翻译类型应该验证失败"
        assert 'translation_type' in serializer.errors or '翻译类型' in str(serializer.errors), (
            f"应该包含 translation_type 错误\n"
            f"实际错误: {serializer.errors}"
        )
    
    def test_source_text_too_long(self):
        """测试原文过长验证
        
        验证需求：5.2 - 原文长度不能超过 200 个字符
        """
        data = {
            'source_text': 'a' * 201,
            'translated_text': '测试',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "超长原文应该验证失败"
        assert 'source_text' in serializer.errors or '原文' in str(serializer.errors), (
            f"应该包含 source_text 错误\n"
            f"实际错误: {serializer.errors}"
        )
    
    def test_translated_text_too_long(self):
        """测试译文过长验证
        
        验证需求：5.3 - 译文长度不能超过 200 个字符
        """
        data = {
            'source_text': 'test',
            'translated_text': '测' * 201,
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "超长译文应该验证失败"
        assert 'translated_text' in serializer.errors or '译文' in str(serializer.errors), (
            f"应该包含 translated_text 错误\n"
            f"实际错误: {serializer.errors}"
        )
    
    def test_translation_type_too_long(self):
        """测试翻译类型过长验证
        
        验证需求：5.4 - 翻译类型长度不能超过 50 个字符
        """
        data = {
            'source_text': 'test',
            'translated_text': '测试',
            'translation_type': 'a' * 51,
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "超长翻译类型应该验证失败"
        assert 'translation_type' in serializer.errors or '翻译类型' in str(serializer.errors), (
            f"应该包含 translation_type 错误\n"
            f"实际错误: {serializer.errors}"
        )
    
    def test_duplicate_validation(self):
        """测试重复验证
        
        验证需求：5.6, 5.7 - 检查唯一性约束
        """
        # 创建第一条记录
        Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type',
            source_language='en',
            target_language='zh'
        )
        
        # 尝试创建重复记录
        data = {
            'source_text': 'test',
            'translated_text': '测试2',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "重复的翻译应该验证失败"
        
        # 检查错误消息（可能在 non_field_errors 或自定义验证错误中）
        error_message = str(serializer.errors)
        assert ('已存在' in error_message or 
                'duplicate' in error_message.lower() or
                '唯一' in error_message or
                'unique' in error_message.lower()), (
            f"错误消息应该提示重复或唯一性约束\n"
            f"实际错误: {serializer.errors}"
        )
    
    def test_update_without_duplicate_error(self):
        """测试更新时不触发重复验证
        
        验证需求：5.6 - 更新时排除当前实例
        """
        # 创建记录
        translation = Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type',
            source_language='en',
            target_language='zh'
        )
        
        # 更新译文（不改变 source_text 和 translation_type）
        data = {
            'source_text': 'test',
            'translated_text': '测试更新',
            'translation_type': 'test_type',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(translation, data=data)
        assert serializer.is_valid(), (
            f"更新自己不应该触发重复验证\n"
            f"错误: {serializer.errors}"
        )
    
    def test_trim_whitespace(self):
        """测试去除首尾空白字符
        
        验证需求：5.2, 5.3, 5.4 - 字段应该去除首尾空白
        """
        data = {
            'source_text': '  test  ',
            'translated_text': '  测试  ',
            'translation_type': '  test_type  ',
            'source_language': 'en',
            'target_language': 'zh'
        }
        
        serializer = TranslationSerializer(data=data)
        assert serializer.is_valid(), (
            f"带空白字符的数据应该通过验证\n"
            f"错误: {serializer.errors}"
        )
        
        translation = serializer.save()
        assert translation.source_text == 'test', "原文应该去除首尾空白"
        assert translation.translated_text == '测试', "译文应该去除首尾空白"
        assert translation.translation_type == 'test_type', "翻译类型应该去除首尾空白"
    
    def test_serialization(self):
        """测试序列化输出
        
        验证需求：4.8 - 序列化输出包含所有字段
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
        
        serializer = TranslationSerializer(translation)
        data = serializer.data
        
        # 验证所有字段都存在
        assert 'id' in data, "应该包含 id 字段"
        assert 'source_text' in data, "应该包含 source_text 字段"
        assert 'translated_text' in data, "应该包含 translated_text 字段"
        assert 'translation_type' in data, "应该包含 translation_type 字段"
        assert 'source_language' in data, "应该包含 source_language 字段"
        assert 'target_language' in data, "应该包含 target_language 字段"
        assert 'sort' in data, "应该包含 sort 字段"
        assert 'status' in data, "应该包含 status 字段"
        assert 'create_datetime' in data, "应该包含 create_datetime 字段"
        assert 'update_datetime' in data, "应该包含 update_datetime 字段"
        
        # 验证字段值
        assert data['source_text'] == 'test', "原文应该匹配"
        assert data['translated_text'] == '测试', "译文应该匹配"
        assert data['translation_type'] == 'test_type', "翻译类型应该匹配"
    
    def test_partial_update(self):
        """测试部分更新
        
        验证需求：6.2 - 支持部分更新
        """
        translation = Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type',
            source_language='en',
            target_language='zh'
        )
        
        # 只更新译文
        data = {
            'translated_text': '测试更新'
        }
        
        serializer = TranslationSerializer(translation, data=data, partial=True)
        assert serializer.is_valid(), (
            f"部分更新应该通过验证\n"
            f"错误: {serializer.errors}"
        )
        
        updated = serializer.save()
        assert updated.translated_text == '测试更新', "译文应该已更新"
        assert updated.source_text == 'test', "原文应该保持不变"
    
    def test_read_only_fields(self):
        """测试只读字段
        
        验证需求：5.1 - id, create_datetime, update_datetime 是只读的
        """
        translation = Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type'
        )
        
        original_id = translation.id
        original_create_time = translation.create_datetime
        
        # 尝试修改只读字段
        data = {
            'id': 'new_id',
            'source_text': 'test',
            'translated_text': '测试更新',
            'translation_type': 'test_type',
            'create_datetime': '2020-01-01T00:00:00Z'
        }
        
        serializer = TranslationSerializer(translation, data=data)
        if serializer.is_valid():
            updated = serializer.save()
            
            # 验证只读字段没有被修改
            assert updated.id == original_id, "ID 不应该被修改"
            assert updated.create_datetime == original_create_time, (
                "创建时间不应该被修改"
            )
    
    def test_missing_required_fields(self):
        """测试缺少必填字段
        
        验证需求：5.2, 5.3, 5.4 - 必填字段验证
        """
        # 缺少 source_text
        data = {
            'translated_text': '测试',
            'translation_type': 'test_type'
        }
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "缺少 source_text 应该验证失败"
        
        # 缺少 translated_text
        data = {
            'source_text': 'test',
            'translation_type': 'test_type'
        }
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "缺少 translated_text 应该验证失败"
        
        # 缺少 translation_type
        data = {
            'source_text': 'test',
            'translated_text': '测试'
        }
        serializer = TranslationSerializer(data=data)
        assert not serializer.is_valid(), "缺少 translation_type 应该验证失败"
    
    def test_default_values_in_serialization(self):
        """测试序列化时的默认值
        
        验证需求：1.2 - 默认值正确
        """
        translation = Translation.objects.create(
            source_text='test',
            translated_text='测试',
            translation_type='test_type'
        )
        
        serializer = TranslationSerializer(translation)
        data = serializer.data
        
        assert data['source_language'] == 'en', "默认源语言应该是 en"
        assert data['target_language'] == 'zh', "默认目标语言应该是 zh"
        assert data['sort'] == 1, "默认排序应该是 1"
        assert data['status'] is True, "默认状态应该是 True"
