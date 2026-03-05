"""敏感信息检测服务

本模块提供敏感信息检测功能，用于检测人设卡配置中的敏感信息（5-11 位连续数字）。
支持记录敏感信息位置和生成确认声明模板。

**验证需求：8.1, 8.2, 8.3, 8.4, 8.5**
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SensitiveInfoDetectorService:
    """敏感信息检测服务
    
    检测配置中的敏感信息（5-11 位连续数字，疑似 QQ 号或群号）。
    """
    
    # 敏感信息正则表达式：5-11 位连续数字
    SENSITIVE_PATTERN = re.compile(r'\b\d{5,11}\b')
    
    @staticmethod
    def detect(configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测敏感信息
        
        在配置项列表中检测所有 5-11 位连续数字，记录其位置和匹配内容。
        
        Args:
            configs: 配置项列表，每项包含：
                {
                    "section": "块名",
                    "key": "键名",
                    "value": "值"
                }
            
        Returns:
            list[dict]: 敏感信息列表，每项包含：
                {
                    "section": "块名",
                    "key": "键名",
                    "value": "包含敏感信息的值",
                    "matches": ["12345", "67890"],  # 匹配到的数字列表
                    "path": "section.key"  # 配置项路径
                }
        """
        sensitive_items = []
        
        for config in configs:
            section = config.get('section', '')
            key = config.get('key', '')
            value = str(config.get('value', ''))
            
            # 检测敏感信息
            matches = SensitiveInfoDetectorService.SENSITIVE_PATTERN.findall(value)
            
            if matches:
                # 构建配置项路径
                path = f"{section}.{key}" if section else key
                
                sensitive_items.append({
                    'section': section,
                    'key': key,
                    'value': value,
                    'matches': matches,
                    'path': path
                })
        
        if sensitive_items:
            logger.info(
                f"检测到敏感信息: 配置项数量={len(configs)}, "
                f"敏感信息数量={len(sensitive_items)}"
            )
        
        return sensitive_items
    
    @staticmethod
    def detect_from_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从配置块列表中检测敏感信息
        
        Args:
            sections: 配置块列表，格式为：
                [
                    {
                        "name": "section_name",
                        "items": [
                            {
                                "key": "key_name",
                                "value": "value"
                            }
                        ]
                    }
                ]
            
        Returns:
            list[dict]: 敏感信息列表，格式同 detect 方法
        """
        configs = []
        
        # 将配置块列表转换为配置项列表
        for section in sections:
            section_name = section.get('name', '')
            items = section.get('items', [])
            
            for item in items:
                configs.append({
                    'section': section_name,
                    'key': item.get('key', ''),
                    'value': item.get('value', '')
                })
        
        return SensitiveInfoDetectorService.detect(configs)
    
    @staticmethod
    def generate_confirmation_text(sensitive_items: List[Dict[str, Any]]) -> str:
        """生成确认声明文本
        
        根据检测到的敏感信息生成确认声明模板。
        
        Args:
            sensitive_items: 敏感信息列表（由 detect 方法返回）
            
        Returns:
            str: 确认声明模板，格式为：
                "我已确认该文件在第X行、第Y行的内容不涉及个人隐私信息"
        """
        if not sensitive_items:
            return ""
        
        # 提取所有配置项路径
        paths = [item['path'] for item in sensitive_items]
        
        # 生成确认声明
        if len(paths) == 1:
            return f"我已确认该文件在配置项 {paths[0]} 的内容不涉及个人隐私信息"
        else:
            paths_str = "、".join(paths)
            return f"我已确认该文件在配置项 {paths_str} 的内容不涉及个人隐私信息"
    
    @staticmethod
    def get_sensitive_locations(sensitive_items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """获取敏感信息位置列表
        
        提取敏感信息的位置信息，用于记录到数据库。
        
        Args:
            sensitive_items: 敏感信息列表（由 detect 方法返回）
            
        Returns:
            list[dict]: 位置信息列表，每项包含：
                {
                    "path": "section.key",
                    "matches": ["12345", "67890"]
                }
        """
        locations = []
        
        for item in sensitive_items:
            locations.append({
                'path': item['path'],
                'matches': item['matches']
            })
        
        return locations
