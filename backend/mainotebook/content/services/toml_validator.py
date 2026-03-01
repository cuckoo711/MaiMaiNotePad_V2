"""TOML 配置文件验证器

本模块提供 TOML 配置文件的验证功能，用于验证人设卡的 bot_config.toml 文件。
"""

import os
import tomllib
from typing import Tuple

from django.conf import settings


class TOMLValidator:
    """TOML 配置文件验证器
    
    验证人设卡的 bot_config.toml 文件格式。
    """
    
    @staticmethod
    def validate_file(file_path: str) -> Tuple[bool, str]:
        """验证 TOML 文件
        
        Args:
            file_path: TOML 文件路径
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
            
        Examples:
            >>> is_valid, error_msg = TOMLValidator.validate_file('/path/to/bot_config.toml')
            >>> if not is_valid:
            ...     print(f"验证失败: {error_msg}")
        """
        try:
            # 如果是相对路径，拼接 MEDIA_ROOT 得到绝对路径
            if not os.path.isabs(file_path):
                file_path = os.path.join(settings.MEDIA_ROOT, file_path)

            # 读取文件内容（tomllib 需要二进制模式）
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 解析 TOML
            config = tomllib.loads(content.decode('utf-8'))
            
            # 查找 version 字段：支持顶层和常见子字段（inner/meta/card）
            version = config.get('version')
            if version is None:
                for section in ('inner', 'meta', 'card', 'Inner', 'Meta', 'Card'):
                    sub = config.get(section)
                    if isinstance(sub, dict) and 'version' in sub:
                        version = sub['version']
                        break
            
            # 验证必需字段
            if version is None:
                return False, "缺少必需字段: version"
            
            # 验证字段类型
            if not isinstance(version, str):
                return False, "version 字段必须是字符串类型"
            
            return True, ""
            
        except FileNotFoundError:
            return False, f"文件不存在: {file_path}"
        except PermissionError:
            return False, f"无权限读取文件: {file_path}"
        except tomllib.TOMLDecodeError as e:
            return False, f"TOML 语法错误: {str(e)}"
        except UnicodeDecodeError as e:
            return False, f"文件编码错误: {str(e)}"
        except Exception as e:
            return False, f"文件读取失败: {str(e)}"
    
    @staticmethod
    def validate_content(content: str) -> Tuple[bool, str]:
        """验证 TOML 内容
        
        Args:
            content: TOML 内容字符串
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
            
        Examples:
            >>> content = 'version = "1.0.0"'
            >>> is_valid, error_msg = TOMLValidator.validate_content(content)
            >>> assert is_valid == True
        """
        try:
            # 解析 TOML
            config = tomllib.loads(content)
            
            # 查找 version 字段：支持顶层和常见子字段（inner/meta/card）
            version = config.get('version')
            if version is None:
                for section in ('inner', 'meta', 'card', 'Inner', 'Meta', 'Card'):
                    sub = config.get(section)
                    if isinstance(sub, dict) and 'version' in sub:
                        version = sub['version']
                        break
            
            # 验证必需字段
            if version is None:
                return False, "缺少必需字段: version"
            
            # 验证字段类型
            if not isinstance(version, str):
                return False, "version 字段必须是字符串类型"
            
            return True, ""
            
        except tomllib.TOMLDecodeError as e:
            return False, f"TOML 语法错误: {str(e)}"
        except Exception as e:
            return False, f"解析失败: {str(e)}"
