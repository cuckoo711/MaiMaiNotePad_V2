"""文件验证服务属性测试模块

使用 Hypothesis 进行基于属性的测试，验证人设卡配置文件验证服务的验证规则。

Feature: persona-card-upload
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from hypothesis import given, settings, strategies as st, assume
from hypothesis.extra.django import TestCase

from mainotebook.content.services.file_validation_service import FileValidationService


# 配置 Hypothesis
settings.register_profile("default", max_examples=100, deadline=None)
settings.load_profile("default")


class FileNameValidationPropertyTest(TestCase):
    """文件名验证属性测试
    
    Feature: persona-card-upload, Property 9: 文件名验证
    **Validates: Requirements 3.1**
    
    验证文件名验证规则：
    - 只有文件名为 "bot_config.toml" 的文件才能通过验证
    - 其他任何文件名都应被拒绝
    """
    
    @given(
        filename=st.text(
            alphabet=st.characters(
                whitelist_categories=('Ll', 'Lu', 'Nd', 'Pd'),
                whitelist_characters='_.'
            ),
            min_size=1,
            max_size=100
        ).filter(lambda x: x != "bot_config.toml")
    )
    @settings(max_examples=100, deadline=None)
    def test_property_9_only_bot_config_toml_passes(self, filename):
        """属性 9：文件名验证
        
        Feature: persona-card-upload, Property 9: 文件名验证
        **Validates: Requirements 3.1**
        
        对于任意上传的文件，只有文件名为 "bot_config.toml" 的文件才能通过验证。
        """
        # 跳过空文件名和只包含空格的文件名
        assume(len(filename.strip()) > 0)
        
        # 创建文件
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile(filename, content, content_type="text/plain")
        
        # 验证文件名
        is_valid, error_msg = FileValidationService.validate_filename(file)
        
        # 断言：非 bot_config.toml 的文件名应被拒绝
        self.assertFalse(
            is_valid,
            f"错误的文件名未被拒绝: {filename}"
        )
        self.assertIn("bot_config.toml", error_msg)
    
    @settings(max_examples=100, deadline=None)
    def test_property_9_bot_config_toml_always_passes(self):
        """属性 9：正确的文件名总是通过验证
        
        Feature: persona-card-upload, Property 9: 文件名验证
        **Validates: Requirements 3.1**
        
        文件名为 "bot_config.toml" 的文件应该总是通过文件名验证。
        """
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_filename(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")


class FileSizeValidationPropertyTest(TestCase):
    """文件大小验证属性测试
    
    Feature: persona-card-upload, Property 10: 文件大小验证
    **Validates: Requirements 3.2**
    
    验证文件大小验证规则：
    - 只有文件大小在 1KB 到 2MB 之间的文件才能通过验证
    - 小于 1KB 或大于 2MB 的文件应被拒绝
    """
    
    @given(
        file_size=st.integers(min_value=1024, max_value=2 * 1024 * 1024)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_10_valid_size_passes(self, file_size):
        """属性 10：有效大小的文件通过验证
        
        Feature: persona-card-upload, Property 10: 文件大小验证
        **Validates: Requirements 3.2**
        
        对于任意上传的文件，只有文件大小在 1KB 到 2MB 之间的文件才能通过验证。
        """
        # 创建指定大小的文件
        content = b'a' * file_size
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        # 验证文件大小
        is_valid, error_msg = FileValidationService.validate_file_size(file)
        
        # 断言：1KB-2MB 的文件应通过验证
        self.assertTrue(
            is_valid,
            f"有效大小的文件验证失败: 大小={file_size} 字节, 错误={error_msg}"
        )
        self.assertEqual(error_msg, "")
    
    @given(
        file_size=st.integers(min_value=0, max_value=1023)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_10_too_small_fails(self, file_size):
        """属性 10：过小的文件被拒绝
        
        Feature: persona-card-upload, Property 10: 文件大小验证
        **Validates: Requirements 3.2**
        
        对于任意小于 1KB 的文件，验证应该失败。
        """
        # 创建小于 1KB 的文件
        content = b'a' * file_size
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        # 验证文件大小
        is_valid, error_msg = FileValidationService.validate_file_size(file)
        
        # 断言：小于 1KB 的文件应被拒绝
        self.assertFalse(
            is_valid,
            f"过小的文件未被拒绝: 大小={file_size} 字节"
        )
        self.assertIn("1KB", error_msg)
    
    @given(
        file_size=st.integers(min_value=2 * 1024 * 1024 + 1, max_value=10 * 1024 * 1024)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_10_too_large_fails(self, file_size):
        """属性 10：过大的文件被拒绝
        
        Feature: persona-card-upload, Property 10: 文件大小验证
        **Validates: Requirements 3.2**
        
        对于任意大于 2MB 的文件，验证应该失败。
        """
        # 创建大于 2MB 的文件
        content = b'a' * file_size
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        # 验证文件大小
        is_valid, error_msg = FileValidationService.validate_file_size(file)
        
        # 断言：大于 2MB 的文件应被拒绝
        self.assertFalse(
            is_valid,
            f"过大的文件未被拒绝: 大小={file_size} 字节"
        )
        self.assertIn("2MB", error_msg)
    
    @settings(max_examples=100, deadline=None)
    def test_property_10_boundary_values(self):
        """属性 10：边界值测试
        
        Feature: persona-card-upload, Property 10: 文件大小验证
        **Validates: Requirements 3.2**
        
        测试边界值：1KB 和 2MB 应该通过验证。
        """
        # 测试最小边界：1KB
        content_min = b'a' * 1024
        file_min = SimpleUploadedFile("bot_config.toml", content_min, content_type="text/plain")
        is_valid_min, _ = FileValidationService.validate_file_size(file_min)
        self.assertTrue(is_valid_min, "1KB 边界值未通过验证")
        
        # 测试最大边界：2MB
        content_max = b'a' * (2 * 1024 * 1024)
        file_max = SimpleUploadedFile("bot_config.toml", content_max, content_type="text/plain")
        is_valid_max, _ = FileValidationService.validate_file_size(file_max)
        self.assertTrue(is_valid_max, "2MB 边界值未通过验证")


class MimeTypeValidationPropertyTest(TestCase):
    """MIME 类型验证属性测试
    
    Feature: persona-card-upload, Property 11: MIME 类型验证
    **Validates: Requirements 3.3**
    
    验证 MIME 类型验证规则：
    - 只有 MIME 类型为 text/plain 或 application/toml 的文件才能通过验证
    - 其他 MIME 类型应被拒绝
    """
    
    @given(
        mime_type=st.sampled_from(["text/plain", "application/toml"])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_valid_mime_types_pass(self, mime_type):
        """属性 11：有效的 MIME 类型通过验证
        
        Feature: persona-card-upload, Property 11: MIME 类型验证
        **Validates: Requirements 3.3**
        
        对于任意上传的文件，只有 MIME 类型为 text/plain 或 application/toml 的文件
        才能通过验证。
        """
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type=mime_type)
        
        # 验证 MIME 类型
        is_valid, error_msg = FileValidationService.validate_mime_type(file)
        
        # 断言：有效的 MIME 类型应通过验证
        self.assertTrue(
            is_valid,
            f"有效的 MIME 类型验证失败: {mime_type}, 错误={error_msg}"
        )
        self.assertEqual(error_msg, "")
    
    @given(
        mime_type=st.sampled_from([
            "application/json",
            "application/xml",
            "text/html",
            "text/xml",
            "application/octet-stream",
            "image/png",
            "image/jpeg"
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_invalid_mime_types_fail(self, mime_type):
        """属性 11：无效的 MIME 类型被拒绝
        
        Feature: persona-card-upload, Property 11: MIME 类型验证
        **Validates: Requirements 3.3**
        
        对于任意不是 text/plain 或 application/toml 的 MIME 类型，
        验证应该失败。
        """
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type=mime_type)
        
        # 验证 MIME 类型
        is_valid, error_msg = FileValidationService.validate_mime_type(file)
        
        # 断言：无效的 MIME 类型应被拒绝
        self.assertFalse(
            is_valid,
            f"无效的 MIME 类型未被拒绝: {mime_type}"
        )
        self.assertIn("MIME 类型", error_msg)
    
    @given(
        mime_type=st.sampled_from([
            "application/json",
            "application/xml",
            "text/html",
            "text/xml",
            "application/octet-stream"
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_common_invalid_mime_types_fail(self, mime_type):
        """属性 11：常见的无效 MIME 类型被拒绝
        
        Feature: persona-card-upload, Property 11: MIME 类型验证
        **Validates: Requirements 3.3**
        
        测试常见的但不被接受的 MIME 类型应该被拒绝。
        """
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type=mime_type)
        
        # 验证 MIME 类型
        is_valid, error_msg = FileValidationService.validate_mime_type(file)
        
        # 断言：这些 MIME 类型应被拒绝
        self.assertFalse(
            is_valid,
            f"常见的无效 MIME 类型未被拒绝: {mime_type}"
        )


class EncodingValidationPropertyTest(TestCase):
    """UTF-8 编码验证属性测试
    
    Feature: persona-card-upload, Property 12: UTF-8 编码验证
    **Validates: Requirements 3.4**
    
    验证文件编码验证规则：
    - 只有 UTF-8 编码的文件才能通过验证
    - 非 UTF-8 编码的文件应被拒绝
    """
    
    @given(
        text_content=st.text(
            alphabet=st.characters(
                whitelist_categories=('Ll', 'Lu', 'Nd', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=10,
            max_size=1000
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_utf8_encoded_files_pass(self, text_content):
        """属性 12：UTF-8 编码的文件通过验证
        
        Feature: persona-card-upload, Property 12: UTF-8 编码验证
        **Validates: Requirements 3.4**
        
        对于任意上传的文件，只有 UTF-8 编码的文件才能通过验证。
        """
        # 将文本编码为 UTF-8
        content = text_content.encode('utf-8')
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        # 验证编码
        is_valid, error_msg = FileValidationService.validate_encoding(file)
        
        # 断言：UTF-8 编码的文件应通过验证
        self.assertTrue(
            is_valid,
            f"UTF-8 编码的文件验证失败: 错误={error_msg}"
        )
        self.assertEqual(error_msg, "")
    
    @given(
        text_content=st.text(
            alphabet=st.characters(whitelist_categories=('Lo',)),  # 中文字符
            min_size=5,
            max_size=100
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_utf8_with_chinese_passes(self, text_content):
        """属性 12：包含中文的 UTF-8 文件通过验证
        
        Feature: persona-card-upload, Property 12: UTF-8 编码验证
        **Validates: Requirements 3.4**
        
        包含中文字符的 UTF-8 编码文件应该通过验证。
        """
        # 跳过空字符串
        assume(len(text_content.strip()) > 0)
        
        # 将中文文本编码为 UTF-8
        content = text_content.encode('utf-8')
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        # 验证编码
        is_valid, error_msg = FileValidationService.validate_encoding(file)
        
        # 断言：包含中文的 UTF-8 文件应通过验证
        self.assertTrue(
            is_valid,
            f"包含中文的 UTF-8 文件验证失败: 错误={error_msg}"
        )
    
    @given(
        text_content=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu')),
            min_size=5,
            max_size=100
        ).filter(lambda x: all(ord(c) < 128 for c in x))  # 只包含 ASCII 字符
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_ascii_is_valid_utf8(self, text_content):
        """属性 12：ASCII 是 UTF-8 的子集
        
        Feature: persona-card-upload, Property 12: UTF-8 编码验证
        **Validates: Requirements 3.4**
        
        ASCII 编码的文件应该通过 UTF-8 验证（因为 ASCII 是 UTF-8 的子集）。
        """
        # 跳过空字符串
        assume(len(text_content.strip()) > 0)
        
        # ASCII 文本可以直接编码为字节
        content = text_content.encode('ascii')
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        # 验证编码
        is_valid, error_msg = FileValidationService.validate_encoding(file)
        
        # 断言：ASCII 文件应通过 UTF-8 验证
        self.assertTrue(
            is_valid,
            f"ASCII 文件未通过 UTF-8 验证: 错误={error_msg}"
        )
    
    @given(
        encoding=st.sampled_from(['gbk', 'gb2312', 'big5', 'shift_jis', 'euc_kr'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_non_utf8_encodings_fail(self, encoding):
        """属性 12：非 UTF-8 编码的文件被拒绝
        
        Feature: persona-card-upload, Property 12: UTF-8 编码验证
        **Validates: Requirements 3.4**
        
        对于任意非 UTF-8 编码的文件，验证应该失败。
        """
        # 创建包含非 ASCII 字符的文本（确保编码差异可检测）
        text_content = "这是中文测试内容"
        
        try:
            # 使用非 UTF-8 编码
            content = text_content.encode(encoding)
            file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
            
            # 验证编码
            is_valid, error_msg = FileValidationService.validate_encoding(file)
            
            # 断言：非 UTF-8 编码的文件应被拒绝
            self.assertFalse(
                is_valid,
                f"非 UTF-8 编码的文件未被拒绝: 编码={encoding}"
            )
            self.assertIn("UTF-8", error_msg)
        except (UnicodeEncodeError, LookupError):
            # 如果编码不支持该字符，跳过此测试
            assume(False)


class IntegratedFileValidationPropertyTest(TestCase):
    """集成文件验证属性测试
    
    Feature: persona-card-upload, Properties 9-12: 综合文件验证
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    
    验证所有验证规则的集成：
    - 文件必须同时满足所有验证条件才能通过
    - 任一验证失败都应导致整体验证失败
    """
    
    @given(
        file_size=st.integers(min_value=1024, max_value=2 * 1024 * 1024),
        mime_type=st.sampled_from(["text/plain", "application/toml"]),
        text_content=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd', 'Zs')),
            min_size=10,
            max_size=500
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_all_valid_conditions_pass(self, file_size, mime_type, text_content):
        """属性：所有条件都满足时验证通过
        
        Feature: persona-card-upload, Properties 9-12
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
        
        当文件名、大小、MIME 类型和编码都满足要求时，
        验证应该通过。
        """
        # 创建符合所有要求的文件
        content = text_content.encode('utf-8')
        # 调整内容大小以匹配指定的 file_size
        if len(content) < file_size:
            content = content + b'a' * (file_size - len(content))
        else:
            content = content[:file_size]
        
        file = SimpleUploadedFile("bot_config.toml", content, content_type=mime_type)
        
        # 执行完整验证
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        # 断言：所有条件都满足时应通过验证
        self.assertTrue(
            is_valid,
            f"所有条件都满足但验证失败: "
            f"大小={file_size}, MIME={mime_type}, 错误={error_msg}"
        )
        self.assertEqual(error_msg, "")
    
    @given(
        file_size=st.integers(min_value=1024, max_value=2 * 1024 * 1024),
        mime_type=st.sampled_from(["text/plain", "application/toml"])
    )
    @settings(max_examples=100, deadline=None)
    def test_wrong_filename_fails_even_if_other_conditions_valid(self, file_size, mime_type):
        """属性：文件名错误时即使其他条件满足也应失败
        
        Feature: persona-card-upload, Properties 9-12
        **Validates: Requirements 3.1**
        
        即使文件大小、MIME 类型和编码都正确，
        如果文件名不是 bot_config.toml，验证也应该失败。
        """
        # 创建文件名错误但其他条件都正确的文件
        content = b'a' * file_size
        file = SimpleUploadedFile("wrong_name.toml", content, content_type=mime_type)
        
        # 执行完整验证
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        # 断言：文件名错误应导致验证失败
        self.assertFalse(
            is_valid,
            "文件名错误但验证通过"
        )
        self.assertIn("bot_config.toml", error_msg)
    
    @given(
        mime_type=st.sampled_from(["text/plain", "application/toml"])
    )
    @settings(max_examples=100, deadline=None)
    def test_wrong_size_fails_even_if_other_conditions_valid(self, mime_type):
        """属性：文件大小错误时即使其他条件满足也应失败
        
        Feature: persona-card-upload, Properties 9-12
        **Validates: Requirements 3.2**
        
        即使文件名、MIME 类型和编码都正确，
        如果文件大小不在 1KB-2MB 范围内，验证也应该失败。
        """
        # 创建文件大小错误但其他条件都正确的文件（500 字节）
        content = b'a' * 500
        file = SimpleUploadedFile("bot_config.toml", content, content_type=mime_type)
        
        # 执行完整验证
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        # 断言：文件大小错误应导致验证失败
        self.assertFalse(
            is_valid,
            "文件大小错误但验证通过"
        )
        self.assertIn("1KB", error_msg)
    
    @given(
        file_size=st.integers(min_value=1024, max_value=2 * 1024 * 1024)
    )
    @settings(max_examples=100, deadline=None)
    def test_wrong_mime_type_fails_even_if_other_conditions_valid(self, file_size):
        """属性：MIME 类型错误时即使其他条件满足也应失败
        
        Feature: persona-card-upload, Properties 9-12
        **Validates: Requirements 3.3**
        
        即使文件名、大小和编码都正确，
        如果 MIME 类型不是 text/plain 或 application/toml，验证也应该失败。
        """
        # 创建 MIME 类型错误但其他条件都正确的文件
        content = b'a' * file_size
        file = SimpleUploadedFile("bot_config.toml", content, content_type="application/json")
        
        # 执行完整验证
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        # 断言：MIME 类型错误应导致验证失败
        self.assertFalse(
            is_valid,
            "MIME 类型错误但验证通过"
        )
        self.assertIn("MIME 类型", error_msg)
    
    @given(
        file_size=st.integers(min_value=1024, max_value=2 * 1024 * 1024),
        mime_type=st.sampled_from(["text/plain", "application/toml"])
    )
    @settings(max_examples=100, deadline=None)
    def test_wrong_encoding_fails_even_if_other_conditions_valid(self, file_size, mime_type):
        """属性：编码错误时即使其他条件满足也应失败
        
        Feature: persona-card-upload, Properties 9-12
        **Validates: Requirements 3.4**
        
        即使文件名、大小和 MIME 类型都正确，
        如果编码不是 UTF-8，验证也应该失败。
        """
        # 创建编码错误但其他条件都正确的文件
        text_content = "这是中文"
        content = text_content.encode('gbk')
        # 填充到指定大小
        if len(content) < file_size:
            content = content + b'a' * (file_size - len(content))
        else:
            content = content[:file_size]
        
        file = SimpleUploadedFile("bot_config.toml", content, content_type=mime_type)
        
        # 执行完整验证
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        # 断言：编码错误应导致验证失败
        self.assertFalse(
            is_valid,
            "编码错误但验证通过"
        )
        self.assertIn("UTF-8", error_msg)
