"""文件服务模块

本模块提供文件上传、下载、删除等功能，包括：
- 文件类型验证（扩展名和魔数验证）
- 文件大小验证
- 文件安全性验证（路径遍历攻击防护）
- 文件存储和删除
- 文件下载响应生成
"""

import os
import uuid
import logging
from typing import Tuple, Dict, Optional, List
from django.http import FileResponse
from django.conf import settings
from ..constants import (
    ALLOWED_IMAGE_TYPES,
    ALLOWED_DOCUMENT_TYPES,
    ALLOWED_CONFIG_TYPES,
    ALL_ALLOWED_TYPES,
    MAX_FILE_SIZE,
    ERROR_MESSAGES
)
from ..exceptions import ValidationException

logger = logging.getLogger(__name__)


class FileService:
    """文件服务类
    
    提供文件上传、下载、删除等功能。
    所有方法都是静态方法，无需实例化。
    """
    
    # 文件魔数验证映射表
    # 用于验证文件内容与声明的文件类型是否一致，防止文件伪造
    MAGIC_NUMBERS = {
        'jpg': [b'\xFF\xD8\xFF'],
        'jpeg': [b'\xFF\xD8\xFF'],
        'png': [b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'],
        'gif': [b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61'],  # GIF87a 和 GIF89a
        'webp': [b'\x52\x49\x46\x46'],  # RIFF (WebP 容器格式)
        'pdf': [b'\x25\x50\x44\x46'],  # %PDF
    }
    
    @staticmethod
    def validate_file(file, allowed_extensions: Optional[List[str]] = None) -> Tuple[bool, str]:
        """验证文件
        
        验证文件的大小、类型和内容，确保文件符合安全要求。
        
        Args:
            file: Django 上传的文件对象
            allowed_extensions: 允许的扩展名列表，如果为 None 则使用默认的所有允许类型
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
            - 如果验证通过，返回 (True, "")
            - 如果验证失败，返回 (False, "错误描述")
        """
        # 验证文件大小
        if file.size > MAX_FILE_SIZE:
            error_msg = f"文件大小不能超过 {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            logger.warning(f"文件大小验证失败: {file.name}, 大小: {file.size} 字节")
            return False, error_msg
        
        # 获取文件扩展名
        file_name = file.name.lower()
        if '.' not in file_name:
            logger.warning(f"文件名无扩展名: {file.name}")
            return False, "文件名必须包含扩展名"
        
        file_ext = file_name.split('.')[-1]
        
        # 验证文件类型
        allowed = allowed_extensions if allowed_extensions else ALL_ALLOWED_TYPES
        if file_ext not in allowed:
            logger.warning(f"不支持的文件类型: {file_ext}, 文件名: {file.name}")
            return False, f"不支持的文件类型: {file_ext}。允许的类型: {', '.join(allowed)}"
        
        # 验证文件内容（魔数验证）
        # 只对有魔数定义的文件类型进行验证
        if file_ext in FileService.MAGIC_NUMBERS:
            try:
                # 读取文件头部用于魔数验证
                file.seek(0)
                header = file.read(20)  # 读取前 20 字节足够验证大多数文件类型
                file.seek(0)  # 重置文件指针
                
                # 检查文件头是否匹配任一魔数
                magic_numbers = FileService.MAGIC_NUMBERS[file_ext]
                is_valid = any(header.startswith(magic) for magic in magic_numbers)
                
                if not is_valid:
                    logger.warning(
                        f"文件魔数验证失败: {file.name}, "
                        f"声明类型: {file_ext}, "
                        f"文件头: {header[:10].hex()}"
                    )
                    return False, "文件内容与声明的文件类型不匹配"
            except Exception as e:
                logger.error(f"文件魔数验证异常: {file.name}, 错误: {str(e)}")
                return False, f"文件验证失败: {str(e)}"
        
        return True, ""
    
    @staticmethod
    def save_file(file, upload_path: str) -> Dict[str, any]:
        """保存文件到指定路径
        
        生成唯一的文件名并保存文件到指定目录。
        
        Args:
            file: Django 上传的文件对象
            upload_path: 上传路径（相对于 MEDIA_ROOT）
            
        Returns:
            Dict[str, any]: 文件信息字典，包含：
                - file_name: 生成的唯一文件名
                - original_name: 原始文件名
                - file_path: 完整文件路径
                - file_type: MIME 类型
                - file_size: 文件大小（字节）
                
        Raises:
            Exception: 当文件保存失败时
        """
        try:
            # 获取文件扩展名
            file_ext = file.name.split('.')[-1].lower()
            
            # 生成唯一文件名（使用 UUID 防止文件名冲突）
            unique_filename = f"{uuid.uuid4()}.{file_ext}"
            
            # 构建完整路径
            media_root = settings.MEDIA_ROOT
            full_dir = os.path.join(media_root, upload_path)
            full_path = os.path.join(full_dir, unique_filename)
            
            # 确保目录存在
            os.makedirs(full_dir, exist_ok=True)
            
            # 保存文件
            with open(full_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            logger.info(
                f"文件保存成功: {unique_filename}, "
                f"原始文件名: {file.name}, "
                f"大小: {file.size} 字节"
            )
            
            # 返回文件信息
            return {
                'file_name': unique_filename,
                'original_name': file.name,
                'file_path': os.path.join(upload_path, unique_filename),
                'file_type': file.content_type,
                'file_size': file.size
            }
            
        except Exception as e:
            logger.error(
                f"文件保存失败: {file.name}, "
                f"路径: {upload_path}, "
                f"错误: {str(e)}",
                exc_info=True
            )
            raise
    
    @staticmethod
    def delete_file(file_path: str) -> None:
        """删除文件
        
        删除指定路径的文件。如果文件不存在，不会抛出异常。
        
        Args:
            file_path: 文件路径（相对于 MEDIA_ROOT）
        """
        try:
            # 构建完整路径
            media_root = settings.MEDIA_ROOT
            full_path = os.path.join(media_root, file_path)
            
            # 删除文件
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"文件删除成功: {file_path}")
            else:
                logger.warning(f"文件不存在，无需删除: {file_path}")
                
        except Exception as e:
            logger.error(
                f"文件删除失败: {file_path}, "
                f"错误: {str(e)}",
                exc_info=True
            )
            # 不抛出异常，避免影响主流程
    
    @staticmethod
    def get_file_response(file_path: str, original_name: str) -> FileResponse:
        """获取文件下载响应
        
        生成文件下载的 HTTP 响应对象。
        包含路径安全性验证，防止路径遍历攻击。
        
        Args:
            file_path: 文件路径（相对于 MEDIA_ROOT）
            original_name: 原始文件名（用于下载时的文件名）
            
        Returns:
            FileResponse: Django 文件响应对象
            
        Raises:
            ValidationException: 当文件路径不安全时
            FileNotFoundError: 当文件不存在时
        """
        # 验证路径安全性（防止路径遍历攻击）
        if '..' in file_path:
            logger.warning(f"检测到路径遍历攻击尝试: {file_path}")
            raise ValidationException("非法的文件路径")
        
        # 不允许绝对路径
        if os.path.isabs(file_path):
            logger.warning(f"检测到绝对路径访问尝试: {file_path}")
            raise ValidationException("非法的文件路径")
        
        # 构建完整路径
        media_root = settings.MEDIA_ROOT
        full_path = os.path.join(media_root, file_path)
        
        # 验证文件存在
        if not os.path.exists(full_path):
            logger.warning(f"文件不存在: {file_path}")
            raise FileNotFoundError("文件不存在")
        
        # 验证路径在 MEDIA_ROOT 内（防止符号链接攻击）
        real_path = os.path.realpath(full_path)
        real_media_root = os.path.realpath(media_root)
        if not real_path.startswith(real_media_root):
            logger.warning(
                f"检测到路径遍历攻击尝试: {file_path}, "
                f"真实路径: {real_path}, "
                f"MEDIA_ROOT: {real_media_root}"
            )
            raise ValidationException("非法的文件路径")
        
        try:
            # 创建文件响应
            response = FileResponse(open(full_path, 'rb'))
            
            # 设置响应头，指定下载文件名
            # 使用 attachment 强制下载，而不是在浏览器中打开
            response['Content-Disposition'] = f'attachment; filename="{original_name}"'
            
            logger.info(f"文件下载: {file_path}, 原始文件名: {original_name}")
            
            return response
            
        except Exception as e:
            logger.error(
                f"生成文件响应失败: {file_path}, "
                f"错误: {str(e)}",
                exc_info=True
            )
            raise
    
    @staticmethod
    def get_allowed_extensions_by_category(category: str) -> List[str]:
        """根据类别获取允许的文件扩展名列表
        
        Args:
            category: 文件类别，可选值：'image', 'document', 'config', 'all'
            
        Returns:
            List[str]: 允许的扩展名列表
            
        Raises:
            ValidationException: 当类别无效时
        """
        category_map = {
            'image': ALLOWED_IMAGE_TYPES,
            'document': ALLOWED_DOCUMENT_TYPES,
            'config': ALLOWED_CONFIG_TYPES,
            'all': ALL_ALLOWED_TYPES
        }
        
        if category not in category_map:
            raise ValidationException(
                f"无效的文件类别: {category}。"
                f"允许的类别: {', '.join(category_map.keys())}"
            )
        
        return category_map[category]
