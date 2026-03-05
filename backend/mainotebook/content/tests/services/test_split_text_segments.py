"""文本分段逻辑单元测试

测试 AutoReviewService._split_text_segments 方法的核心行为：
- 短文本直接返回
- 按段落分割
- 超长段落按固定长度切分
- 拼接还原等于原文
- 每段长度 <= MAX_SEGMENT_LENGTH
"""

import pytest

from mainotebook.content.services.auto_review_service import AutoReviewService


MAX_LEN = AutoReviewService.MAX_SEGMENT_LENGTH


class TestSplitTextSegmentsShortText:
    """短文本（<= MAX_SEGMENT_LENGTH）直接返回"""

    def test_empty_string(self):
        """空字符串返回单元素列表"""
        result = AutoReviewService._split_text_segments("")
        assert result == [""]

    def test_short_text(self):
        """短文本直接返回原文"""
        text = "这是一段短文本"
        result = AutoReviewService._split_text_segments(text)
        assert result == [text]

    def test_exact_max_length(self):
        """恰好等于 MAX_SEGMENT_LENGTH 的文本直接返回"""
        text = "a" * MAX_LEN
        result = AutoReviewService._split_text_segments(text)
        assert result == [text]


class TestSplitTextSegmentsParagraphs:
    """按段落（\\n\\n）分割"""

    def test_two_short_paragraphs(self):
        """两个短段落，分隔符保留在前一段末尾"""
        p1 = "a" * 100
        p2 = "b" * 100
        text = p1 + "\n\n" + p2
        # 总长度需要超过 MAX_LEN 才会触发分段
        # 这里总长度 202，远小于 4000，所以直接返回
        result = AutoReviewService._split_text_segments(text)
        assert result == [text]

    def test_paragraphs_exceeding_max(self):
        """多个段落总长度超过 MAX_SEGMENT_LENGTH，按段落分割"""
        p1 = "a" * 2000
        p2 = "b" * 2000
        p3 = "c" * 2000
        text = p1 + "\n\n" + p2 + "\n\n" + p3
        result = AutoReviewService._split_text_segments(text)
        # 验证拼接还原
        assert "".join(result) == text
        # 验证每段 <= MAX_LEN
        for seg in result:
            assert len(seg) <= MAX_LEN

    def test_concatenation_preserves_separators(self):
        """分段拼接后保留所有 \\n\\n 分隔符"""
        paragraphs = ["段落" + str(i) * 1000 for i in range(6)]
        text = "\n\n".join(paragraphs)
        result = AutoReviewService._split_text_segments(text)
        assert "".join(result) == text


class TestSplitTextSegmentsLongParagraph:
    """超长段落按固定长度切分"""

    def test_single_long_paragraph(self):
        """单个超长段落按 MAX_SEGMENT_LENGTH 切分"""
        text = "x" * (MAX_LEN * 3 + 500)
        result = AutoReviewService._split_text_segments(text)
        assert "".join(result) == text
        for seg in result:
            assert len(seg) <= MAX_LEN
        # 应该有 4 段
        assert len(result) == 4

    def test_mixed_short_and_long_paragraphs(self):
        """混合短段落和超长段落"""
        short_p = "短段落内容"
        long_p = "长" * (MAX_LEN * 2 + 100)
        text = short_p + "\n\n" + long_p + "\n\n" + short_p
        result = AutoReviewService._split_text_segments(text)
        assert "".join(result) == text
        for seg in result:
            assert len(seg) <= MAX_LEN


class TestSplitTextSegmentsEdgeCases:
    """边界情况"""

    def test_text_with_only_separators(self):
        """仅包含分隔符的超长文本"""
        text = "\n\n" * (MAX_LEN + 1)
        result = AutoReviewService._split_text_segments(text)
        assert "".join(result) == text
        for seg in result:
            assert len(seg) <= MAX_LEN

    def test_consecutive_separators(self):
        """连续多个 \\n\\n 分隔符"""
        p1 = "a" * 2000
        p2 = "b" * 2000
        text = p1 + "\n\n\n\n" + p2
        result = AutoReviewService._split_text_segments(text)
        assert "".join(result) == text

    def test_text_just_over_max(self):
        """文本长度刚好超过 MAX_SEGMENT_LENGTH 一个字符"""
        text = "a" * (MAX_LEN + 1)
        result = AutoReviewService._split_text_segments(text)
        assert "".join(result) == text
        assert len(result) == 2
        assert len(result[0]) == MAX_LEN
        assert len(result[1]) == 1
