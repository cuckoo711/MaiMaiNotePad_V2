"""TOML 解析服务

本模块提供 TOML 配置文件的解析功能，用于解析人设卡的 bot_config.toml 文件。
支持提取配置块、键值对、数据类型识别和注释关联。

**验证需求：4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8**
"""

import re
import tomllib
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class TomlParserService:
    """TOML 解析服务
    
    负责解析 bot_config.toml 文件，提取配置块、键值对、数据类型和注释。
    """
    
    @staticmethod
    def parse_file(file_path: str) -> Dict[str, Any]:
        """解析 TOML 文件
        
        Args:
            file_path: TOML 文件路径
            
        Returns:
            dict: 解析结果，包含以下结构：
                {
                    "sections": [
                        {
                            "name": "section_name",
                            "comment": "块注释",
                            "items": [
                                {
                                    "key": "key_name",
                                    "value": "value",
                                    "type": "string|integer|float|boolean|array|object",
                                    "comment": "键注释"
                                }
                            ]
                        }
                    ],
                    "version": "1.0"
                }
                
        Raises:
            FileNotFoundError: 文件不存在
            tomllib.TOMLDecodeError: TOML 格式错误
            ValueError: 缺少必需字段
        """
        # 读取文件内容
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read().decode('utf-8')
        except FileNotFoundError as e:
            logger.error(f"TOML 文件不存在: {file_path}")
            raise
        except UnicodeDecodeError as e:
            logger.error(f"TOML 文件编码错误: {file_path}, 错误: {str(e)}")
            raise
        
        # 解析 TOML
        try:
            parsed_data = tomllib.loads(file_content)
        except tomllib.TOMLDecodeError as e:
            logger.error(
                f"TOML 解析失败: {file_path}, "
                f"错误: {str(e)}"
            )
            raise
        
        # 提取注释
        comments = TomlParserService.extract_comments(file_content)
        
        # 验证结构
        try:
            TomlParserService.validate_structure(parsed_data)
        except ValueError as e:
            logger.warning(f"TOML 结构验证失败: {file_path}, 错误: {str(e)}")
            raise
        
        # 构建结果
        result = TomlParserService._build_result(parsed_data, comments, file_content)
        
        logger.info(
            f"TOML 文件解析成功: {file_path}, "
            f"配置块数量={len(result.get('sections', []))}, "
            f"版本={result.get('version')}"
        )
        
        return result
    
    @staticmethod
    def parse_content(content: str) -> Dict[str, Any]:
        """解析 TOML 内容字符串
        
        Args:
            content: TOML 内容字符串
            
        Returns:
            dict: 解析结果，格式同 parse_file
            
        Raises:
            tomllib.TOMLDecodeError: TOML 格式错误
            ValueError: 缺少必需字段
        """
        # 解析 TOML
        try:
            parsed_data = tomllib.loads(content)
        except tomllib.TOMLDecodeError as e:
            logger.error(f"TOML 内容解析失败, 错误: {str(e)}")
            raise
        
        # 提取注释
        comments = TomlParserService.extract_comments(content)
        
        # 验证结构
        try:
            TomlParserService.validate_structure(parsed_data)
        except ValueError as e:
            logger.warning(f"TOML 结构验证失败, 错误: {str(e)}")
            raise
        
        # 构建结果
        result = TomlParserService._build_result(parsed_data, comments, content)
        
        logger.info(
            f"TOML 内容解析成功, "
            f"配置块数量={len(result.get('sections', []))}, "
            f"版本={result.get('version')}"
        )
        
        return result
    
    @staticmethod
    def validate_structure(parsed_data: Dict[str, Any]) -> bool:
        """验证 TOML 结构
        
        Args:
            parsed_data: 解析后的数据
            
        Returns:
            bool: 是否有效
            
        Raises:
            ValueError: 结构无效时抛出异常
        """
        # 查找 version 字段：支持顶层、inner、inner.meta.card 等位置
        version = parsed_data.get('version')
        
        if version is None:
            # 尝试在 inner 中查找 version
            inner = parsed_data.get('inner', {})
            if isinstance(inner, dict):
                version = inner.get('version')
                
                if version is None:
                    # 尝试在 inner.meta 中查找
                    meta = inner.get('meta', {})
                    if isinstance(meta, dict):
                        version = meta.get('version')
                        
                        if version is None:
                            # 尝试在 inner.meta.card 中查找
                            card = meta.get('card', {})
                            if isinstance(card, dict):
                                version = card.get('version')
        
        if version is None:
            raise ValueError("缺少必需字段: version（应在顶层、inner 或 inner.meta.card 中）")
        
        return True
    
    @staticmethod
    def extract_comments(file_content: str) -> Dict[int, str]:
        """提取注释并关联到配置项
        
        Args:
            file_content: TOML 文件内容
            
        Returns:
            dict: 注释映射，键为行号（从 1 开始），值为注释内容
        """
        comments = {}
        lines = file_content.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # 去除首尾空白
            stripped_line = line.strip()
            
            # 检查是否是注释行（以 # 开头）
            if stripped_line.startswith('#'):
                # 提取注释内容（去除 # 和空白）
                comment_text = stripped_line[1:].strip()
                comments[line_num] = comment_text
            
            # 检查是否是行内注释
            elif '#' in line:
                # 查找 # 的位置（需要排除字符串中的 #）
                # 简单处理：查找不在引号内的 #
                in_string = False
                escape_next = False
                
                for i, char in enumerate(line):
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"':
                        in_string = not in_string
                        continue
                    
                    if char == '#' and not in_string:
                        # 找到行内注释
                        comment_text = line[i+1:].strip()
                        if comment_text:
                            comments[line_num] = comment_text
                        break
        
        return comments
    
    @staticmethod
    def _identify_data_type(value: Any) -> str:
        """识别数据类型
        
        Args:
            value: 值
            
        Returns:
            str: 数据类型（string, integer, float, boolean, array, object）
        """
        if isinstance(value, bool):
            # 注意：bool 必须在 int 之前检查，因为 bool 是 int 的子类
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, str):
            return 'string'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        else:
            return 'string'  # 默认为字符串
    
    @staticmethod
    def _build_result(
        parsed_data: Dict[str, Any],
        comments: Dict[int, str],
        file_content: str
    ) -> Dict[str, Any]:
        """构建解析结果
        
        Args:
            parsed_data: 解析后的 TOML 数据
            comments: 注释映射
            file_content: 原始文件内容
            
        Returns:
            dict: 格式化的解析结果
        """
        sections = []
        lines = file_content.split('\n')
        
        # 提取 version 字段
        version = parsed_data.get('version')
        if version is None:
            # 尝试在 inner 中查找
            inner = parsed_data.get('inner', {})
            if isinstance(inner, dict):
                version = inner.get('version')
                
                if version is None:
                    # 尝试在 inner.meta 中查找
                    meta = inner.get('meta', {})
                    if isinstance(meta, dict):
                        version = meta.get('version')
                        
                        if version is None:
                            # 尝试在 inner.meta.card 中查找
                            card = meta.get('card', {})
                            if isinstance(card, dict):
                                version = card.get('version')
        
        # 构建行号到配置项的映射，用于确定排序
        line_to_section = {}  # {line_num: section_name}
        line_to_key = {}  # {line_num: (section_name, key_name)}
        
        # 解析文件，记录每个 section 和 key 的行号
        current_section = None
        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            
            # 检查是否是 section 声明
            section_match = re.match(r'^\[([^\]]+)\]', stripped)
            if section_match:
                section_name = section_match.group(1)
                current_section = section_name
                line_to_section[line_num] = section_name
                continue
            
            # 检查是否是键值对
            key_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=', stripped)
            if key_match:
                key_name = key_match.group(1)
                line_to_key[line_num] = (current_section, key_name)
        
        # 处理顶层配置项（不在任何 section 中的）
        top_level_items = []
        for key, value in parsed_data.items():
            if not isinstance(value, dict):
                # 查找该键的注释
                key_comment = TomlParserService._find_comment_for_key(
                    key, lines, comments, section_name=None
                )
                
                # 查找该键的行号
                item_order = 0
                for line_num, (sec, k) in line_to_key.items():
                    if sec is None and k == key:
                        item_order = line_num
                        break
                
                top_level_items.append({
                    'key': key,
                    'value': value,
                    'type': TomlParserService._identify_data_type(value),
                    'comment': key_comment,
                    'item_order': item_order
                })
        
        if top_level_items:
            # 查找顶层的注释（文件开头的注释）
            top_comment = TomlParserService._find_section_comment(
                None, lines, comments
            )
            
            # 顶层配置块的排序为 0
            sections.append({
                'name': '',  # 顶层配置项，section 名称为空
                'comment': top_comment,
                'items': top_level_items,
                'section_order': 0
            })
        
        # 处理各个 section
        for section_name, section_data in parsed_data.items():
            if isinstance(section_data, dict):
                # 这是一个 section
                section_items = []
                
                # 查找该 section 的行号
                section_order = 0
                for line_num, sec in line_to_section.items():
                    if sec == section_name:
                        section_order = line_num
                        break
                
                for key, value in section_data.items():
                    # 查找该键的注释
                    key_comment = TomlParserService._find_comment_for_key(
                        key, lines, comments, section_name=section_name
                    )
                    
                    # 查找该键的行号
                    item_order = 0
                    for line_num, (sec, k) in line_to_key.items():
                        if sec == section_name and k == key:
                            item_order = line_num
                            break
                    
                    section_items.append({
                        'key': key,
                        'value': value,
                        'type': TomlParserService._identify_data_type(value),
                        'comment': key_comment,
                        'item_order': item_order
                    })
                
                # 查找 section 的注释
                section_comment = TomlParserService._find_section_comment(
                    section_name, lines, comments
                )
                
                sections.append({
                    'name': section_name,
                    'comment': section_comment,
                    'items': section_items,
                    'section_order': section_order
                })
        
        return {
            'sections': sections,
            'version': version
        }
    
    @staticmethod
    def _find_section_comment(
        section_name: Optional[str],
        lines: List[str],
        comments: Dict[int, str]
    ) -> str:
        """查找 section 的注释
        
        Args:
            section_name: section 名称，None 表示顶层
            lines: 文件行列表
            comments: 注释映射
            
        Returns:
            str: section 的注释，如果没有则返回空字符串
        """
        if section_name is None:
            # 顶层注释：查找文件开头的注释
            for line_num in sorted(comments.keys()):
                if line_num <= 3:  # 只查找前 3 行
                    return comments[line_num]
            return ''
        
        # 查找 section 声明行
        section_pattern = re.compile(rf'^\s*\[{re.escape(section_name)}\]\s*$')
        
        for line_num, line in enumerate(lines, start=1):
            if section_pattern.match(line):
                # 找到 section 声明，查找其上方的注释
                # 向上查找连续的注释行
                comment_lines = []
                for prev_line_num in range(line_num - 1, 0, -1):
                    if prev_line_num in comments:
                        comment_lines.insert(0, comments[prev_line_num])
                    elif lines[prev_line_num - 1].strip():
                        # 遇到非空非注释行，停止
                        break
                
                return ' '.join(comment_lines) if comment_lines else ''
        
        return ''
    
    @staticmethod
    def _find_comment_for_key(
        key: str,
        lines: List[str],
        comments: Dict[int, str],
        section_name: Optional[str]
    ) -> str:
        """查找配置项的注释
        
        Args:
            key: 配置项键名
            lines: 文件行列表
            comments: 注释映射
            section_name: 所属 section 名称，None 表示顶层
            
        Returns:
            str: 配置项的注释，如果没有则返回空字符串
        """
        # 查找键的声明行
        key_pattern = re.compile(rf'^\s*{re.escape(key)}\s*=')
        
        # 如果有 section，需要先找到 section 的位置
        in_target_section = (section_name is None)
        
        for line_num, line in enumerate(lines, start=1):
            # 检查是否进入目标 section
            if section_name is not None:
                section_pattern = re.compile(rf'^\s*\[{re.escape(section_name)}\]\s*$')
                if section_pattern.match(line):
                    in_target_section = True
                    continue
                
                # 检查是否进入其他 section
                other_section_pattern = re.compile(r'^\s*\[.+\]\s*$')
                if in_target_section and other_section_pattern.match(line):
                    # 进入了其他 section，停止查找
                    break
            
            # 在目标 section 中查找键
            if in_target_section and key_pattern.match(line):
                # 找到键声明
                # 1. 检查行内注释
                if line_num in comments:
                    return comments[line_num]
                
                # 2. 检查上方的注释（紧邻的注释行）
                if line_num - 1 in comments:
                    # 向上查找连续的注释行
                    comment_lines = []
                    for prev_line_num in range(line_num - 1, 0, -1):
                        if prev_line_num in comments:
                            comment_lines.insert(0, comments[prev_line_num])
                        elif lines[prev_line_num - 1].strip():
                            # 遇到非空非注释行，停止
                            break
                    
                    return ' '.join(comment_lines) if comment_lines else ''
                
                return ''
        
        return ''
