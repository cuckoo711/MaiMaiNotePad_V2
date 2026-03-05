"""文件验证服务单元测试

测试人设卡配置文件验证服务的各项功能，包括：
- 文件名验证（必须为 bot_config.toml）
- 文件大小验证（1KB-2MB）
- MIME 类型验证（text/plain 或 application/toml）
- UTF-8 编码验证
"""

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from mainotebook.content.services.file_validation_service import FileValidationService


class FileValidationServiceTest(TestCase):
    """文件验证服务单元测试类"""
    
    def test_validate_filename_with_correct_name(self):
        """测试验证正确的文件名"""
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_filename(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_filename_with_incorrect_name(self):
        """测试验证错误的文件名"""
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("wrong_name.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_filename(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件名必须为 bot_config.toml", error_msg)
    
    def test_validate_filename_with_different_extension(self):
        """测试验证不同扩展名的文件名"""
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.txt", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_filename(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件名必须为 bot_config.toml", error_msg)
    
    def test_validate_file_size_within_range(self):
        """测试验证文件大小在 1KB-2MB 范围内"""
        # 创建一个 10KB 的文件
        content = b'a' * (10 * 1024)
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file_size(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_size_at_minimum(self):
        """测试验证文件大小刚好为 1KB"""
        # 创建一个刚好 1KB 的文件
        content = b'a' * 1024
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file_size(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_size_at_maximum(self):
        """测试验证文件大小刚好为 2MB"""
        # 创建一个刚好 2MB 的文件
        content = b'a' * (2 * 1024 * 1024)
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file_size(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_size_below_minimum(self):
        """测试验证文件大小小于 1KB"""
        # 创建一个小于 1KB 的文件（500 字节）
        content = b'a' * 500
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file_size(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件大小不能小于 1KB", error_msg)
    
    def test_validate_file_size_above_maximum(self):
        """测试验证文件大小大于 2MB"""
        # 创建一个大于 2MB 的文件（3MB）
        content = b'a' * (3 * 1024 * 1024)
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file_size(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件大小不能超过 2MB", error_msg)
    
    def test_validate_mime_type_text_plain(self):
        """测试验证 MIME 类型为 text/plain"""
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_mime_type(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_mime_type_application_toml(self):
        """测试验证 MIME 类型为 application/toml"""
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type="application/toml")
        
        is_valid, error_msg = FileValidationService.validate_mime_type(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_mime_type_invalid(self):
        """测试验证无效的 MIME 类型"""
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type="application/json")
        
        is_valid, error_msg = FileValidationService.validate_mime_type(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件 MIME 类型必须为", error_msg)
        self.assertIn("application/json", error_msg)
    
    def test_validate_encoding_utf8(self):
        """测试验证 UTF-8 编码的文件"""
        # 创建包含中文的 UTF-8 编码文件
        content = 'version = "1.0.0"\n# 这是中文注释'.encode('utf-8')
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_encoding(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_encoding_non_utf8(self):
        """测试验证非 UTF-8 编码的文件"""
        # 创建 GBK 编码的文件
        content = '这是中文'.encode('gbk')
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_encoding(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件编码必须为 UTF-8", error_msg)
    
    def test_validate_encoding_ascii(self):
        """测试验证 ASCII 编码的文件（ASCII 是 UTF-8 的子集）"""
        # ASCII 文件应该能通过 UTF-8 验证
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_encoding(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_all_checks_pass(self):
        """测试所有验证都通过"""
        # 创建一个符合所有要求的文件（至少 1KB）
        content = 'version = "1.0.0"\n# 中文注释\n'
        # 填充到 1KB 以上
        content = content + 'a' * (1024 - len(content.encode('utf-8')))
        content = content.encode('utf-8')
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_fails_on_filename(self):
        """测试文件名验证失败时立即返回"""
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("wrong_name.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件名必须为 bot_config.toml", error_msg)
    
    def test_validate_file_fails_on_size(self):
        """测试文件大小验证失败时立即返回"""
        # 创建一个文件名正确但大小过小的文件
        content = b'a' * 500
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件大小不能小于 1KB", error_msg)
    
    def test_validate_file_fails_on_mime_type(self):
        """测试 MIME 类型验证失败时立即返回"""
        # 创建一个文件名和大小正确但 MIME 类型错误的文件
        content = b'a' * (10 * 1024)
        file = SimpleUploadedFile("bot_config.toml", content, content_type="application/json")
        
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件 MIME 类型必须为", error_msg)
    
    def test_validate_file_fails_on_encoding(self):
        """测试编码验证失败时立即返回"""
        # 创建一个文件名、大小、MIME 类型都正确但编码错误的文件
        content = '这是中文'.encode('gbk')
        # 填充到 1KB 以上
        content = content + b'a' * (1024 - len(content))
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件编码必须为 UTF-8", error_msg)
    
    def test_validate_file_with_empty_file(self):
        """测试验证空文件"""
        content = b''
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件大小不能小于 1KB", error_msg)
    
    def test_validate_file_with_large_valid_file(self):
        """测试验证接近 2MB 的有效文件"""
        # 创建一个接近 2MB 的有效文件（1.9MB）
        content = 'a' * (1900 * 1024)
        content = content.encode('utf-8')
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileValidationService.validate_file(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
