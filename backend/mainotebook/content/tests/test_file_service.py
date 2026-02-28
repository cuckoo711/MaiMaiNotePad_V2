"""文件服务单元测试

测试文件服务的各项功能，包括：
- 文件验证（大小、类型、魔数）
- 文件保存和删除
- 文件下载响应生成
- 路径安全性验证
"""

import os
import tempfile
from io import BytesIO
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from ..services import FileService
from ..exceptions import ValidationException
from ..constants import MAX_FILE_SIZE


class FileServiceTest(TestCase):
    """文件服务单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        # 清理临时目录
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_validate_file_with_valid_image(self):
        """测试验证有效的图片文件"""
        # 创建一个有效的 PNG 文件
        png_header = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'
        png_content = png_header + b'\x00' * 100
        file = SimpleUploadedFile("test.png", png_content, content_type="image/png")
        
        is_valid, error_msg = FileService.validate_file(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_with_valid_jpg(self):
        """测试验证有效的 JPG 文件"""
        # 创建一个有效的 JPG 文件
        jpg_header = b'\xFF\xD8\xFF'
        jpg_content = jpg_header + b'\x00' * 100
        file = SimpleUploadedFile("test.jpg", jpg_content, content_type="image/jpeg")
        
        is_valid, error_msg = FileService.validate_file(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_with_valid_pdf(self):
        """测试验证有效的 PDF 文件"""
        # 创建一个有效的 PDF 文件
        pdf_header = b'\x25\x50\x44\x46'
        pdf_content = pdf_header + b'\x00' * 100
        file = SimpleUploadedFile("test.pdf", pdf_content, content_type="application/pdf")
        
        is_valid, error_msg = FileService.validate_file(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_with_text_file(self):
        """测试验证文本文件（无魔数验证）"""
        # 文本文件不需要魔数验证
        content = b'This is a test text file.'
        file = SimpleUploadedFile("test.txt", content, content_type="text/plain")
        
        is_valid, error_msg = FileService.validate_file(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_with_toml_file(self):
        """测试验证 TOML 配置文件"""
        content = b'version = "1.0.0"'
        file = SimpleUploadedFile("bot_config.toml", content, content_type="text/plain")
        
        is_valid, error_msg = FileService.validate_file(file)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_file_with_oversized_file(self):
        """测试验证超大文件应该失败"""
        # 创建一个超过大小限制的文件
        content = b'\x00' * (MAX_FILE_SIZE + 1)
        file = SimpleUploadedFile("large.png", content, content_type="image/png")
        
        is_valid, error_msg = FileService.validate_file(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件大小不能超过", error_msg)
    
    def test_validate_file_with_invalid_extension(self):
        """测试验证不支持的文件类型应该失败"""
        content = b'test content'
        file = SimpleUploadedFile("test.exe", content, content_type="application/x-msdownload")
        
        is_valid, error_msg = FileService.validate_file(file)
        
        self.assertFalse(is_valid)
        self.assertIn("不支持的文件类型", error_msg)
    
    def test_validate_file_with_mismatched_magic_number(self):
        """测试验证魔数不匹配的文件应该失败"""
        # 声明为 PNG 但内容不是 PNG
        fake_content = b'\x00\x00\x00\x00' + b'\x00' * 100
        file = SimpleUploadedFile("fake.png", fake_content, content_type="image/png")
        
        is_valid, error_msg = FileService.validate_file(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件内容与声明的文件类型不匹配", error_msg)
    
    def test_validate_file_without_extension(self):
        """测试验证没有扩展名的文件应该失败"""
        content = b'test content'
        file = SimpleUploadedFile("noextension", content, content_type="text/plain")
        
        is_valid, error_msg = FileService.validate_file(file)
        
        self.assertFalse(is_valid)
        self.assertIn("文件名必须包含扩展名", error_msg)
    
    def test_validate_file_with_allowed_extensions(self):
        """测试使用自定义允许扩展名列表验证文件"""
        content = b'test content'
        file = SimpleUploadedFile("test.txt", content, content_type="text/plain")
        
        # 只允许 txt 文件
        is_valid, error_msg = FileService.validate_file(file, allowed_extensions=['txt'])
        self.assertTrue(is_valid)
        
        # 不允许 txt 文件
        is_valid, error_msg = FileService.validate_file(file, allowed_extensions=['pdf'])
        self.assertFalse(is_valid)
        self.assertIn("不支持的文件类型", error_msg)
    
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_save_file(self):
        """测试保存文件"""
        content = b'test file content'
        file = SimpleUploadedFile("test.txt", content, content_type="text/plain")
        
        file_info = FileService.save_file(file, 'test_uploads')
        
        # 验证返回的文件信息
        self.assertIn('file_name', file_info)
        self.assertEqual(file_info['original_name'], 'test.txt')
        self.assertIn('test_uploads', file_info['file_path'])
        self.assertEqual(file_info['file_type'], 'text/plain')
        self.assertEqual(file_info['file_size'], len(content))
        
        # 验证文件确实被保存
        full_path = os.path.join(tempfile.gettempdir(), file_info['file_path'])
        self.assertTrue(os.path.exists(full_path))
        
        # 验证文件内容
        with open(full_path, 'rb') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, content)
        
        # 清理
        os.remove(full_path)
    
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_delete_file(self):
        """测试删除文件"""
        # 先创建一个文件
        content = b'test file content'
        file = SimpleUploadedFile("test.txt", content, content_type="text/plain")
        file_info = FileService.save_file(file, 'test_uploads')
        
        full_path = os.path.join(tempfile.gettempdir(), file_info['file_path'])
        self.assertTrue(os.path.exists(full_path))
        
        # 删除文件
        FileService.delete_file(file_info['file_path'])
        
        # 验证文件已被删除
        self.assertFalse(os.path.exists(full_path))
    
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_delete_nonexistent_file(self):
        """测试删除不存在的文件不会抛出异常"""
        # 删除不存在的文件应该不会抛出异常
        try:
            FileService.delete_file('nonexistent/file.txt')
        except Exception as e:
            self.fail(f"删除不存在的文件不应该抛出异常: {e}")
    
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_get_file_response(self):
        """测试获取文件下载响应"""
        # 先创建一个文件
        content = b'test file content'
        file = SimpleUploadedFile("test.txt", content, content_type="text/plain")
        file_info = FileService.save_file(file, 'test_uploads')
        
        # 获取文件响应
        response = FileService.get_file_response(file_info['file_path'], 'download.txt')
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('download.txt', response['Content-Disposition'])
        
        # 清理
        full_path = os.path.join(tempfile.gettempdir(), file_info['file_path'])
        os.remove(full_path)
    
    def test_get_file_response_with_path_traversal_attack(self):
        """测试路径遍历攻击应该被拒绝"""
        # 尝试使用 .. 进行路径遍历
        with self.assertRaises(ValidationException) as context:
            FileService.get_file_response('../../../etc/passwd', 'passwd')
        
        self.assertIn("非法的文件路径", str(context.exception.message))
    
    def test_get_file_response_with_absolute_path(self):
        """测试绝对路径访问应该被拒绝"""
        # 尝试使用绝对路径
        with self.assertRaises(ValidationException) as context:
            FileService.get_file_response('/etc/passwd', 'passwd')
        
        self.assertIn("非法的文件路径", str(context.exception.message))
    
    def test_get_file_response_with_nonexistent_file(self):
        """测试访问不存在的文件应该抛出异常"""
        with self.assertRaises(FileNotFoundError):
            FileService.get_file_response('nonexistent/file.txt', 'file.txt')
    
    def test_get_allowed_extensions_by_category(self):
        """测试根据类别获取允许的扩展名"""
        # 测试图片类别
        image_exts = FileService.get_allowed_extensions_by_category('image')
        self.assertIn('jpg', image_exts)
        self.assertIn('png', image_exts)
        
        # 测试文档类别
        doc_exts = FileService.get_allowed_extensions_by_category('document')
        self.assertIn('pdf', doc_exts)
        self.assertIn('txt', doc_exts)
        
        # 测试配置类别
        config_exts = FileService.get_allowed_extensions_by_category('config')
        self.assertIn('toml', config_exts)
        self.assertIn('json', config_exts)
        
        # 测试所有类别
        all_exts = FileService.get_allowed_extensions_by_category('all')
        self.assertIn('jpg', all_exts)
        self.assertIn('pdf', all_exts)
        self.assertIn('toml', all_exts)
    
    def test_get_allowed_extensions_with_invalid_category(self):
        """测试使用无效类别应该抛出异常"""
        with self.assertRaises(ValidationException) as context:
            FileService.get_allowed_extensions_by_category('invalid')
        
        self.assertIn("无效的文件类别", str(context.exception.message))
