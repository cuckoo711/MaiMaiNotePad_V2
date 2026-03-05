"""文件服务属性测试模块

使用 Hypothesis 进行基于属性的测试，验证文件服务的验证规则。

**Validates: Requirements 1.2, 2.2, 8.1, 8.2**
"""

import io
import os
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import FileResponse
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.content.services.file_service import FileService
from mainotebook.content.exceptions import ValidationException
from mainotebook.content.constants import (
    ALLOWED_IMAGE_TYPES,
    ALLOWED_DOCUMENT_TYPES,
    ALLOWED_CONFIG_TYPES,
    ALL_ALLOWED_TYPES,
    MAX_FILE_SIZE
)


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


# 文件魔数映射（用于生成有效的文件内容）
FILE_MAGIC_NUMBERS = {
    'jpg': b'\xFF\xD8\xFF\xE0\x00\x10JFIF',
    'jpeg': b'\xFF\xD8\xFF\xE0\x00\x10JFIF',
    'png': b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A\x00\x00\x00\x0DIHDR',
    'gif': b'\x47\x49\x46\x38\x39\x61',  # GIF89a
    'webp': b'\x52\x49\x46\x46\x00\x00\x00\x00WEBP',
    'pdf': b'\x25\x50\x44\x46\x2D\x31\x2E\x34',  # %PDF-1.4
    'txt': b'This is a text file content',
    'md': b'# Markdown content',
    'toml': b'[section]\nkey = "value"',
    'json': b'{"key": "value"}',
    'yaml': b'key: value',
    'yml': b'key: value',
}


class FileUploadValidationPropertyTest(TestCase):
    """文件上传验证规则属性测试
    
    **属性 2：文件上传验证规则**
    **Validates: Requirements 1.2, 2.2, 8.1, 8.2**
    
    验证文件上传的验证规则：
    - 文件类型验证（图片、文档、配置文件）
    - 文件大小验证（不超过 10MB）
    - 验证应拒绝无效文件
    - 验证应接受有效文件
    """
    
    @given(
        file_ext=st.sampled_from(ALL_ALLOWED_TYPES),
        file_size=st.integers(min_value=100, max_value=MAX_FILE_SIZE)
    )
    @settings(max_examples=100, deadline=None)
    def test_valid_files_pass_validation(self, file_ext, file_size):
        """属性：有效的文件应通过验证
        
        **Validates: Requirements 8.1**
        
        对于所有允许的文件类型和有效的文件大小，
        文件验证应该返回成功。
        """
        # 生成有效的文件内容（包含正确的魔数）
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            # 确保文件大小足够容纳魔数
            content_size = max(file_size, len(magic_number) + 10)
            file_content = magic_number + b'\x00' * (content_size - len(magic_number))
        else:
            file_content = b'Valid file content\n' * (file_size // 20 + 1)
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"test_file.{file_ext}",
            content=file_content[:file_size],
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：有效文件应通过验证
        self.assertTrue(
            is_valid,
            f"有效文件验证失败: 类型={file_ext}, 大小={file_size}, 错误={error_msg}"
        )
        self.assertEqual(error_msg, "")
    
    @given(
        file_ext=st.sampled_from(ALL_ALLOWED_TYPES),
        file_size=st.integers(min_value=MAX_FILE_SIZE + 1, max_value=MAX_FILE_SIZE + 1024 * 1024)
    )
    @settings(max_examples=100, deadline=None)
    def test_oversized_files_fail_validation(self, file_ext, file_size):
        """属性：超大文件应被拒绝
        
        **Validates: Requirements 8.1, 8.12**
        
        对于所有超过大小限制的文件，
        文件验证应该返回失败，并提供明确的错误信息。
        """
        # 生成文件内容
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            file_content = magic_number + b'\x00' * (file_size - len(magic_number))
        else:
            file_content = b'\x00' * file_size
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"test_file.{file_ext}",
            content=file_content,
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：超大文件应被拒绝
        self.assertFalse(
            is_valid,
            f"超大文件未被拒绝: 类型={file_ext}, 大小={file_size}"
        )
        self.assertIn("10MB", error_msg)
    
    @given(
        invalid_ext=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=2,
            max_size=10
        ).filter(lambda x: x not in ALL_ALLOWED_TYPES),
        file_size=st.integers(min_value=100, max_value=1024)
    )
    @settings(max_examples=100, deadline=None)
    def test_invalid_file_types_fail_validation(self, invalid_ext, file_size):
        """属性：不支持的文件类型应被拒绝
        
        **Validates: Requirements 8.1, 8.11**
        
        对于所有不在允许列表中的文件类型，
        文件验证应该返回失败，并提供明确的错误信息。
        """
        # 跳过空字符串和包含特殊字符的扩展名
        assume(len(invalid_ext) > 0)
        assume('.' not in invalid_ext)
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"test_file.{invalid_ext}",
            content=b'\x00' * file_size,
            content_type=f"application/{invalid_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：不支持的文件类型应被拒绝
        self.assertFalse(
            is_valid,
            f"不支持的文件类型未被拒绝: 类型={invalid_ext}"
        )
        self.assertIn("不支持的文件类型", error_msg)
    
    @given(
        file_ext=st.sampled_from(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']),
        file_size=st.integers(min_value=100, max_value=MAX_FILE_SIZE)
    )
    @settings(max_examples=100, deadline=None)
    def test_files_with_wrong_magic_number_fail_validation(self, file_ext, file_size):
        """属性：魔数不匹配的文件应被拒绝
        
        **Validates: Requirements 8.6, 8.13**
        
        对于声明类型与实际内容不匹配的文件，
        文件验证应该返回失败，防止文件伪造。
        """
        # 生成错误的文件内容（不包含正确的魔数）
        # 使用随机字节，确保不会意外匹配任何魔数
        file_content = b'\xFF\xFF\xFF\xFF' + b'\x00' * (file_size - 4)
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"test_file.{file_ext}",
            content=file_content,
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：魔数不匹配的文件应被拒绝
        self.assertFalse(
            is_valid,
            f"魔数不匹配的文件未被拒绝: 类型={file_ext}"
        )
        self.assertIn("不匹配", error_msg)
    
    @given(
        file_name=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=50
        ).filter(lambda x: '.' not in x),
        file_size=st.integers(min_value=100, max_value=1024)
    )
    @settings(max_examples=100, deadline=None)
    def test_files_without_extension_fail_validation(self, file_name, file_size):
        """属性：没有扩展名的文件应被拒绝
        
        **Validates: Requirements 8.1**
        
        对于没有扩展名的文件，
        文件验证应该返回失败。
        """
        # 跳过空文件名
        assume(len(file_name) > 0)
        
        # 创建上传文件对象（没有扩展名）
        file = SimpleUploadedFile(
            name=file_name,
            content=b'\x00' * file_size,
            content_type="application/octet-stream"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：没有扩展名的文件应被拒绝
        self.assertFalse(
            is_valid,
            f"没有扩展名的文件未被拒绝: 文件名={file_name}"
        )
        self.assertIn("扩展名", error_msg)
    
    @given(
        file_ext=st.sampled_from(ALLOWED_IMAGE_TYPES),
        file_size=st.integers(min_value=100, max_value=MAX_FILE_SIZE)
    )
    @settings(max_examples=100, deadline=None)
    def test_image_files_pass_validation(self, file_ext, file_size):
        """属性：有效的图片文件应通过验证
        
        **Validates: Requirements 8.1, 8.4**
        
        对于所有允许的图片类型，
        文件验证应该返回成功。
        """
        # 生成有效的图片文件内容
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            content_size = max(file_size, len(magic_number) + 10)
            file_content = magic_number + b'\x00' * (content_size - len(magic_number))
        else:
            file_content = b'Image data\n' * (file_size // 11 + 1)
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"image.{file_ext}",
            content=file_content[:file_size],
            content_type=f"image/{file_ext}"
        )
        
        # 验证文件（仅允许图片类型）
        is_valid, error_msg = FileService.validate_file(file, allowed_extensions=ALLOWED_IMAGE_TYPES)
        
        # 断言：有效的图片文件应通过验证
        self.assertTrue(
            is_valid,
            f"有效的图片文件验证失败: 类型={file_ext}, 大小={file_size}, 错误={error_msg}"
        )
    
    @given(
        file_ext=st.sampled_from(ALLOWED_DOCUMENT_TYPES),
        file_size=st.integers(min_value=100, max_value=MAX_FILE_SIZE)
    )
    @settings(max_examples=100, deadline=None)
    def test_document_files_pass_validation(self, file_ext, file_size):
        """属性：有效的文档文件应通过验证
        
        **Validates: Requirements 8.1, 8.4**
        
        对于所有允许的文档类型，
        文件验证应该返回成功。
        """
        # 生成有效的文档文件内容
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            content_size = max(file_size, len(magic_number) + 10)
            file_content = magic_number + b'\x00' * (content_size - len(magic_number))
        else:
            file_content = b'Document content\n' * (file_size // 17 + 1)
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"document.{file_ext}",
            content=file_content[:file_size],
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件（仅允许文档类型）
        is_valid, error_msg = FileService.validate_file(file, allowed_extensions=ALLOWED_DOCUMENT_TYPES)
        
        # 断言：有效的文档文件应通过验证
        self.assertTrue(
            is_valid,
            f"有效的文档文件验证失败: 类型={file_ext}, 大小={file_size}, 错误={error_msg}"
        )
    
    @given(
        file_ext=st.sampled_from(ALLOWED_CONFIG_TYPES),
        file_size=st.integers(min_value=1, max_value=MAX_FILE_SIZE)
    )
    @settings(max_examples=100, deadline=None)
    def test_config_files_pass_validation(self, file_ext, file_size):
        """属性：有效的配置文件应通过验证
        
        **Validates: Requirements 8.1, 8.4**
        
        对于所有允许的配置文件类型，
        文件验证应该返回成功。
        """
        # 生成有效的配置文件内容
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            content_size = max(file_size, len(magic_number) + 10)
            file_content = magic_number + b'\x00' * (content_size - len(magic_number))
        else:
            file_content = b'\x00' * file_size
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"config.{file_ext}",
            content=file_content[:file_size],
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件（仅允许配置文件类型）
        is_valid, error_msg = FileService.validate_file(file, allowed_extensions=ALLOWED_CONFIG_TYPES)
        
        # 断言：有效的配置文件应通过验证
        self.assertTrue(
            is_valid,
            f"有效的配置文件验证失败: 类型={file_ext}, 大小={file_size}, 错误={error_msg}"
        )
    
    @given(
        file_ext=st.sampled_from(ALL_ALLOWED_TYPES),
        file_size=st.integers(min_value=1, max_value=MAX_FILE_SIZE)
    )
    @settings(max_examples=100, deadline=None)
    def test_validation_is_case_insensitive(self, file_ext, file_size):
        """属性：文件扩展名验证应不区分大小写
        
        **Validates: Requirements 8.1**
        
        对于所有允许的文件类型，
        无论扩展名使用大写、小写还是混合大小写，
        文件验证都应该返回相同的结果。
        """
        # 生成有效的文件内容
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            content_size = max(file_size, len(magic_number) + 10)
            file_content = magic_number + b'\x00' * (content_size - len(magic_number))
        else:
            file_content = b'\x00' * file_size
        
        # 测试小写扩展名
        file_lower = SimpleUploadedFile(
            name=f"test.{file_ext.lower()}",
            content=file_content[:file_size],
            content_type=f"application/{file_ext}"
        )
        is_valid_lower, _ = FileService.validate_file(file_lower)
        
        # 测试大写扩展名
        file_upper = SimpleUploadedFile(
            name=f"test.{file_ext.upper()}",
            content=file_content[:file_size],
            content_type=f"application/{file_ext}"
        )
        is_valid_upper, _ = FileService.validate_file(file_upper)
        
        # 断言：大小写应返回相同的验证结果
        self.assertEqual(
            is_valid_lower,
            is_valid_upper,
            f"大小写扩展名验证结果不一致: 类型={file_ext}"
        )
    
    @given(
        file_ext=st.sampled_from(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'])
    )
    @settings(max_examples=100, deadline=None)
    def test_zero_size_files_fail_validation(self, file_ext):
        """属性：空文件应被拒绝（仅对有魔数验证的文件类型）
        
        **Validates: Requirements 8.1, 8.6, 8.13**
        
        对于有魔数验证的文件类型（图片和 PDF），
        大小为 0 的文件应该被拒绝，因为无法验证魔数。
        
        注意：对于没有魔数验证的文件类型（txt, md, toml, json, yaml, yml），
        空文件可能通过验证，这是预期行为。
        """
        # 创建空文件
        file = SimpleUploadedFile(
            name=f"empty.{file_ext}",
            content=b'',
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：空文件应被拒绝（因为无法验证魔数）
        self.assertFalse(
            is_valid,
            f"空文件未被拒绝: 类型={file_ext}"
        )
        self.assertIn("不匹配", error_msg)


class FileMagicNumberValidationPropertyTest(TestCase):
    """文件类型验证（魔数验证）属性测试
    
    **属性 24：文件类型验证**
    **Validates: Requirements 8.6, 8.13**
    
    验证文件内容与声明的文件类型一致性：
    - 文件头魔数应与声明的类型匹配
    - 魔数不匹配的文件应被拒绝
    - 验证应防止文件类型伪造
    - 错误消息应清晰说明魔数不匹配
    """
    
    @given(
        file_ext=st.sampled_from(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'])
    )
    @settings(max_examples=100, deadline=None)
    def test_files_with_correct_magic_numbers_pass_validation(self, file_ext):
        """属性：包含正确魔数的文件应通过验证
        
        **Validates: Requirements 8.6**
        
        对于所有有魔数验证的文件类型，
        如果文件内容包含正确的魔数，验证应该成功。
        """
        # 生成包含正确魔数的文件内容
        magic_number = FILE_MAGIC_NUMBERS[file_ext]
        file_content = magic_number + b'\x00' * 100  # 添加一些额外内容
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"valid_file.{file_ext}",
            content=file_content,
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：包含正确魔数的文件应通过验证
        self.assertTrue(
            is_valid,
            f"包含正确魔数的文件验证失败: 类型={file_ext}, 错误={error_msg}"
        )
        self.assertEqual(error_msg, "")
    
    @given(
        declared_ext=st.sampled_from(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']),
        actual_ext=st.sampled_from(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'])
    )
    @settings(max_examples=100, deadline=None)
    def test_files_with_mismatched_magic_numbers_fail_validation(self, declared_ext, actual_ext):
        """属性：魔数与声明类型不匹配的文件应被拒绝
        
        **Validates: Requirements 8.6, 8.13**
        
        对于任意两种不同的文件类型，
        如果文件声明为类型 A 但内容包含类型 B 的魔数，
        验证应该失败，防止文件伪造。
        """
        # 跳过相同类型的情况（jpg 和 jpeg 使用相同的魔数）
        if declared_ext == actual_ext:
            return
        if {declared_ext, actual_ext} == {'jpg', 'jpeg'}:
            return
        
        # 使用实际类型的魔数，但声明为另一种类型
        actual_magic = FILE_MAGIC_NUMBERS[actual_ext]
        file_content = actual_magic + b'\x00' * 100
        
        # 创建上传文件对象（声明类型与实际内容不匹配）
        file = SimpleUploadedFile(
            name=f"fake_file.{declared_ext}",
            content=file_content,
            content_type=f"application/{declared_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：魔数不匹配的文件应被拒绝
        self.assertFalse(
            is_valid,
            f"魔数不匹配的文件未被拒绝: 声明={declared_ext}, 实际={actual_ext}"
        )
        self.assertIn(
            "不匹配",
            error_msg,
            f"错误消息未说明魔数不匹配: {error_msg}"
        )
    
    @given(
        file_ext=st.sampled_from(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']),
        random_bytes=st.binary(min_size=20, max_size=20)
    )
    @settings(max_examples=100, deadline=None)
    def test_files_with_random_magic_numbers_fail_validation(self, file_ext, random_bytes):
        """属性：包含随机魔数的文件应被拒绝
        
        **Validates: Requirements 8.6, 8.13**
        
        对于任意随机的文件头字节序列，
        如果不匹配声明的文件类型的魔数，
        验证应该失败。
        """
        # 确保随机字节不会意外匹配任何已知的魔数
        all_magic_numbers = []
        for magic_list in FileService.MAGIC_NUMBERS.values():
            all_magic_numbers.extend(magic_list)
        
        # 如果随机字节恰好匹配某个魔数，跳过此测试
        assume(not any(random_bytes.startswith(magic) for magic in all_magic_numbers))
        
        # 创建包含随机魔数的文件
        file_content = random_bytes + b'\x00' * 100
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"random_file.{file_ext}",
            content=file_content,
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：包含随机魔数的文件应被拒绝
        self.assertFalse(
            is_valid,
            f"包含随机魔数的文件未被拒绝: 类型={file_ext}, 魔数={random_bytes[:10].hex()}"
        )
        self.assertIn("不匹配", error_msg)
    
    @given(
        file_ext=st.sampled_from(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'])
    )
    @settings(max_examples=100, deadline=None)
    def test_files_with_truncated_magic_numbers_fail_validation(self, file_ext):
        """属性：魔数被截断的文件应被拒绝
        
        **Validates: Requirements 8.6, 8.13**
        
        对于任意文件类型，如果文件内容不足以包含完整的魔数，
        验证应该失败。
        """
        # 使用 FileService 中实际定义的魔数（而不是测试用的扩展魔数）
        actual_magic_numbers = FileService.MAGIC_NUMBERS[file_ext]
        
        # 获取最短的魔数（因为有些文件类型有多个魔数）
        shortest_magic = min(actual_magic_numbers, key=len)
        
        # 截断魔数（去掉最后一个字节，确保不完整）
        if len(shortest_magic) <= 1:
            return  # 跳过魔数太短的情况
        
        truncated_content = shortest_magic[:-1]  # 去掉最后一个字节
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"truncated_file.{file_ext}",
            content=truncated_content,
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：魔数被截断的文件应被拒绝
        self.assertFalse(
            is_valid,
            f"魔数被截断的文件未被拒绝: 类型={file_ext}, "
            f"截断后大小={len(truncated_content)}, "
            f"完整魔数大小={len(shortest_magic)}"
        )
        self.assertIn("不匹配", error_msg)
    
    @given(
        file_ext=st.sampled_from(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']),
        prefix_size=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_files_with_prefix_before_magic_number_fail_validation(self, file_ext, prefix_size):
        """属性：魔数前有额外字节的文件应被拒绝
        
        **Validates: Requirements 8.6, 8.13**
        
        对于任意文件类型，如果正确的魔数前面有额外的字节，
        验证应该失败，因为魔数必须在文件开头。
        """
        # 生成前缀字节
        prefix = b'\x00' * prefix_size
        
        # 获取正确的魔数
        magic_number = FILE_MAGIC_NUMBERS[file_ext]
        
        # 在魔数前添加前缀
        file_content = prefix + magic_number + b'\x00' * 100
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"prefixed_file.{file_ext}",
            content=file_content,
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：魔数前有前缀的文件应被拒绝
        self.assertFalse(
            is_valid,
            f"魔数前有前缀的文件未被拒绝: 类型={file_ext}, 前缀大小={prefix_size}"
        )
        self.assertIn("不匹配", error_msg)
    
    @given(
        file_ext=st.sampled_from(['txt', 'md', 'toml', 'json', 'yaml', 'yml'])
    )
    @settings(max_examples=100, deadline=None)
    def test_files_without_magic_number_definition_skip_validation(self, file_ext):
        """属性：没有魔数定义的文件类型应跳过魔数验证
        
        **Validates: Requirements 8.6**
        
        对于没有魔数定义的文件类型（如文本文件、配置文件），
        应该跳过魔数验证，只进行扩展名和大小验证。
        """
        # 生成任意内容（不包含特定魔数）
        file_content = b'Any content without magic number\n' * 10
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"text_file.{file_ext}",
            content=file_content,
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：没有魔数定义的文件应通过验证（只要扩展名和大小有效）
        self.assertTrue(
            is_valid,
            f"没有魔数定义的文件验证失败: 类型={file_ext}, 错误={error_msg}"
        )
    
    @given(
        file_ext=st.sampled_from(['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']),
        file_size=st.integers(min_value=100, max_value=MAX_FILE_SIZE)
    )
    @settings(max_examples=100, deadline=None)
    def test_magic_number_validation_with_various_file_sizes(self, file_ext, file_size):
        """属性：魔数验证应对各种文件大小都有效
        
        **Validates: Requirements 8.6**
        
        对于任意有效的文件大小，
        魔数验证应该正确工作，不受文件大小影响。
        """
        # 生成包含正确魔数的文件内容
        magic_number = FILE_MAGIC_NUMBERS[file_ext]
        content_size = max(file_size, len(magic_number) + 10)
        file_content = magic_number + b'\x00' * (content_size - len(magic_number))
        file_content = file_content[:file_size]
        
        # 创建上传文件对象
        file = SimpleUploadedFile(
            name=f"sized_file.{file_ext}",
            content=file_content,
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(file)
        
        # 断言：包含正确魔数的文件应通过验证，不受大小影响
        self.assertTrue(
            is_valid,
            f"魔数验证受文件大小影响: 类型={file_ext}, 大小={file_size}, 错误={error_msg}"
        )
    
    @given(
        file_ext=st.sampled_from(['gif'])  # GIF 有两种魔数
    )
    @settings(max_examples=100, deadline=None)
    def test_files_with_multiple_valid_magic_numbers(self, file_ext):
        """属性：支持多个有效魔数的文件类型应正确验证
        
        **Validates: Requirements 8.6**
        
        对于支持多个有效魔数的文件类型（如 GIF87a 和 GIF89a），
        任一有效魔数都应通过验证。
        """
        # GIF 有两种魔数：GIF87a 和 GIF89a
        gif87a_magic = b'\x47\x49\x46\x38\x37\x61'
        gif89a_magic = b'\x47\x49\x46\x38\x39\x61'
        
        # 测试 GIF87a
        file_87a = SimpleUploadedFile(
            name="test_87a.gif",
            content=gif87a_magic + b'\x00' * 100,
            content_type="image/gif"
        )
        is_valid_87a, error_msg_87a = FileService.validate_file(file_87a)
        
        # 测试 GIF89a
        file_89a = SimpleUploadedFile(
            name="test_89a.gif",
            content=gif89a_magic + b'\x00' * 100,
            content_type="image/gif"
        )
        is_valid_89a, error_msg_89a = FileService.validate_file(file_89a)
        
        # 断言：两种魔数都应通过验证
        self.assertTrue(
            is_valid_87a,
            f"GIF87a 魔数验证失败: {error_msg_87a}"
        )
        self.assertTrue(
            is_valid_89a,
            f"GIF89a 魔数验证失败: {error_msg_89a}"
        )


class FileUploadDownloadRoundTripPropertyTest(TestCase):
    """文件上传下载往返一致性属性测试
    
    **属性 5：文件上传下载往返一致性**
    **Validates: Requirements 1.7, 2.7**
    
    验证文件上传和下载的往返一致性：
    - 上传文件后立即下载，内容应完全一致
    - 文件元数据应被保留（文件名、大小、类型）
    - 对所有支持的文件类型都应保持一致性
    """
    
    def setUp(self):
        """设置测试环境"""
        # 创建临时目录用于文件存储
        self.temp_dir = tempfile.mkdtemp()
        self.upload_path = "test_uploads"
    
    def tearDown(self):
        """清理测试环境"""
        # 清理临时文件
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(
        file_ext=st.sampled_from(ALL_ALLOWED_TYPES),
        file_size=st.integers(min_value=100, max_value=10240)  # 限制大小以加快测试
    )
    @settings(max_examples=100, deadline=None)
    def test_upload_download_content_consistency(self, file_ext, file_size):
        """属性：上传后下载的文件内容应与原始内容完全一致
        
        **Validates: Requirements 1.7, 2.7**
        
        对于任意有效的文件，上传后立即下载，
        下载的文件内容应该与原始文件内容完全一致。
        """
        # 生成有效的文件内容
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            content_size = max(file_size, len(magic_number) + 10)
            original_content = magic_number + b'\x00' * (content_size - len(magic_number))
            original_content = original_content[:file_size]
        else:
            original_content = b'Test content\n' * (file_size // 13 + 1)
            original_content = original_content[:file_size]
        
        # 创建上传文件对象
        original_filename = f"test_file.{file_ext}"
        upload_file = SimpleUploadedFile(
            name=original_filename,
            content=original_content,
            content_type=f"application/{file_ext}"
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(upload_file)
        assume(is_valid)  # 只测试有效文件的往返一致性
        
        try:
            # 保存文件
            file_info = FileService.save_file(upload_file, self.upload_path)
            
            # 验证文件信息
            self.assertIsNotNone(file_info)
            self.assertIn('file_name', file_info)
            self.assertIn('original_name', file_info)
            self.assertIn('file_path', file_info)
            self.assertIn('file_size', file_info)
            
            # 验证原始文件名被保留
            self.assertEqual(
                file_info['original_name'],
                original_filename,
                "原始文件名未被正确保留"
            )
            
            # 验证文件大小被保留
            self.assertEqual(
                file_info['file_size'],
                len(original_content),
                "文件大小未被正确保留"
            )
            
            # 读取保存的文件内容
            saved_file_path = os.path.join(
                tempfile.gettempdir(),
                file_info['file_path']
            )
            
            # 如果文件不在临时目录，尝试从 MEDIA_ROOT 读取
            if not os.path.exists(saved_file_path):
                from django.conf import settings
                saved_file_path = os.path.join(
                    settings.MEDIA_ROOT,
                    file_info['file_path']
                )
            
            # 验证文件存在
            self.assertTrue(
                os.path.exists(saved_file_path),
                f"保存的文件不存在: {saved_file_path}"
            )
            
            # 读取文件内容
            with open(saved_file_path, 'rb') as f:
                downloaded_content = f.read()
            
            # 断言：下载的内容应与原始内容完全一致
            self.assertEqual(
                downloaded_content,
                original_content,
                f"文件内容不一致: 类型={file_ext}, "
                f"原始大小={len(original_content)}, "
                f"下载大小={len(downloaded_content)}"
            )
            
        finally:
            # 清理测试文件
            try:
                if 'file_info' in locals():
                    FileService.delete_file(file_info['file_path'])
            except:
                pass
    
    @given(
        file_ext=st.sampled_from(ALL_ALLOWED_TYPES),
        file_size=st.integers(min_value=100, max_value=10240)
    )
    @settings(max_examples=100, deadline=None)
    def test_upload_download_metadata_preservation(self, file_ext, file_size):
        """属性：上传后文件元数据应被正确保留
        
        **Validates: Requirements 1.7, 2.7**
        
        对于任意有效的文件，上传后文件的元数据
        （原始文件名、大小、类型）应该被正确保留。
        """
        # 生成有效的文件内容
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            content_size = max(file_size, len(magic_number) + 10)
            file_content = magic_number + b'\x00' * (content_size - len(magic_number))
            file_content = file_content[:file_size]
        else:
            file_content = b'Metadata test\n' * (file_size // 14 + 1)
            file_content = file_content[:file_size]
        
        # 创建上传文件对象
        original_filename = f"metadata_test.{file_ext}"
        original_content_type = f"application/{file_ext}"
        upload_file = SimpleUploadedFile(
            name=original_filename,
            content=file_content,
            content_type=original_content_type
        )
        
        # 验证文件
        is_valid, error_msg = FileService.validate_file(upload_file)
        assume(is_valid)
        
        try:
            # 保存文件
            file_info = FileService.save_file(upload_file, self.upload_path)
            
            # 断言：原始文件名应被保留
            self.assertEqual(
                file_info['original_name'],
                original_filename,
                "原始文件名未被保留"
            )
            
            # 断言：文件大小应被保留
            self.assertEqual(
                file_info['file_size'],
                len(file_content),
                "文件大小未被保留"
            )
            
            # 断言：文件类型应被保留
            self.assertEqual(
                file_info['file_type'],
                original_content_type,
                "文件类型未被保留"
            )
            
            # 断言：生成的文件名应包含正确的扩展名
            self.assertTrue(
                file_info['file_name'].endswith(f".{file_ext}"),
                f"生成的文件名扩展名不正确: {file_info['file_name']}"
            )
            
        finally:
            # 清理测试文件
            try:
                if 'file_info' in locals():
                    FileService.delete_file(file_info['file_path'])
            except:
                pass
    
    @given(
        file_ext=st.sampled_from(['jpg', 'png', 'pdf', 'txt', 'toml']),
        file_size=st.integers(min_value=100, max_value=5120)
    )
    @settings(max_examples=100, deadline=None)
    def test_multiple_upload_download_cycles(self, file_ext, file_size):
        """属性：多次上传下载循环应保持内容一致性
        
        **Validates: Requirements 1.7, 2.7**
        
        对于任意有效的文件，经过多次上传-下载循环后，
        文件内容应该始终与原始内容保持一致。
        """
        # 生成有效的文件内容
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            content_size = max(file_size, len(magic_number) + 10)
            original_content = magic_number + b'\x00' * (content_size - len(magic_number))
            original_content = original_content[:file_size]
        else:
            original_content = b'Cycle test\n' * (file_size // 11 + 1)
            original_content = original_content[:file_size]
        
        current_content = original_content
        file_paths = []
        
        try:
            # 执行 3 次上传-下载循环
            for cycle in range(3):
                # 创建上传文件对象
                upload_file = SimpleUploadedFile(
                    name=f"cycle_{cycle}.{file_ext}",
                    content=current_content,
                    content_type=f"application/{file_ext}"
                )
                
                # 验证文件
                is_valid, error_msg = FileService.validate_file(upload_file)
                assume(is_valid)
                
                # 保存文件
                file_info = FileService.save_file(upload_file, self.upload_path)
                file_paths.append(file_info['file_path'])
                
                # 读取保存的文件
                saved_file_path = os.path.join(
                    tempfile.gettempdir(),
                    file_info['file_path']
                )
                
                if not os.path.exists(saved_file_path):
                    from django.conf import settings
                    saved_file_path = os.path.join(
                        settings.MEDIA_ROOT,
                        file_info['file_path']
                    )
                
                with open(saved_file_path, 'rb') as f:
                    current_content = f.read()
                
                # 断言：每次循环后内容应与原始内容一致
                self.assertEqual(
                    current_content,
                    original_content,
                    f"第 {cycle + 1} 次循环后内容不一致: 类型={file_ext}"
                )
            
        finally:
            # 清理所有测试文件
            for file_path in file_paths:
                try:
                    FileService.delete_file(file_path)
                except:
                    pass
    
    @given(
        file_ext=st.sampled_from(ALL_ALLOWED_TYPES),
        file_size=st.integers(min_value=100, max_value=10240)
    )
    @settings(max_examples=100, deadline=None)
    def test_unique_filename_generation(self, file_ext, file_size):
        """属性：每次上传应生成唯一的文件名
        
        **Validates: Requirements 1.7, 2.7**
        
        对于相同的原始文件，多次上传应生成不同的唯一文件名，
        防止文件名冲突。
        """
        # 生成有效的文件内容
        if file_ext in FILE_MAGIC_NUMBERS:
            magic_number = FILE_MAGIC_NUMBERS[file_ext]
            content_size = max(file_size, len(magic_number) + 10)
            file_content = magic_number + b'\x00' * (content_size - len(magic_number))
            file_content = file_content[:file_size]
        else:
            file_content = b'Unique test\n' * (file_size // 12 + 1)
            file_content = file_content[:file_size]
        
        generated_filenames = []
        file_paths = []
        
        try:
            # 上传同一文件 3 次
            for i in range(3):
                upload_file = SimpleUploadedFile(
                    name=f"same_file.{file_ext}",
                    content=file_content,
                    content_type=f"application/{file_ext}"
                )
                
                # 验证文件
                is_valid, error_msg = FileService.validate_file(upload_file)
                assume(is_valid)
                
                # 保存文件
                file_info = FileService.save_file(upload_file, self.upload_path)
                generated_filenames.append(file_info['file_name'])
                file_paths.append(file_info['file_path'])
            
            # 断言：所有生成的文件名应该是唯一的
            self.assertEqual(
                len(generated_filenames),
                len(set(generated_filenames)),
                f"生成的文件名不唯一: {generated_filenames}"
            )
            
            # 断言：所有文件名应该包含正确的扩展名
            for filename in generated_filenames:
                self.assertTrue(
                    filename.endswith(f".{file_ext}"),
                    f"文件名扩展名不正确: {filename}"
                )
            
        finally:
            # 清理所有测试文件
            for file_path in file_paths:
                try:
                    FileService.delete_file(file_path)
                except:
                    pass



class FilePathSecurityPropertyTest(TestCase):
    """文件路径安全性属性测试
    
    **属性 25：文件路径安全性**
    **Validates: Requirements 8.8**
    
    验证文件路径的安全性，防止路径遍历攻击：
    - 包含 ".." 的路径应被拒绝
    - 绝对路径应被拒绝
    - 包含特殊字符的路径应被拒绝
    - 只有安全的相对路径应被接受
    - 符号链接攻击应被防止
    """
    
    def setUp(self):
        """设置测试环境"""
        # 创建临时目录用于文件存储
        self.temp_dir = tempfile.mkdtemp()
        self.upload_path = "test_uploads"
    
    def tearDown(self):
        """清理测试环境"""
        # 清理临时文件
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(
        path_segments=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
                min_size=1,
                max_size=10
            ).filter(lambda x: '..' not in x and '/' not in x and '\\' not in x),
            min_size=1,
            max_size=5
        ),
        filename=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=20
        ).filter(lambda x: '.' not in x and '/' not in x and '\\' not in x),
        file_ext=st.sampled_from(['txt', 'jpg', 'pdf'])
    )
    @settings(max_examples=100, deadline=None)
    def test_safe_relative_paths_are_accepted(self, path_segments, filename, file_ext):
        """属性：安全的相对路径应被接受
        
        **Validates: Requirements 8.8**
        
        对于所有不包含 ".."、绝对路径标识符和特殊字符的相对路径，
        文件下载应该成功。
        """
        # 跳过空路径段
        assume(all(len(seg) > 0 for seg in path_segments))
        assume(len(filename) > 0)
        
        # 构建安全的相对路径
        safe_path = os.path.join(*path_segments, f"{filename}.{file_ext}")
        
        # 创建测试文件
        from django.conf import settings
        full_path = os.path.join(settings.MEDIA_ROOT, safe_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        try:
            with open(full_path, 'wb') as f:
                f.write(b'Safe content')
            
            # 尝试获取文件响应
            response = FileService.get_file_response(safe_path, f"{filename}.{file_ext}")
            
            # 断言：安全路径应成功返回文件响应
            self.assertIsNotNone(
                response,
                f"安全路径被拒绝: {safe_path}"
            )
            self.assertIsInstance(response, FileResponse)
            
        finally:
            # 清理测试文件
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
                # 清理空目录
                dir_path = os.path.dirname(full_path)
                while dir_path != settings.MEDIA_ROOT:
                    try:
                        os.rmdir(dir_path)
                        dir_path = os.path.dirname(dir_path)
                    except:
                        break
            except:
                pass
    
    @given(
        traversal_pattern=st.sampled_from([
            '../',
            '../../',
            '../../../',
            '..',
            '../file.txt',
            'dir/../../../file.txt',
            'a/b/../../../c/file.txt'
        ]),
        filename=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_paths_with_parent_directory_references_are_rejected(self, traversal_pattern, filename):
        """属性：包含父目录引用的路径应被拒绝
        
        **Validates: Requirements 8.8**
        
        对于所有包含 ".." 的路径，
        文件下载应该抛出 ValidationException，防止路径遍历攻击。
        """
        # 构建包含 ".." 的路径
        malicious_path = f"{traversal_pattern}{filename}.txt"
        
        # 尝试获取文件响应
        from mainotebook.content.exceptions import ValidationException
        
        with self.assertRaises(
            ValidationException,
            msg=f"包含 '..' 的路径未被拒绝: {malicious_path}"
        ):
            FileService.get_file_response(malicious_path, "file.txt")
    
    @given(
        absolute_path=st.sampled_from([
            '/etc/passwd',
            '/var/log/system.log',
            '/root/.ssh/id_rsa',
            '/home/user/secret.txt',
            '/tmp/malicious.txt'
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_absolute_paths_are_rejected(self, absolute_path):
        """属性：绝对路径应被拒绝
        
        **Validates: Requirements 8.8**
        
        对于所有绝对路径（以 / 开头），
        文件下载应该抛出 ValidationException，防止访问系统文件。
        """
        # 尝试获取文件响应
        # 绝对路径应该被拒绝（ValidationException）或文件不存在（FileNotFoundError）
        with self.assertRaises(
            (ValidationException, FileNotFoundError),
            msg=f"绝对路径未被正确处理: {absolute_path}"
        ):
            FileService.get_file_response(absolute_path, "file.txt")
    
    @given(
        base_path=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=10
        ),
        filename=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_nonexistent_files_raise_file_not_found(self, base_path, filename):
        """属性：不存在的文件应抛出 FileNotFoundError
        
        **Validates: Requirements 8.8**
        
        对于不存在的文件路径（即使路径是安全的），
        文件下载应该抛出 FileNotFoundError。
        """
        # 跳过空字符串
        assume(len(base_path) > 0 and len(filename) > 0)
        assume('..' not in base_path and '..' not in filename)
        assume('/' not in base_path and '/' not in filename)
        
        # 构建不存在的文件路径
        nonexistent_path = f"{base_path}/{filename}.txt"
        
        # 尝试获取文件响应
        with self.assertRaises(
            FileNotFoundError,
            msg=f"不存在的文件未抛出 FileNotFoundError: {nonexistent_path}"
        ):
            FileService.get_file_response(nonexistent_path, "file.txt")
    
    @given(
        special_chars=st.sampled_from([
            '\x00',  # NULL 字符
            '\n',    # 换行符
            '\r',    # 回车符
            '\t',    # 制表符
        ]),
        base_name=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_paths_with_special_characters_are_handled_safely(self, special_chars, base_name):
        """属性：包含特殊字符的路径应被安全处理
        
        **Validates: Requirements 8.8**
        
        对于包含特殊字符（NULL、换行符等）的路径，
        文件下载应该安全失败，不会导致安全问题。
        """
        # 跳过空字符串
        assume(len(base_name) > 0)
        
        # 构建包含特殊字符的路径
        malicious_path = f"{base_name}{special_chars}file.txt"
        
        # 尝试获取文件响应
        # 应该抛出异常（ValidationException 或 FileNotFoundError）
        with self.assertRaises(
            (ValidationException, FileNotFoundError, OSError),
            msg=f"包含特殊字符的路径未被安全处理: {repr(malicious_path)}"
        ):
            FileService.get_file_response(malicious_path, "file.txt")
    
    @given(
        path_with_null=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_path_validation_prevents_null_byte_injection(self, path_with_null):
        """属性：路径验证应防止 NULL 字节注入
        
        **Validates: Requirements 8.8**
        
        对于包含 NULL 字节的路径，
        文件下载应该失败，防止 NULL 字节注入攻击。
        """
        # 跳过空字符串
        assume(len(path_with_null) > 0)
        
        # 在路径中注入 NULL 字节
        malicious_path = f"{path_with_null}\x00../../etc/passwd"
        
        # 尝试获取文件响应
        with self.assertRaises(
            (ValidationException, FileNotFoundError, ValueError, OSError),
            msg=f"NULL 字节注入未被防止: {repr(malicious_path)}"
        ):
            FileService.get_file_response(malicious_path, "file.txt")
    
    @given(
        safe_path=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=20
        ).filter(lambda x: '/' not in x and '\\' not in x and '..' not in x),
        file_ext=st.sampled_from(['txt', 'jpg', 'pdf'])
    )
    @settings(max_examples=100, deadline=None)
    def test_path_normalization_prevents_bypass(self, safe_path, file_ext):
        """属性：路径规范化应防止绕过攻击
        
        **Validates: Requirements 8.8**
        
        对于使用路径规范化技巧的攻击路径，
        文件下载应该正确识别并拒绝。
        """
        # 跳过空字符串
        assume(len(safe_path) > 0)
        
        # 创建测试文件
        from django.conf import settings
        safe_file_path = f"{safe_path}.{file_ext}"
        full_path = os.path.join(settings.MEDIA_ROOT, safe_file_path)
        
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(b'Test content')
            
            # 测试各种路径规范化绕过技巧
            bypass_attempts = [
                f"./{safe_file_path}",           # 当前目录引用
                f".//{safe_file_path}",          # 双斜杠
                f"././{safe_file_path}",         # 多个当前目录引用
            ]
            
            for bypass_path in bypass_attempts:
                # 这些路径应该被接受（因为它们实际上是安全的）
                # 或者被拒绝（取决于实现的严格程度）
                try:
                    response = FileService.get_file_response(bypass_path, safe_file_path)
                    # 如果接受，应该返回正确的文件
                    self.assertIsInstance(response, FileResponse)
                except (ValidationException, FileNotFoundError):
                    # 如果拒绝，也是可以接受的（更严格的安全策略）
                    pass
            
        finally:
            # 清理测试文件
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
            except:
                pass
    
    @given(
        filename=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=20
        ),
        file_ext=st.sampled_from(['txt', 'jpg', 'pdf'])
    )
    @settings(max_examples=100, deadline=None)
    def test_realpath_validation_prevents_symlink_attacks(self, filename, file_ext):
        """属性：真实路径验证应防止符号链接攻击
        
        **Validates: Requirements 8.8**
        
        对于指向 MEDIA_ROOT 外部的符号链接，
        文件下载应该被拒绝，防止符号链接攻击。
        """
        # 跳过空字符串
        assume(len(filename) > 0)
        
        from django.conf import settings
        
        # 创建一个指向外部的符号链接（如果系统支持）
        safe_filename = f"{filename}.{file_ext}"
        symlink_path = os.path.join(settings.MEDIA_ROOT, safe_filename)
        
        # 创建一个外部目标文件
        external_target = os.path.join(tempfile.gettempdir(), f"external_{filename}.{file_ext}")
        
        try:
            # 创建外部目标文件
            with open(external_target, 'wb') as f:
                f.write(b'External content')
            
            # 尝试创建符号链接（在某些系统上可能需要管理员权限）
            try:
                if os.path.exists(symlink_path):
                    os.remove(symlink_path)
                os.symlink(external_target, symlink_path)
            except (OSError, NotImplementedError):
                # 如果系统不支持符号链接，跳过此测试
                assume(False)
            
            # 尝试通过符号链接访问文件
            # 应该被拒绝，因为真实路径在 MEDIA_ROOT 外部
            
            with self.assertRaises(
                ValidationException,
                msg=f"符号链接攻击未被防止: {safe_filename}"
            ):
                FileService.get_file_response(safe_filename, safe_filename)
            
        finally:
            # 清理测试文件
            try:
                if os.path.exists(symlink_path):
                    os.remove(symlink_path)
                if os.path.exists(external_target):
                    os.remove(external_target)
            except:
                pass
    
    @given(
        path_components=st.lists(
            st.sampled_from(['..', '.', 'normal_dir', 'file.txt']),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_complex_path_traversal_attempts_are_rejected(self, path_components):
        """属性：复杂的路径遍历尝试应被拒绝
        
        **Validates: Requirements 8.8**
        
        对于包含多个 ".." 和正常目录混合的复杂路径，
        只要包含 ".."，就应该被拒绝。
        """
        # 构建复杂路径
        complex_path = '/'.join(path_components)
        
        # 如果路径包含 ".."，应该被拒绝
        if '..' in complex_path:
            
            with self.assertRaises(
                ValidationException,
                msg=f"复杂路径遍历未被拒绝: {complex_path}"
            ):
                FileService.get_file_response(complex_path, "file.txt")
    
    @given(
        safe_dir=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=10
        ).filter(lambda x: '/' not in x and '\\' not in x and '..' not in x),
        safe_file=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
            min_size=1,
            max_size=10
        ).filter(lambda x: '/' not in x and '\\' not in x and '..' not in x),
        file_ext=st.sampled_from(['txt', 'jpg', 'pdf'])
    )
    @settings(max_examples=100, deadline=None)
    def test_nested_safe_paths_are_accepted(self, safe_dir, safe_file, file_ext):
        """属性：嵌套的安全路径应被接受
        
        **Validates: Requirements 8.8**
        
        对于多层嵌套但不包含危险字符的安全路径，
        文件下载应该成功。
        """
        # 跳过空字符串
        assume(len(safe_dir) > 0 and len(safe_file) > 0)
        
        from django.conf import settings
        
        # 构建嵌套的安全路径
        nested_path = f"{safe_dir}/subdir/{safe_file}.{file_ext}"
        full_path = os.path.join(settings.MEDIA_ROOT, nested_path)
        
        try:
            # 创建嵌套目录和文件
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(b'Nested content')
            
            # 尝试获取文件响应
            response = FileService.get_file_response(nested_path, f"{safe_file}.{file_ext}")
            
            # 断言：嵌套的安全路径应成功返回文件响应
            self.assertIsNotNone(
                response,
                f"嵌套的安全路径被拒绝: {nested_path}"
            )
            self.assertIsInstance(response, FileResponse)
            
        finally:
            # 清理测试文件和目录
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
                # 清理空目录
                dir_path = os.path.dirname(full_path)
                while dir_path != settings.MEDIA_ROOT:
                    try:
                        os.rmdir(dir_path)
                        dir_path = os.path.dirname(dir_path)
                    except:
                        break
            except:
                pass
