"""JSON 辅助解析工具

处理 AI 模型返回的各种非标准 JSON 格式，包括：
- markdown 代码块包裹（```json ... ```）
- 前后有多余文字
- 多个 JSON 对象混在一起（只取第一个）
- 带 BOM 或不可见字符
"""

import json
import re
from typing import Any, Optional


def extract_json(text: str) -> Any:
    """从文本中提取并解析 JSON 对象

    按优先级依次尝试以下策略：
    1. 直接解析（标准 JSON）
    2. 去除 markdown 代码块标记后解析
    3. 用正则提取第一个 { ... } 块后解析
    4. 全部失败则抛出 ValueError

    Args:
        text: 可能包含 JSON 的原始文本

    Returns:
        Any: 解析后的 Python 对象（通常是 dict）

    Raises:
        ValueError: 所有策略均无法提取有效 JSON 时
    """
    if not text or not text.strip():
        raise ValueError("输入文本为空")

    # 清理不可见字符和 BOM
    cleaned = text.strip().lstrip('\ufeff')

    # 策略 1：直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 策略 2：去除 markdown 代码块标记
    # 匹配 ```json ... ``` 或 ``` ... ```
    code_block_pattern = re.compile(
        r'```(?:json)?\s*\n?(.*?)\n?\s*```',
        re.DOTALL,
    )
    match = code_block_pattern.search(cleaned)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 策略 3：提取第一个完整的 { ... } JSON 对象
    brace_json = _extract_first_brace_block(cleaned)
    if brace_json:
        try:
            return json.loads(brace_json)
        except json.JSONDecodeError:
            pass

    # 全部失败
    raise ValueError(f"无法从文本中提取有效 JSON: {cleaned[:200]}")


def _extract_first_brace_block(text: str) -> Optional[str]:
    """从文本中提取第一个配对的花括号块

    使用计数器匹配花括号层级，处理字符串内的转义花括号。

    Args:
        text: 待提取的文本

    Returns:
        Optional[str]: 提取到的 JSON 字符串，未找到则返回 None
    """
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None
