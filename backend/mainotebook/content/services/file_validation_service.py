"""文件验证服务模块

本模块提供人设卡配置文件的验证功能，包括：
- 文件名验证（必须为 bot_config.toml）
- 文件大小验证（1KB-2MB）
- MIME 类型验证（text/plain 或 application/toml）
- UTF-8 编码验证
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class FileValidationService:
    """文件验证服务类
    
    提供人设卡配置文件的验证功能。
    所有方法都是静态方法，无需实例化。
    """
    
    # 文件大小限制常量
    MIN_FILE_SIZE = 1024  # 1KB
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    
    # 允许的文件名
    ALLOWED_FILENAME = "bot_config.toml"
    
    # 允许的 MIME 类型
    ALLOWED_MIME_TYPES = ["text/plain", "application/toml"]
    
    @staticmethod
    def validate_filename(file) -> Tuple[bool, str]:
        """验证文件名为 bot_config.toml
        
        Args:
            file: Django 上传的文件对象
            
        Returns:
            Tuple[bool, str]: (是否通过验证, 错误消息)
            - 如果验证通过，返回 (True, "")
            - 如果验证失败，返回 (False, "错误描述")
        """
        if file.name != FileValidationService.ALLOWED_FILENAME:
            error_msg = f"文件名必须为 {FileValidationService.ALLOWED_FILENAME}"
            logger.warning(f"文件名验证失败: {file.name}")
            return False, error_msg
        
        return True, ""
    
    @staticmethod
    def validate_file_size(file) -> Tuple[bool, str]:
        """验证文件大小在 1KB-2MB 之间
        
        Args:
            file: Django 上传的文件对象
            
        Returns:
            Tuple[bool, str]: (是否通过验证, 错误消息)
            - 如果验证通过，返回 (True, "")
            - 如果验证失败，返回 (False, "错误描述")
        """
        file_size = file.size
        
        if file_size < FileValidationService.MIN_FILE_SIZE:
            error_msg = f"文件大小不能小于 {FileValidationService.MIN_FILE_SIZE / 1024:.0f}KB"
            logger.warning(f"文件大小验证失败（过小）: {file.name}, 大小: {file_size} 字节")
            return False, error_msg
        
        if file_size > FileValidationService.MAX_FILE_SIZE:
            error_msg = f"文件大小不能超过 {FileValidationService.MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            logger.warning(f"文件大小验证失败（过大）: {file.name}, 大小: {file_size} 字节")
            return False, error_msg
        
        return True, ""
    
    @staticmethod
    def validate_mime_type(file) -> Tuple[bool, str]:
        """验证 MIME 类型为 text/plain 或 application/toml
        
        Args:
            file: Django 上传的文件对象
            
        Returns:
            Tuple[bool, str]: (是否通过验证, 错误消息)
            - 如果验证通过，返回 (True, "")
            - 如果验证失败，返回 (False, "错误描述")
        """
        content_type = file.content_type
        
        if content_type not in FileValidationService.ALLOWED_MIME_TYPES:
            error_msg = (
                f"文件 MIME 类型必须为 {' 或 '.join(FileValidationService.ALLOWED_MIME_TYPES)}，"
                f"当前为 {content_type}"
            )
            logger.warning(f"MIME 类型验证失败: {file.name}, MIME 类型: {content_type}")
            return False, error_msg
        
        return True, ""
    
    @staticmethod
    def validate_encoding(file) -> Tuple[bool, str]:
        """验证文件编码为 UTF-8
        
        Args:
            file: Django 上传的文件对象
            
        Returns:
            Tuple[bool, str]: (是否通过验证, 错误消息)
            - 如果验证通过，返回 (True, "")
            - 如果验证失败，返回 (False, "错误描述")
        """
        try:
            # 读取文件内容并尝试用 UTF-8 解码
            file.seek(0)
            content = file.read()
            file.seek(0)  # 重置文件指针
            
            # 尝试解码为 UTF-8
            content.decode('utf-8')
            
            return True, ""
            
        except UnicodeDecodeError as e:
            error_msg = "文件编码必须为 UTF-8"
            logger.warning(
                f"文件编码验证失败: {file.name}, "
                f"错误: {str(e)}"
            )
            return False, error_msg
        except Exception as e:
            error_msg = f"文件编码验证失败: {str(e)}"
            logger.error(
                f"文件编码验证异常: {file.name}, "
                f"错误: {str(e)}",
                exc_info=True
            )
            return False, error_msg
    
    @staticmethod
    def validate_file(file) -> Tuple[bool, str]:
        """执行所有验证
        
        按顺序执行文件名、文件大小、MIME 类型和编码验证。
        如果任一验证失败，立即返回失败结果。
        
        Args:
            file: Django 上传的文件对象
            
        Returns:
            Tuple[bool, str]: (是否通过验证, 错误消息)
            - 如果所有验证通过，返回 (True, "")
            - 如果任一验证失败，返回 (False, "第一个失败验证的错误描述")
        """
        # 1. 验证文件名
        is_valid, error_msg = FileValidationService.validate_filename(file)
        if not is_valid:
            return False, error_msg
        
        # 2. 验证文件大小
        is_valid, error_msg = FileValidationService.validate_file_size(file)
        if not is_valid:
            return False, error_msg
        
        # 3. 验证 MIME 类型
        is_valid, error_msg = FileValidationService.validate_mime_type(file)
        if not is_valid:
            return False, error_msg
        
        # 4. 验证编码
        is_valid, error_msg = FileValidationService.validate_encoding(file)
        if not is_valid:
            return False, error_msg
        
        logger.info(f"文件验证通过: {file.name}, 大小: {file.size} 字节")
        return True, ""
