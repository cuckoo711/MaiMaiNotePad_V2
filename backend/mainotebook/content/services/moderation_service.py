"""
AI 内容审核服务模块

基于硅基流动 Qwen/Qwen2.5-7B-Instruct 模型的内容安全审核服务。
支持色情、涉政、辱骂等违规内容的检测。
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_api_key() -> Optional[str]:
    """获取 API Key
    
    优先级：
    1. 环境变量 SILICONFLOW_API_KEY
    2. Django settings 中的 SILICONFLOW_API_KEY
    
    Returns:
        str: API Key，如果未配置则返回 None
    """
    # 优先从环境变量读取
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if api_key:
        return api_key
    
    # 尝试从 Django settings 读取
    try:
        from django.conf import settings
        return getattr(settings, 'SILICONFLOW_API_KEY', None)
    except Exception:
        return None


class ModerationService:
    """AI 内容审核服务类"""

    # 基础系统提示词模板
    BASE_SYSTEM_PROMPT = """你是一个专业的内容安全审核员，负责判断用户生成的文本是否包含违规信息。

审核范围：
1. 色情（porn）：仅限露骨的性行为描写、色情词汇，不包含软色情或性暗示
2. 涉政（politics）：仅限中国国内政治敏感内容，包括对领导人的负面评价、敏感历史事件、领土分裂言论等
3. 辱骂（abuse）：仅限粗口脏话，不包含隐晦的人身攻击或歧视性言论

判断逻辑：
- 明确违规（置信度 > 0.8）：文本明显包含上述任一违规类型
- 明确正常（置信度 < 0.4）：文本完全正常，无任何违规迹象
- 不确定（置信度 0.4 ~ 0.8）：文本疑似违规但无法确定，如隐晦表达、谐音、反讽或边缘内容

{context_specific_rules}

输出格式（必须是合法的 JSON，不含任何额外文字）：
{{
  "decision": "true/false/unknown",
  "confidence": 0.0-1.0,
  "violation_types": ["porn", "politics", "abuse"]
}}

字段说明：
- decision: "true"（通过）、"false"（拒绝）或 "unknown"（不确定）
- confidence: 0~1 的浮点数，表示内容违规的置信度，越接近 1 越确信违规
- violation_types: 违规类型数组，若 decision 为 "true" 则为空数组

示例：

输入：[包含露骨性描写的文本]
输出：{{"decision": "false", "confidence": 0.95, "violation_types": ["porn"]}}

输入：[包含对领导人侮辱性称呼的文本]
输出：{{"decision": "false", "confidence": 0.92, "violation_types": ["politics"]}}

输入：[包含粗口的句子]
输出：{{"decision": "false", "confidence": 0.88, "violation_types": ["abuse"]}}

输入：[正常的日常对话]
输出：{{"decision": "true", "confidence": 0.15, "violation_types": []}}

输入：[使用谐音或隐晦表达的疑似违规内容]
输出：{{"decision": "unknown", "confidence": 0.65, "violation_types": ["politics"]}}

输入：[同时包含多种违规类型的文本]
输出：{{"decision": "false", "confidence": 0.93, "violation_types": ["porn", "abuse"]}}

请严格按照上述格式输出，不要添加任何解释或额外文字。"""

    # 不同文本类型的特定审核规则
    CONTEXT_RULES = {
        "comment": """
特定审核规则（评论）：
- 评论通常较短，需要特别关注辱骂和人身攻击
- 对于争论性评论，区分正常辩论和恶意攻击
- 允许合理的批评和不同意见，但不允许粗口和人身攻击
- 评论中的反讽和讽刺需要结合上下文判断，如果明显带有恶意则标记为违规
- 对于技术讨论、学术交流等专业评论，应更加宽容""",
        
        "post": """
特定审核规则（帖子/文章）：
- 帖子内容较长，需要综合评估整体倾向
- 允许讨论敏感话题，但不允许传播极端观点或煽动性言论
- 对于学术性、科普性内容，即使涉及敏感话题也应更加宽容
- 重点关注是否有系统性的违规内容传播意图
- 标题党、夸张表达不等同于违规，需要看实际内容""",
        
        "title": """
特定审核规则（标题）：
- 标题通常很短，需要更严格的审核标准
- 标题是内容的门面，违规标题影响更大
- 对于明显的标题党、低俗标题要严格把关
- 允许使用吸引眼球的表达，但不允许违规词汇
- 技术性标题、学术性标题应更加宽容""",
        
        "content": """
特定审核规则（内容正文）：
- 内容正文是核心部分，需要全面评估
- 允许引用违规内容用于批判、教育目的，需要看整体意图
- 对于创作性内容（小说、剧本等），需要区分虚构和现实
- 重点关注是否有传播违规信息的主观意图
- 学术研究、新闻报道等专业内容应更加宽容""",

        "knowledge": """
特定审核规则（知识库）：
- 知识库内容通常为教育性、参考性资料，应更加宽容
- 允许包含学术性讨论、历史事件描述、科学知识等
- 重点关注是否有恶意篡改知识、传播虚假信息的意图
- 对于引用性内容（如百科、教材摘录），即使涉及敏感话题也应宽容
- 不允许以知识库为名传播违规内容""",

        "persona": """
特定审核规则（人设卡）：
- 人设卡描述虚构角色的性格、背景、对话风格
- 允许角色设定中包含复杂的性格特征和背景故事
- 重点关注是否有引导 AI 生成违规内容的意图
- 不允许设定明确违规的角色行为（如色情角色、暴力角色）
- 对于文学性、创作性的角色描述应更加宽容
- 角色的对话示例需要审核是否包含违规内容""",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.siliconflow.cn/v1"
    ):
        """初始化审核服务
        
        Args:
            api_key: 硅基流动 API Key，若为 None 则自动从环境变量或 Django settings 读取
            base_url: API 基础地址
            
        Raises:
            ValueError: 当未找到 API Key 时
        """
        self.api_key = api_key or _get_api_key()
        if not self.api_key:
            raise ValueError(
                "未找到 SILICONFLOW_API_KEY，请在以下任一位置配置：\n"
                "1. 环境变量: export SILICONFLOW_API_KEY=your_key\n"
                "2. conf/env.py: SILICONFLOW_API_KEY = 'your_key'"
            )

        self.base_url = base_url
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.model = "Qwen/Qwen2.5-7B-Instruct"  # 硅基流动免费模型

        logger.info(f"ModerationService 初始化成功，使用模型: {self.model}")
    def _get_system_prompt(self, text_type: str) -> str:
        """根据文本类型获取对应的系统提示词

        Args:
            text_type: 文本类型（comment/post/title/content）

        Returns:
            str: 完整的系统提示词
        """
        # 获取特定规则，如果类型不存在则使用 content 的规则
        context_rules = self.CONTEXT_RULES.get(text_type, self.CONTEXT_RULES["content"])

        # 组合基础提示词和特定规则
        return self.BASE_SYSTEM_PROMPT.format(context_specific_rules=context_rules)


    def moderate(
        self,
        text: str,
        text_type: str = "comment",
        temperature: float = 0.1,
        max_tokens: int = 100
    ) -> Dict[str, Any]:
        """对文本进行内容审核
        
        Args:
            text: 待审核的文本内容
            text_type: 文本类型（comment/post/title/content），帮助模型更好理解上下文
            temperature: 模型温度参数，越低输出越稳定
            max_tokens: 最大输出 token 数
            
        Returns:
            dict: 审核结果字典，包含以下字段：
                - decision: str, "true"（通过）/"false"（拒绝）/"unknown"（不确定）
                - confidence: float, 0~1，违规置信度
                - violation_types: List[str], 违规类型列表
        """
        if not text or not text.strip():
            logger.warning("输入文本为空，返回默认通过结果")
            return {"decision": "true", "confidence": 0.0, "violation_types": []}

        # 构建用户消息，包含文本类型信息
        user_message = f"文本类型：{text_type}\n待审核内容：{text}"

        try:
            # 根据文本类型获取对应的系统提示词
            system_prompt = self._get_system_prompt(text_type)
            
            # 调用模型进行审核
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            # 提取模型输出
            output = response.choices[0].message.content.strip()
            logger.debug(f"模型原始输出: {output}")

            # 解析 JSON 结果
            result = json.loads(output)

            # 验证结果格式
            if not self._validate_result(result):
                logger.error(f"模型输出格式不符合要求: {result}")
                return self._get_default_unknown_result()

            logger.info(
                f"审核完成 - 决策: {result['decision']}, "
                f"置信度: {result['confidence']}, "
                f"违规类型: {result['violation_types']}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(
                f"JSON 解析失败: {e}, "
                f"原始输出: {output if 'output' in locals() else 'N/A'}"
            )
            return self._get_default_unknown_result()

        except Exception as e:
            logger.error(f"审核过程发生异常: {e}", exc_info=True)
            return self._get_default_unknown_result()

    def _validate_result(self, result: dict) -> bool:
        """验证审核结果格式是否正确
        
        Args:
            result: 待验证的结果字典
            
        Returns:
            bool: 格式是否正确
        """
        if not isinstance(result, dict):
            return False

        # 检查必需字段
        if "decision" not in result or "confidence" not in result or "violation_types" not in result:
            return False

        # 检查字段类型和取值
        if result["decision"] not in ["true", "false", "unknown"]:
            return False

        if not isinstance(result["confidence"], (int, float)) or not (0 <= result["confidence"] <= 1):
            return False

        if not isinstance(result["violation_types"], list):
            return False

        # 检查违规类型是否合法
        valid_types = {"porn", "politics", "abuse"}
        if not all(vtype in valid_types for vtype in result["violation_types"]):
            return False

        return True

    def _get_default_unknown_result(self) -> Dict[str, Any]:
        """获取默认的"不确定"结果（用于异常情况）
        
        Returns:
            dict: 默认结果字典
        """
        return {"decision": "unknown", "confidence": 0.5, "violation_types": []}


# 全局服务实例（延迟初始化）
_moderation_service: Optional[ModerationService] = None


def get_moderation_service() -> ModerationService:
    """获取全局审核服务实例（单例模式）
    
    Returns:
        ModerationService: 审核服务实例
        
    Raises:
        ValueError: 当未配置 API Key 时
    """
    global _moderation_service
    if _moderation_service is None:
        _moderation_service = ModerationService()
    return _moderation_service
