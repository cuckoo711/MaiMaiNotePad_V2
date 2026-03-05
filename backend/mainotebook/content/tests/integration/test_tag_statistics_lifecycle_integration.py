# -*- coding: utf-8 -*-

"""
标签统计生命周期集成测试

测试完整的内容生命周期流程中标签统计的同步更新。
验证多个操作组合后标签统计的最终一致性。

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 3.2**
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from mainotebook.system.models import Users
from mainotebook.content.models import PersonaCard, KnowledgeBase, TagStatistics
from mainotebook.content.services.tag_service import TagService


@pytest.mark.django_db
class TestCompleteContentLifecycle(TestCase):
    """测试完整的内容生命周期流程
    
    测试场景：
    - 创建公开内容 → 验证标签统计增加
    - 更新标签列表 → 验证新增和删除标签的统计正确更新
    - 公开转私有 → 验证标签统计减少
    - 私有转公开 → 验证标签统计增加
    - 删除内容 → 验证标签统计减少
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.user = Users.objects.create_user(
            username='lifecycle_user',
            password='test_password',
            name='生命周期测试用户'
        )
        
        # 创建 API 客户端
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # 清空标签统计表
        TagStatistics.objects.all().delete()
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        TagStatistics.objects.all().delete()
        Users.objects.all().delete()
    
    def test_persona_card_complete_lifecycle(self):
        """测试 PersonaCard 完整生命周期
        
        流程：
        1. 创建公开内容 → 标签统计增加
        2. 更新标签列表 → 新增和删除标签的统计正确更新
        3. 公开转私有 → 标签统计减少
        4. 私有转公开 → 标签统计增加
        5. 删除内容 → 标签统计减少
        """
        # 步骤 1: 创建公开的 PersonaCard
        persona_card = PersonaCard.objects.create(
            name='生命周期测试人设卡',
            description='测试描述',
            uploader=self.user,
            tags=['AI', '助手', '聊天'],
            is_public=True,
            is_pending=False
        )
        
        # 手动触发标签统计更新（模拟创建时的行为）
        TagService.update_tag_usage(['AI', '助手', '聊天'], tag_type='persona')
        
        # 验证标签统计已创建
        ai_tag = TagStatistics.objects.get(tag='AI', tag_type='persona')
        helper_tag = TagStatistics.objects.get(tag='助手', tag_type='persona')
        chat_tag = TagStatistics.objects.get(tag='聊天', tag_type='persona')
        
        self.assertEqual(ai_tag.usage_count, 1)
        self.assertEqual(helper_tag.usage_count, 1)
        self.assertEqual(chat_tag.usage_count, 1)
        
        # 步骤 2: 更新标签列表（删除 '助手'，添加 '游戏'，保留 'AI' 和 '聊天'）
        url = f'/api/content/persona/{persona_card.id}/'
        data = {
            'name': '生命周期测试人设卡',
            'description': '测试描述',
            'is_public': True,
            'tags': ['AI', '聊天', '游戏']
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计更新
        ai_tag.refresh_from_db()
        chat_tag.refresh_from_db()
        self.assertEqual(ai_tag.usage_count, 1)  # 保持不变
        self.assertEqual(chat_tag.usage_count, 1)  # 保持不变
        
        # '助手' 标签应该被删除（usage_count 降为 0）
        self.assertFalse(
            TagStatistics.objects.filter(tag='助手', tag_type='persona').exists()
        )
        
        # '游戏' 标签应该被创建
        game_tag = TagStatistics.objects.get(tag='游戏', tag_type='persona')
        self.assertEqual(game_tag.usage_count, 1)
        
        # 步骤 3: 公开转私有
        toggle_url = f'/api/content/persona/{persona_card.id}/toggle-public/'
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计减少并删除记录（usage_count 降为 0）
        self.assertFalse(
            TagStatistics.objects.filter(tag='AI', tag_type='persona').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='聊天', tag_type='persona').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='游戏', tag_type='persona').exists()
        )
        
        # 步骤 4: 私有转公开
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计增加
        ai_tag = TagStatistics.objects.get(tag='AI', tag_type='persona')
        chat_tag = TagStatistics.objects.get(tag='聊天', tag_type='persona')
        game_tag = TagStatistics.objects.get(tag='游戏', tag_type='persona')
        
        self.assertEqual(ai_tag.usage_count, 1)
        self.assertEqual(chat_tag.usage_count, 1)
        self.assertEqual(game_tag.usage_count, 1)
        
        # 步骤 5: 删除内容
        delete_url = f'/api/content/persona/{persona_card.id}/'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计减少并删除记录
        self.assertFalse(
            TagStatistics.objects.filter(tag='AI', tag_type='persona').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='聊天', tag_type='persona').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='游戏', tag_type='persona').exists()
        )
    
    def test_knowledge_base_complete_lifecycle(self):
        """测试 KnowledgeBase 完整生命周期
        
        流程：
        1. 创建公开内容 → 标签统计增加
        2. 更新标签列表 → 新增和删除标签的统计正确更新
        3. 删除内容 → 标签统计减少
        """
        # 步骤 1: 创建公开的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='生命周期测试知识库',
            description='测试描述',
            uploader=self.user,
            tags=['Python', 'Django', 'Web'],
            is_public=True,
            is_pending=False
        )
        
        # 手动触发标签统计更新
        TagService.update_tag_usage(['Python', 'Django', 'Web'], tag_type='knowledge')
        
        # 验证标签统计已创建
        python_tag = TagStatistics.objects.get(tag='Python', tag_type='knowledge')
        django_tag = TagStatistics.objects.get(tag='Django', tag_type='knowledge')
        web_tag = TagStatistics.objects.get(tag='Web', tag_type='knowledge')
        
        self.assertEqual(python_tag.usage_count, 1)
        self.assertEqual(django_tag.usage_count, 1)
        self.assertEqual(web_tag.usage_count, 1)
        
        # 步骤 2: 更新标签列表（删除 'Django'，添加 'FastAPI'，保留 'Python' 和 'Web'）
        url = f'/api/content/knowledge/{kb.id}/'
        data = {
            'name': '生命周期测试知识库',
            'description': '测试描述',
            'tags': ['Python', 'Web', 'FastAPI']
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证标签统计更新
        python_tag.refresh_from_db()
        web_tag.refresh_from_db()
        self.assertEqual(python_tag.usage_count, 1)  # 保持不变
        self.assertEqual(web_tag.usage_count, 1)  # 保持不变
        
        # 'Django' 标签应该被删除
        self.assertFalse(
            TagStatistics.objects.filter(tag='Django', tag_type='knowledge').exists()
        )
        
        # 'FastAPI' 标签应该被创建
        fastapi_tag = TagStatistics.objects.get(tag='FastAPI', tag_type='knowledge')
        self.assertEqual(fastapi_tag.usage_count, 1)
        
        # 步骤 3: 删除内容
        delete_url = f'/api/content/knowledge/{kb.id}/'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 验证标签统计减少并删除记录
        self.assertFalse(
            TagStatistics.objects.filter(tag='Python', tag_type='knowledge').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='Web', tag_type='knowledge').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='FastAPI', tag_type='knowledge').exists()
        )


@pytest.mark.django_db
class TestMultipleContentsSharedTags(TestCase):
    """测试多个内容共享同一标签的场景
    
    测试场景：
    - 创建多个使用相同标签的内容
    - 删除其中一个内容，验证标签统计正确减少但不为 0
    - 删除所有内容，验证标签统计降为 0 并删除记录
    
    **Validates: Requirements 2.1, 2.5**
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create_user(
            username='shared_tags_user',
            password='test_password',
            name='共享标签测试用户'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        TagStatistics.objects.all().delete()
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        TagStatistics.objects.all().delete()
        Users.objects.all().delete()
    
    def test_multiple_persona_cards_share_same_tag(self):
        """测试多个 PersonaCard 共享同一标签
        
        验证：
        1. 创建 3 个使用 'AI' 标签的 PersonaCard
        2. 删除其中 1 个，usage_count 减 1
        3. 删除第 2 个，usage_count 再减 1
        4. 删除第 3 个，usage_count 降为 0，记录被删除
        """
        # 创建 3 个公开的 PersonaCard，都使用 'AI' 标签
        pc1 = PersonaCard.objects.create(
            name='AI助手1',
            description='描述1',
            uploader=self.user,
            tags=['AI', '助手'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['AI', '助手'], tag_type='persona')
        
        pc2 = PersonaCard.objects.create(
            name='AI助手2',
            description='描述2',
            uploader=self.user,
            tags=['AI', '聊天'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['AI', '聊天'], tag_type='persona')
        
        pc3 = PersonaCard.objects.create(
            name='AI助手3',
            description='描述3',
            uploader=self.user,
            tags=['AI', '游戏'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['AI', '游戏'], tag_type='persona')
        
        # 验证 'AI' 标签的 usage_count 为 3
        ai_tag = TagStatistics.objects.get(tag='AI', tag_type='persona')
        self.assertEqual(ai_tag.usage_count, 3)
        
        # 删除第 1 个 PersonaCard
        url1 = f'/api/content/persona/{pc1.id}/'
        response = self.client.delete(url1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证 'AI' 标签的 usage_count 减少到 2
        ai_tag.refresh_from_db()
        self.assertEqual(ai_tag.usage_count, 2)
        
        # 验证 '助手' 标签被删除（只有 1 个内容使用）
        self.assertFalse(
            TagStatistics.objects.filter(tag='助手', tag_type='persona').exists()
        )
        
        # 删除第 2 个 PersonaCard
        url2 = f'/api/content/persona/{pc2.id}/'
        response = self.client.delete(url2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证 'AI' 标签的 usage_count 减少到 1
        ai_tag.refresh_from_db()
        self.assertEqual(ai_tag.usage_count, 1)
        
        # 验证 '聊天' 标签被删除
        self.assertFalse(
            TagStatistics.objects.filter(tag='聊天', tag_type='persona').exists()
        )
        
        # 删除第 3 个 PersonaCard
        url3 = f'/api/content/persona/{pc3.id}/'
        response = self.client.delete(url3)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证 'AI' 标签被删除（usage_count 降为 0）
        self.assertFalse(
            TagStatistics.objects.filter(tag='AI', tag_type='persona').exists()
        )
        
        # 验证 '游戏' 标签被删除
        self.assertFalse(
            TagStatistics.objects.filter(tag='游戏', tag_type='persona').exists()
        )

    def test_mixed_content_types_share_same_tag(self):
        """测试不同类型的内容共享同一标签名称
        
        验证：
        1. PersonaCard 和 KnowledgeBase 可以使用相同的标签名称
        2. 它们的统计是分开的（不同的 tag_type）
        3. 删除一种类型的内容不影响另一种类型的标签统计
        """
        # 创建使用 'Python' 标签的 PersonaCard
        pc = PersonaCard.objects.create(
            name='Python助手',
            description='Python编程助手',
            uploader=self.user,
            tags=['Python', '编程'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['Python', '编程'], tag_type='persona')
        
        # 创建使用 'Python' 标签的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='Python教程',
            description='Python学习资料',
            uploader=self.user,
            tags=['Python', '教程'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['Python', '教程'], tag_type='knowledge')
        
        # 验证两种类型的 'Python' 标签统计都存在
        python_persona = TagStatistics.objects.get(tag='Python', tag_type='persona')
        python_knowledge = TagStatistics.objects.get(tag='Python', tag_type='knowledge')
        
        self.assertEqual(python_persona.usage_count, 1)
        self.assertEqual(python_knowledge.usage_count, 1)
        
        # 删除 PersonaCard
        url_pc = f'/api/content/persona/{pc.id}/'
        response = self.client.delete(url_pc)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证 persona 类型的 'Python' 标签被删除
        self.assertFalse(
            TagStatistics.objects.filter(tag='Python', tag_type='persona').exists()
        )
        
        # 验证 knowledge 类型的 'Python' 标签仍然存在
        python_knowledge.refresh_from_db()
        self.assertEqual(python_knowledge.usage_count, 1)
        
        # 删除 KnowledgeBase
        url_kb = f'/api/content/knowledge/{kb.id}/'
        response = self.client.delete(url_kb)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 验证 knowledge 类型的 'Python' 标签被删除
        self.assertFalse(
            TagStatistics.objects.filter(tag='Python', tag_type='knowledge').exists()
        )


@pytest.mark.django_db
class TestTagStatisticsFinalConsistency(TestCase):
    """测试标签统计的最终一致性
    
    测试场景：
    - 执行一系列混合操作（创建、更新、删除、状态切换）
    - 验证最终的标签统计与实际公开内容一致
    - 使用 rebuild_statistics() 重建统计，验证结果相同
    
    **Validates: Requirements 2.5, 3.2**
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create_user(
            username='consistency_user',
            password='test_password',
            name='一致性测试用户'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        TagStatistics.objects.all().delete()
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        TagStatistics.objects.all().delete()
        Users.objects.all().delete()
    
    def test_mixed_operations_final_consistency(self):
        """测试混合操作后的最终一致性
        
        执行一系列复杂操作：
        1. 创建多个公开和私有内容
        2. 更新标签列表
        3. 切换公开/私有状态
        4. 删除部分内容
        5. 验证最终标签统计与实际公开内容一致
        """
        # 操作 1: 创建公开的 PersonaCard
        pc1 = PersonaCard.objects.create(
            name='助手1',
            description='描述1',
            uploader=self.user,
            tags=['AI', '助手', '聊天'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['AI', '助手', '聊天'], tag_type='persona')
        
        # 操作 2: 创建私有的 PersonaCard（不应影响统计）
        pc2 = PersonaCard.objects.create(
            name='助手2',
            description='描述2',
            uploader=self.user,
            tags=['AI', '游戏'],
            is_public=False
        )
        
        # 操作 3: 创建公开的 KnowledgeBase
        kb1 = KnowledgeBase.objects.create(
            name='知识库1',
            description='描述1',
            uploader=self.user,
            tags=['Python', 'Django'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['Python', 'Django'], tag_type='knowledge')
        
        # 操作 4: 更新 pc1 的标签（删除 '助手'，添加 '娱乐'）
        url_pc1 = f'/api/content/persona/{pc1.id}/'
        data = {
            'name': '助手1',
            'description': '描述1',
            'is_public': True,
            'tags': ['AI', '聊天', '娱乐']
        }
        response = self.client.put(url_pc1, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 操作 5: 将 pc2 从私有改为公开
        url_pc2_toggle = f'/api/content/persona/{pc2.id}/toggle-public/'
        response = self.client.post(url_pc2_toggle)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 操作 6: 删除 kb1
        url_kb1 = f'/api/content/knowledge/{kb1.id}/'
        response = self.client.delete(url_kb1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 操作 7: 将 pc1 从公开改为私有
        response = self.client.post(url_pc1 + 'toggle-public/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证最终标签统计
        # 预期结果：
        # - persona 类型：只有 pc2 是公开的，标签为 ['AI', '游戏']
        # - knowledge 类型：没有公开的内容
        
        # 验证 persona 类型的标签统计
        ai_persona = TagStatistics.objects.filter(tag='AI', tag_type='persona').first()
        game_persona = TagStatistics.objects.filter(tag='游戏', tag_type='persona').first()
        
        self.assertIsNotNone(ai_persona)
        self.assertEqual(ai_persona.usage_count, 1)
        self.assertIsNotNone(game_persona)
        self.assertEqual(game_persona.usage_count, 1)
        
        # 验证其他 persona 标签不存在
        self.assertFalse(
            TagStatistics.objects.filter(tag='助手', tag_type='persona').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='聊天', tag_type='persona').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='娱乐', tag_type='persona').exists()
        )
        
        # 验证 knowledge 类型的标签不存在
        self.assertFalse(
            TagStatistics.objects.filter(tag='Python', tag_type='knowledge').exists()
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='Django', tag_type='knowledge').exists()
        )
    
    def test_rebuild_statistics_matches_incremental_updates(self):
        """测试重建统计与增量更新的结果一致
        
        验证：
        1. 执行一系列操作后，记录当前的标签统计
        2. 使用 rebuild_statistics() 重建统计
        3. 验证重建后的统计与之前的统计完全一致
        """
        # 创建多个公开内容
        pc1 = PersonaCard.objects.create(
            name='助手A',
            description='描述A',
            uploader=self.user,
            tags=['AI', '助手'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['AI', '助手'], tag_type='persona')
        
        pc2 = PersonaCard.objects.create(
            name='助手B',
            description='描述B',
            uploader=self.user,
            tags=['AI', '聊天'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['AI', '聊天'], tag_type='persona')
        
        kb1 = KnowledgeBase.objects.create(
            name='教程A',
            description='描述A',
            uploader=self.user,
            tags=['Python', 'Web'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['Python', 'Web'], tag_type='knowledge')
        
        # 记录当前的标签统计
        persona_stats_before = {
            stat.tag: stat.usage_count
            for stat in TagStatistics.objects.filter(tag_type='persona')
        }
        knowledge_stats_before = {
            stat.tag: stat.usage_count
            for stat in TagStatistics.objects.filter(tag_type='knowledge')
        }
        
        # 重建统计
        TagService.rebuild_statistics()
        
        # 记录重建后的标签统计
        persona_stats_after = {
            stat.tag: stat.usage_count
            for stat in TagStatistics.objects.filter(tag_type='persona')
        }
        knowledge_stats_after = {
            stat.tag: stat.usage_count
            for stat in TagStatistics.objects.filter(tag_type='knowledge')
        }
        
        # 验证重建前后的统计一致
        self.assertEqual(persona_stats_before, persona_stats_after)
        self.assertEqual(knowledge_stats_before, knowledge_stats_after)
        
        # 验证具体的统计值
        self.assertEqual(persona_stats_after.get('AI'), 2)
        self.assertEqual(persona_stats_after.get('助手'), 1)
        self.assertEqual(persona_stats_after.get('聊天'), 1)
        self.assertEqual(knowledge_stats_after.get('Python'), 1)
        self.assertEqual(knowledge_stats_after.get('Web'), 1)
    
    def test_rebuild_statistics_after_complex_operations(self):
        """测试复杂操作后重建统计的正确性
        
        验证：
        1. 执行包括删除、状态切换等复杂操作
        2. 重建统计
        3. 验证统计结果正确反映当前的公开内容
        """
        # 创建内容
        pc1 = PersonaCard.objects.create(
            name='测试1',
            description='描述1',
            uploader=self.user,
            tags=['标签A', '标签B'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['标签A', '标签B'], tag_type='persona')
        
        pc2 = PersonaCard.objects.create(
            name='测试2',
            description='描述2',
            uploader=self.user,
            tags=['标签A', '标签C'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['标签A', '标签C'], tag_type='persona')
        
        # 验证初始状态
        self.assertEqual(
            TagStatistics.objects.filter(tag='标签A', tag_type='persona').first().usage_count, 2
        )
        self.assertEqual(
            TagStatistics.objects.filter(tag='标签B', tag_type='persona').first().usage_count, 1
        )
        self.assertEqual(
            TagStatistics.objects.filter(tag='标签C', tag_type='persona').first().usage_count, 1
        )
        
        # 删除 pc1
        url_pc1 = f'/api/content/persona/{pc1.id}/'
        response = self.client.delete(url_pc1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证删除后的状态
        self.assertEqual(
            TagStatistics.objects.filter(tag='标签A', tag_type='persona').first().usage_count, 1
        )
        self.assertFalse(
            TagStatistics.objects.filter(tag='标签B', tag_type='persona').exists()
        )
        self.assertEqual(
            TagStatistics.objects.filter(tag='标签C', tag_type='persona').first().usage_count, 1
        )
        
        # 将 pc2 改为私有
        url_pc2_toggle = f'/api/content/persona/{pc2.id}/toggle-public/'
        response = self.client.post(url_pc2_toggle)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 此时应该没有公开的内容，所有标签统计应该为空
        self.assertEqual(
            TagStatistics.objects.filter(tag_type='persona').count(), 0,
            "将所有内容改为私有后，应该没有标签统计"
        )
        
        # 重建统计
        TagService.rebuild_statistics()
        
        # 验证重建后仍然没有标签统计
        self.assertEqual(
            TagStatistics.objects.filter(tag_type='persona').count(), 0,
            "重建统计后，应该没有标签统计（因为没有公开内容）"
        )
        
        # 将 pc2 改回公开
        response = self.client.post(url_pc2_toggle)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 重建统计
        TagService.rebuild_statistics()
        
        # 验证重建后的统计正确
        tag_a = TagStatistics.objects.filter(tag='标签A', tag_type='persona').first()
        tag_c = TagStatistics.objects.filter(tag='标签C', tag_type='persona').first()
        
        self.assertIsNotNone(tag_a)
        self.assertEqual(tag_a.usage_count, 1)
        self.assertIsNotNone(tag_c)
        self.assertEqual(tag_c.usage_count, 1)
        
        # '标签B' 不应该存在（pc1 已删除）
        self.assertFalse(
            TagStatistics.objects.filter(tag='标签B', tag_type='persona').exists()
        )


@pytest.mark.django_db
class TestCacheClearingMechanism(TestCase):
    """测试缓存清除机制
    
    测试场景：
    - 执行标签统计更新操作
    - 验证对应类型的缓存被清除
    - 验证查询标签统计时返回最新数据
    
    **Validates: Requirements 2.5**
    """
    
    def setUp(self):
        """测试前准备"""
        self.user = Users.objects.create_user(
            username='cache_user',
            password='test_password',
            name='缓存测试用户'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        TagStatistics.objects.all().delete()
    
    def tearDown(self):
        """测试后清理"""
        PersonaCard.objects.all().delete()
        KnowledgeBase.objects.all().delete()
        TagStatistics.objects.all().delete()
        Users.objects.all().delete()
    
    def test_cache_cleared_after_tag_update(self):
        """测试标签更新后缓存被清除
        
        验证：
        1. 创建内容并查询标签统计（缓存数据）
        2. 更新标签
        3. 再次查询标签统计，验证返回最新数据
        """
        # 创建公开的 PersonaCard
        pc = PersonaCard.objects.create(
            name='缓存测试',
            description='测试描述',
            uploader=self.user,
            tags=['旧标签'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['旧标签'], tag_type='persona')
        
        # 查询标签统计（可能会缓存）
        popular_tags_before = TagService.get_popular_tags(limit=20, tag_type='persona')
        tag_names_before = [tag['tag'] for tag in popular_tags_before]
        self.assertIn('旧标签', tag_names_before)
        
        # 更新标签
        url = f'/api/content/persona/{pc.id}/'
        data = {
            'name': '缓存测试',
            'description': '测试描述',
            'is_public': True,
            'tags': ['新标签']
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 再次查询标签统计，应该返回最新数据
        popular_tags_after = TagService.get_popular_tags(limit=20, tag_type='persona')
        tag_names_after = [tag['tag'] for tag in popular_tags_after]
        
        # 验证返回最新数据
        self.assertIn('新标签', tag_names_after)
        self.assertNotIn('旧标签', tag_names_after)
    
    def test_cache_cleared_after_delete(self):
        """测试删除内容后缓存被清除
        
        验证：
        1. 创建内容并查询标签统计
        2. 删除内容
        3. 再次查询标签统计，验证标签不再出现
        """
        # 创建公开的 KnowledgeBase
        kb = KnowledgeBase.objects.create(
            name='缓存测试知识库',
            description='测试描述',
            uploader=self.user,
            tags=['临时标签'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['临时标签'], tag_type='knowledge')
        
        # 查询标签统计
        popular_tags_before = TagService.get_popular_tags(limit=20, tag_type='knowledge')
        tag_names_before = [tag['tag'] for tag in popular_tags_before]
        self.assertIn('临时标签', tag_names_before)
        
        # 删除内容
        url = f'/api/content/knowledge/{kb.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 再次查询标签统计
        popular_tags_after = TagService.get_popular_tags(limit=20, tag_type='knowledge')
        tag_names_after = [tag['tag'] for tag in popular_tags_after]
        
        # 验证标签不再出现
        self.assertNotIn('临时标签', tag_names_after)
    
    def test_cache_cleared_after_status_toggle(self):
        """测试状态切换后缓存被清除
        
        验证：
        1. 创建公开内容并查询标签统计
        2. 切换为私有
        3. 再次查询标签统计，验证标签不再出现
        4. 切换回公开
        5. 再次查询标签统计，验证标签重新出现
        """
        # 创建公开的 PersonaCard
        pc = PersonaCard.objects.create(
            name='状态切换测试',
            description='测试描述',
            uploader=self.user,
            tags=['切换标签'],
            is_public=True,
            is_pending=False
        )
        TagService.update_tag_usage(['切换标签'], tag_type='persona')
        
        # 查询标签统计
        popular_tags_1 = TagService.get_popular_tags(limit=20, tag_type='persona')
        tag_names_1 = [tag['tag'] for tag in popular_tags_1]
        self.assertIn('切换标签', tag_names_1)
        
        # 切换为私有
        url_toggle = f'/api/content/persona/{pc.id}/toggle-public/'
        response = self.client.post(url_toggle)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 再次查询标签统计
        popular_tags_2 = TagService.get_popular_tags(limit=20, tag_type='persona')
        tag_names_2 = [tag['tag'] for tag in popular_tags_2]
        self.assertNotIn('切换标签', tag_names_2)
        
        # 切换回公开
        response = self.client.post(url_toggle)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 再次查询标签统计
        popular_tags_3 = TagService.get_popular_tags(limit=20, tag_type='persona')
        tag_names_3 = [tag['tag'] for tag in popular_tags_3]
        self.assertIn('切换标签', tag_names_3)
