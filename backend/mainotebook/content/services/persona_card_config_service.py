"""
人设卡配置管理服务

提供人设卡配置项的 CRUD 操作和管理功能。
"""

import json
import logging
from typing import List, Dict, Any, Optional
from django.db.models import QuerySet
from django.db import transaction
from mainotebook.system.models import Users
from ..models import PersonaCard, PersonaCardConfig

logger = logging.getLogger(__name__)


class PersonaCardConfigService:
    """配置管理服务
    
    负责配置项的 CRUD 操作，支持批量创建、更新和查询配置项。
    """
    
    @staticmethod
    def create_configs(
        persona_card: PersonaCard,
        parsed_data: Dict[str, Any],
        user: Users
    ) -> List[PersonaCardConfig]:
        """批量创建配置项
        
        从解析后的 TOML 数据创建配置项记录。支持复杂类型的 JSON 序列化和排序信息保存。
        
        Args:
            persona_card: 人设卡实例
            parsed_data: 解析后的数据，格式为：
                {
                    "sections": [
                        {
                            "name": "section_name",
                            "comment": "块注释",
                            "section_order": 10,
                            "items": [
                                {
                                    "key": "key_name",
                                    "value": "value",
                                    "type": "string|integer|float|boolean|array|object",
                                    "comment": "键注释",
                                    "item_order": 5
                                }
                            ]
                        }
                    ]
                }
            user: 当前用户
            
        Returns:
            List[PersonaCardConfig]: 创建的配置项列表
            
        Raises:
            ValueError: 当数据格式不正确时
        """
        if 'sections' not in parsed_data:
            raise ValueError("解析数据缺少 'sections' 字段")
        
        configs = []
        
        for section in parsed_data['sections']:
            section_name = section.get('name', '')
            section_comment = section.get('comment', '')
            section_order = section.get('section_order', 0)
            
            for item in section.get('items', []):
                key_name = item.get('key', '')
                value = item.get('value')
                data_type = item.get('type', 'string')
                comment = item.get('comment', '')
                item_order = item.get('item_order', 0)
                
                # 复杂类型序列化为 JSON 字符串
                if data_type in ('array', 'object'):
                    value_str = json.dumps(value, ensure_ascii=False)
                else:
                    value_str = str(value)
                
                # 如果有块注释且没有项注释，使用块注释
                description = comment if comment else section_comment
                
                config = PersonaCardConfig(
                    persona_card=persona_card,
                    section_name=section_name,
                    key_name=key_name,
                    value=value_str,
                    data_type=data_type,
                    description=description,
                    section_order=section_order,
                    item_order=item_order,
                    creator=user,
                    modifier=user.username
                )
                configs.append(config)
        
        # 批量创建配置项
        with transaction.atomic():
            PersonaCardConfig.objects.bulk_create(configs)
        
        logger.info(
            f"批量创建配置项成功: persona_card_id={persona_card.id}, "
            f"配置项数量={len(configs)}, user_id={user.id}"
        )
        
        return configs
    
    @staticmethod
    def update_configs(
        persona_card: PersonaCard,
        updates: List[Dict[str, Any]],
        user: Users
    ) -> List[PersonaCardConfig]:
        """批量更新配置项
        
        根据提供的更新数据批量更新配置项。支持更新值、注释和删除标记。
        
        Args:
            persona_card: 人设卡实例
            updates: 更新数据列表，每项包含：
                {
                    "section": "section_name",
                    "key": "key_name",
                    "value": "new_value",  # 可选
                    "comment": "新注释",    # 可选
                    "is_deleted": False    # 可选
                }
            user: 当前用户
            
        Returns:
            List[PersonaCardConfig]: 更新后的配置项列表
            
        Raises:
            ValueError: 当配置项不存在时
        """
        updated_configs = []
        
        with transaction.atomic():
            for update_data in updates:
                section_name = update_data.get('section')
                key_name = update_data.get('key')
                
                if not section_name or not key_name:
                    continue
                
                try:
                    config = PersonaCardConfig.objects.get(
                        persona_card=persona_card,
                        section_name=section_name,
                        key_name=key_name
                    )
                    
                    # 更新值
                    if 'value' in update_data:
                        value = update_data['value']
                        # 复杂类型序列化为 JSON 字符串
                        if config.data_type in ('array', 'object'):
                            if isinstance(value, (list, dict)):
                                config.value = json.dumps(value, ensure_ascii=False)
                            else:
                                config.value = value
                        else:
                            config.value = str(value)
                    
                    # 更新注释
                    if 'comment' in update_data:
                        config.description = update_data['comment']
                    
                    # 更新删除标记
                    if 'is_deleted' in update_data:
                        config.is_deleted = update_data['is_deleted']
                    
                    # 更新修改者
                    config.modifier = user.username
                    config.save()
                    
                    updated_configs.append(config)
                    
                except PersonaCardConfig.DoesNotExist:
                    logger.warning(
                        f"配置项不存在: persona_card_id={persona_card.id}, "
                        f"section={section_name}, key={key_name}"
                    )
                    raise ValueError(
                        f"配置项不存在: {section_name}.{key_name}"
                    )
        
        logger.info(
            f"批量更新配置项成功: persona_card_id={persona_card.id}, "
            f"更新数量={len(updated_configs)}, user_id={user.id}"
        )
        
        return updated_configs
    
    @staticmethod
    def get_configs(
        persona_card: PersonaCard,
        include_deleted: bool = False
    ) -> QuerySet[PersonaCardConfig]:
        """获取配置项
        
        获取指定人设卡的所有配置项，可选择是否包含已删除的配置项。
        按照原始 TOML 文件中的顺序排序（section_order, item_order）。
        
        Args:
            persona_card: 人设卡实例
            include_deleted: 是否包含已删除的配置项，默认为 False
            
        Returns:
            QuerySet[PersonaCardConfig]: 配置项查询集，按 section_order 和 item_order 排序
        """
        queryset = PersonaCardConfig.objects.filter(
            persona_card=persona_card
        )
        
        if not include_deleted:
            queryset = queryset.filter(is_deleted=False)
        
        return queryset.order_by('section_order', 'item_order', 'section_name', 'key_name')
    
    @staticmethod
    def get_configs_by_section(
        persona_card: PersonaCard,
        section_name: str,
        include_deleted: bool = False
    ) -> QuerySet[PersonaCardConfig]:
        """获取指定配置块的配置项
        
        Args:
            persona_card: 人设卡实例
            section_name: 配置块名称
            include_deleted: 是否包含已删除的配置项，默认为 False
            
        Returns:
            QuerySet[PersonaCardConfig]: 配置项查询集，按 item_order 排序
        """
        queryset = PersonaCardConfig.objects.filter(
            persona_card=persona_card,
            section_name=section_name
        )
        
        if not include_deleted:
            queryset = queryset.filter(is_deleted=False)
        
        return queryset.order_by('item_order', 'key_name')
    
    @staticmethod
    def delete_section(
        persona_card: PersonaCard,
        section_name: str,
        user: Users
    ) -> int:
        """标记配置块为已删除
        
        将指定配置块下的所有配置项标记为已删除（软删除）。
        
        Args:
            persona_card: 人设卡实例
            section_name: 配置块名称
            user: 当前用户
            
        Returns:
            int: 被标记为删除的配置项数量
        """
        with transaction.atomic():
            count = PersonaCardConfig.objects.filter(
                persona_card=persona_card,
                section_name=section_name
            ).update(
                is_deleted=True,
                modifier=user.username
            )
        
        logger.info(
            f"标记配置块为已删除: persona_card_id={persona_card.id}, "
            f"section={section_name}, 影响配置项数量={count}, user_id={user.id}"
        )
        
        return count
    
    @staticmethod
    def get_value(config: PersonaCardConfig) -> Any:
        """获取配置项的值
        
        根据数据类型反序列化配置项的值。
        
        Args:
            config: 配置项实例
            
        Returns:
            Any: 反序列化后的值
        """
        if config.data_type in ('array', 'object'):
            try:
                return json.loads(config.value)
            except json.JSONDecodeError:
                return config.value
        elif config.data_type == 'integer':
            try:
                return int(config.value)
            except ValueError:
                return config.value
        elif config.data_type == 'float':
            try:
                return float(config.value)
            except ValueError:
                return config.value
        elif config.data_type == 'boolean':
            return config.value.lower() in ('true', '1', 'yes')
        else:
            return config.value
    
    @staticmethod
    def format_configs_as_dict(
        configs: QuerySet[PersonaCardConfig]
    ) -> Dict[str, Any]:
        """将配置项格式化为字典结构
        
        将配置项查询集格式化为按配置块分组的字典结构，便于前端展示。
        
        Args:
            configs: 配置项查询集
            
        Returns:
            Dict[str, Any]: 格式化后的字典，结构为：
                {
                    "sections": [
                        {
                            "name": "section_name",
                            "items": [
                                {
                                    "key": "key_name",
                                    "value": value,
                                    "type": "data_type",
                                    "comment": "description",
                                    "is_deleted": False
                                }
                            ]
                        }
                    ]
                }
        """
        sections_dict = {}
        
        for config in configs:
            section_name = config.section_name
            
            if section_name not in sections_dict:
                sections_dict[section_name] = {
                    'name': section_name,
                    'items': []
                }
            
            sections_dict[section_name]['items'].append({
                'key': config.key_name,
                'value': PersonaCardConfigService.get_value(config),
                'type': config.data_type,
                'comment': config.description or '',
                'is_deleted': config.is_deleted
            })
        
        return {
            'sections': list(sections_dict.values())
        }
