"""TOML 导出服务

本模块提供 TOML 配置文件的导出功能，用于将 PersonaCardConfig 对象集合格式化为 TOML 文件。
支持注释保留、被删除块处理和复杂类型格式化。

**验证需求：5.1, 5.3, 5.4, 5.5, 5.6**
"""

import json
from typing import Any, List
from django.db.models import QuerySet


class TomlExporterService:
    """TOML 导出服务
    
    负责将 PersonaCardConfig 对象集合格式化为 TOML 文件。
    """
    
    @staticmethod
    def export_to_toml(
        configs: QuerySet,
        include_deleted: bool = True
    ) -> str:
        """导出为 TOML 格式
        
        Args:
            configs: PersonaCardConfig 查询集
            include_deleted: 是否包含被删除的块（作为空块）
            
        Returns:
            str: TOML 格式的字符串
        """
        # 按 section 分组配置项
        sections_dict = {}
        deleted_sections = set()
        
        for config in configs:
            section_name = config.section_name
            
            # 记录被删除的 section
            if config.is_deleted:
                deleted_sections.add(section_name)
                continue
            
            # 初始化 section
            if section_name not in sections_dict:
                sections_dict[section_name] = {
                    'items': [],
                    'comment': None
                }
            
            # 添加配置项
            sections_dict[section_name]['items'].append({
                'key': config.key_name,
                'value': config.value,
                'type': config.data_type,
                'comment': config.description
            })
        
        # 构建 TOML 字符串
        toml_lines = []
        
        # 处理顶层配置项（section_name 为空字符串）
        if '' in sections_dict:
            top_section = sections_dict['']
            for item in top_section['items']:
                # 添加注释
                if item['comment']:
                    toml_lines.append(f"# {item['comment']}")
                
                # 添加键值对
                formatted_value = TomlExporterService.format_value(
                    item['value'], item['type']
                )
                toml_lines.append(f"{item['key']} = {formatted_value}")
                toml_lines.append('')  # 空行
        
        # 处理其他 section
        for section_name in sorted(sections_dict.keys()):
            if section_name == '':
                continue  # 已处理顶层配置项
            
            section = sections_dict[section_name]
            
            # 添加 section 标题
            toml_lines.append(f"[{section_name}]")
            
            # 添加配置项
            for item in section['items']:
                # 添加注释
                if item['comment']:
                    toml_lines.append(f"# {item['comment']}")
                
                # 添加键值对
                formatted_value = TomlExporterService.format_value(
                    item['value'], item['type']
                )
                toml_lines.append(f"{item['key']} = {formatted_value}")
            
            toml_lines.append('')  # section 之间空行
        
        # 处理被删除的 section
        if include_deleted and deleted_sections:
            for section_name in sorted(deleted_sections):
                if section_name:  # 不处理空 section 名
                    toml_lines.append(f"[{section_name}]")
                    toml_lines.append("# 此配置块已被作者删除")
                    toml_lines.append('')
        
        # 移除末尾多余的空行
        while toml_lines and toml_lines[-1] == '':
            toml_lines.pop()
        
        return '\n'.join(toml_lines)
    
    @staticmethod
    def format_value(value: str, data_type: str) -> str:
        """格式化值为 TOML 类型
        
        Args:
            value: 值（可能是 JSON 字符串）
            data_type: 数据类型
            
        Returns:
            str: 格式化后的 TOML 值字符串
        """
        if data_type == 'string':
            # 字符串需要转义和加引号
            escaped_value = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'"{escaped_value}"'
        
        elif data_type == 'integer':
            # 整数不加引号
            try:
                int_value = int(value)
                return str(int_value)
            except (ValueError, TypeError):
                # 如果转换失败，作为字符串处理
                escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
                return f'"{escaped_value}"'
        
        elif data_type == 'float':
            # 浮点数不加引号，确保有小数点
            try:
                float_value = float(value)
                # 如果是整数值，添加 .0 确保是浮点数格式
                if float_value == int(float_value):
                    return f"{int(float_value)}.0"
                return str(float_value)
            except (ValueError, TypeError):
                # 如果转换失败，作为字符串处理
                escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
                return f'"{escaped_value}"'
        
        elif data_type == 'boolean':
            # 转换为小写的 true/false
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower in ['true', 'false']:
                    return value_lower
                # 如果不是有效的布尔值字符串，作为字符串处理
                escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
                return f'"{escaped_value}"'
            return 'true' if value else 'false'
        
        elif data_type == 'array':
            # 从 JSON 字符串反序列化
            try:
                array_value = json.loads(value) if isinstance(value, str) else value
                # 格式化数组元素
                formatted_items = []
                for item in array_value:
                    if isinstance(item, str):
                        escaped_item = item.replace('\\', '\\\\').replace('"', '\\"')
                        formatted_items.append(f'"{escaped_item}"')
                    elif isinstance(item, bool):
                        formatted_items.append('true' if item else 'false')
                    else:
                        formatted_items.append(str(item))
                return f"[{', '.join(formatted_items)}]"
            except (json.JSONDecodeError, TypeError):
                # 如果解析失败，返回原始值
                return f'[{value}]'
        
        elif data_type == 'object':
            # 从 JSON 字符串反序列化
            try:
                obj_value = json.loads(value) if isinstance(value, str) else value
                # 格式化对象
                formatted_pairs = []
                for key, val in obj_value.items():
                    if isinstance(val, str):
                        escaped_val = val.replace('\\', '\\\\').replace('"', '\\"')
                        formatted_pairs.append(f'{key} = "{escaped_val}"')
                    elif isinstance(val, bool):
                        formatted_pairs.append(f'{key} = {"true" if val else "false"}')
                    else:
                        formatted_pairs.append(f'{key} = {val}')
                return f"{{ {', '.join(formatted_pairs)} }}"
            except (json.JSONDecodeError, TypeError):
                # 如果解析失败，返回原始值
                return f'{{{value}}}'
        
        else:
            # 默认作为字符串处理
            escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped_value}"'
    
    @staticmethod
    def get_deleted_sections(configs: QuerySet) -> List[str]:
        """获取被删除的配置块列表
        
        Args:
            configs: PersonaCardConfig 查询集
            
        Returns:
            list[str]: 被删除的块名列表
        """
        deleted_sections = set()
        
        for config in configs:
            if config.is_deleted and config.section_name:
                deleted_sections.add(config.section_name)
        
        return sorted(list(deleted_sections))
