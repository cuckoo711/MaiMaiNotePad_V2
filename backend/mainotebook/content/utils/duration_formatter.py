"""时长格式化工具

该模块提供时长格式化功能，将小时数或截止时间转换为可读的中文字符串。
"""
from datetime import datetime
from typing import Optional


class DurationFormatter:
    """时长格式化器
    
    提供将小时数和截止时间格式化为可读中文字符串的功能。
    
    示例：
        >>> DurationFormatter.format_hours(72)
        "3天"
        >>> DurationFormatter.format_hours(None)
        "永久"
        >>> from datetime import datetime, timedelta
        >>> future = datetime.now() + timedelta(days=2, hours=3)
        >>> DurationFormatter.format_remaining(future)
        "还剩2天3小时"
    """
    
    @staticmethod
    def format_hours(hours: Optional[int]) -> str:
        """将小时数格式化为可读字符串
        
        Args:
            hours: 小时数，None表示永久
            
        Returns:
            str: 格式化后的字符串（如"3天"、"2周"、"永久"）
            
        Examples:
            >>> DurationFormatter.format_hours(None)
            "永久"
            >>> DurationFormatter.format_hours(12)
            "12小时"
            >>> DurationFormatter.format_hours(48)
            "2天"
            >>> DurationFormatter.format_hours(336)
            "2周"
            >>> DurationFormatter.format_hours(1440)
            "2个月"
        """
        # 永久
        if hours is None:
            return "永久"
        
        # 小于24小时，显示小时
        if hours < 24:
            return f"{hours}小时"
        
        # 小于7天（168小时），显示天数
        if hours < 168:
            days = hours // 24
            return f"{days}天"
        
        # 小于30天（720小时），显示周数
        if hours < 720:
            weeks = hours // 168
            return f"{weeks}周"
        
        # 30天及以上，显示月数
        months = hours // 720
        return f"{months}个月"
    
    @staticmethod
    def format_remaining(until: Optional[datetime]) -> str:
        """格式化剩余时长
        
        Args:
            until: 截止时间，None表示永久
            
        Returns:
            str: 剩余时长描述（如"还剩2天3小时"、"永久"、"已过期"）
            
        Examples:
            >>> DurationFormatter.format_remaining(None)
            "永久"
            >>> from datetime import datetime, timedelta
            >>> past = datetime.now() - timedelta(hours=1)
            >>> DurationFormatter.format_remaining(past)
            "已过期"
            >>> future = datetime.now() + timedelta(days=2, hours=3)
            >>> # 返回类似 "还剩2天3小时"
        """
        # 永久
        if until is None:
            return "永久"
        
        # 计算剩余时间
        now = datetime.now()
        remaining = until - now
        
        # 已过期
        if remaining.total_seconds() <= 0:
            return "已过期"
        
        # 计算剩余的天数和小时数
        total_hours = int(remaining.total_seconds() // 3600)
        days = total_hours // 24
        hours = total_hours % 24
        
        # 格式化输出
        if days > 0:
            if hours > 0:
                return f"还剩{days}天{hours}小时"
            else:
                return f"还剩{days}天"
        else:
            return f"还剩{hours}小时"
