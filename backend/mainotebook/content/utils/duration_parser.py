"""时长解析工具

该模块提供时长字符串解析功能，支持将"3d"、"2w"等格式转换为小时数。
"""
import re
from datetime import datetime, timedelta
from typing import Optional


class DurationParser:
    """时长解析器
    
    支持的格式：
    - h: 小时 (1h = 1小时)
    - d: 天 (1d = 24小时)
    - w: 周 (1w = 168小时)
    - m: 月 (1m = 720小时，按30天计算)
    - permanent: 永久
    
    示例：
        >>> DurationParser.parse("3d")
        72
        >>> DurationParser.parse("2w")
        336
        >>> DurationParser.parse("permanent")
        None
    """
    
    # 单位转换常量
    HOUR = 1
    DAY = 24
    WEEK = 168  # 7 * 24
    MONTH = 720  # 30 * 24
    
    # 正则表达式：匹配"数字+单位"格式
    DURATION_PATTERN = re.compile(r'^(\d+)([hdwm])$')
    
    @staticmethod
    def parse(duration: str) -> Optional[int]:
        """解析时长字符串为小时数
        
        Args:
            duration: 时长字符串（如"3d"、"2w"、"permanent"）
            
        Returns:
            Optional[int]: 小时数，永久返回None
            
        Raises:
            ValueError: 格式无效时抛出异常
            
        Examples:
            >>> DurationParser.parse("3h")
            3
            >>> DurationParser.parse("2d")
            48
            >>> DurationParser.parse("1w")
            168
            >>> DurationParser.parse("1m")
            720
            >>> DurationParser.parse("permanent")
            None
        """
        if not duration:
            raise ValueError("时长格式无效：时长不能为空")
        
        # 处理永久禁言
        if duration.lower() == 'permanent':
            return None
        
        # 使用正则表达式解析
        match = DurationParser.DURATION_PATTERN.match(duration.lower())
        if not match:
            raise ValueError(
                f"时长格式无效：'{duration}'。"
                f"支持的格式：数字+单位（如3h、2d、1w、1m）或 'permanent'"
            )
        
        # 提取数字和单位
        number = int(match.group(1))
        unit = match.group(2)
        
        # 根据单位计算小时数
        unit_multipliers = {
            'h': DurationParser.HOUR,
            'd': DurationParser.DAY,
            'w': DurationParser.WEEK,
            'm': DurationParser.MONTH,
        }
        
        hours = number * unit_multipliers[unit]
        return hours
    
    @staticmethod
    def to_datetime(duration: str) -> Optional[datetime]:
        """解析时长字符串为截止时间
        
        Args:
            duration: 时长字符串（如"3d"、"2w"、"permanent"）
            
        Returns:
            Optional[datetime]: 截止时间，永久返回None
            
        Raises:
            ValueError: 格式无效时抛出异常
            
        Examples:
            >>> from datetime import datetime, timedelta
            >>> result = DurationParser.to_datetime("24h")
            >>> # result 应该约等于 datetime.now() + timedelta(hours=24)
            >>> DurationParser.to_datetime("permanent")
            None
        """
        hours = DurationParser.parse(duration)
        
        # 永久禁言返回None
        if hours is None:
            return None
        
        # 计算截止时间
        return datetime.now() + timedelta(hours=hours)
