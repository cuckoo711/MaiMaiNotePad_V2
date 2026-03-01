"""AI 内容审核服务模块

基于硅基流动免费模型的内容安全审核服务。
支持色情、涉政、辱骂等违规内容的检测。
使用多模型负载均衡应对单模型 RPM/TPM 限制（RPM=1000, TPM=50000）。
"""

import json
import logging
import os
import threading
import time as time_module
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_api_key() -> Optional[str]:
    """获取 API Key

    优先级：
    1. 环境变量 SILICONFLOW_API_KEY
    2. Django settings 中的 SILICONFLOW_API_KEY

    Returns:
        Optional[str]: API Key，如果未配置则返回 None
    """
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if api_key:
        return api_key

    try:
        from django.conf import settings
        return getattr(settings, 'SILICONFLOW_API_KEY', None)
    except Exception:
        return None


class ModelPool:
    """模型池管理器

    从数据库 AIModel 表读取启用的模型配置，按优先级排序后进行轮询调度。
    当某个模型触发 429 限速时，自动标记冷却并切换到下一个可用模型。
    模型列表会定期从数据库刷新，支持管理后台动态增删改。
    """

    # 模型列表缓存刷新间隔（秒）
    REFRESH_INTERVAL = 60

    def __init__(self) -> None:
        """初始化模型池"""
        self._lock = threading.Lock()
        self._index = 0
        # 模型列表缓存：[(name, max_context_length, cooldown_seconds), ...]
        self._models: List[Tuple[str, int, int]] = []
        # 每个模型的冷却截止时间戳
        self._cooldown_until: Dict[str, float] = {}
        # 上次刷新时间
        self._last_refresh: float = 0.0
        # 首次加载
        self._refresh_models()

    def _refresh_models(self) -> None:
        """从数据库刷新模型列表

        读取所有 is_enabled=True 的 AIModel 记录，按 priority 排序。
        仅在距上次刷新超过 REFRESH_INTERVAL 秒时执行。
        """
        now = time_module.time()
        if now - self._last_refresh < self.REFRESH_INTERVAL and self._models:
            return

        try:
            from mainotebook.content.models import AIModel
            db_models = list(
                AIModel.objects.filter(is_enabled=True)
                .order_by('priority', '-parameter_size', '-max_context_length')
                .values_list('name', 'max_context_length', 'cooldown_seconds')
            )
            if db_models:
                self._models = db_models
                # 为新模型初始化冷却时间
                for name, _, _ in self._models:
                    if name not in self._cooldown_until:
                        self._cooldown_until[name] = 0.0
                # 清理已删除模型的冷却记录
                active_names = {name for name, _, _ in self._models}
                for name in list(self._cooldown_until.keys()):
                    if name not in active_names:
                        del self._cooldown_until[name]
                self._last_refresh = now
                logger.debug("模型池已刷新，共 %d 个可用模型", len(self._models))
            elif not self._models:
                logger.warning("数据库中无可用模型，使用空列表")
        except Exception as e:
            logger.error("刷新模型池失败: %s", e)
            # 数据库不可用时保留旧列表

    def get_next_model(self) -> Optional[str]:
        """获取下一个可用模型

        按优先级轮询，跳过处于冷却期的模型。
        如果所有模型都在冷却中，返回冷却时间最短的模型。

        Returns:
            Optional[str]: 模型名称，无可用模型时返回 None
        """
        self._refresh_models()
        now = time_module.time()

        with self._lock:
            if not self._models:
                return None

            # 找到第一个不在冷却期的模型
            for i in range(len(self._models)):
                idx = (self._index + i) % len(self._models)
                model_name = self._models[idx][0]
                if self._cooldown_until.get(model_name, 0.0) <= now:
                    self._index = (idx + 1) % len(self._models)
                    return model_name

            # 所有模型都在冷却中，返回冷却最快结束的
            earliest_model = min(
                ((name, self._cooldown_until.get(name, 0.0)) for name, _, _ in self._models),
                key=lambda x: x[1],
            )[0]
            wait_time = self._cooldown_until.get(earliest_model, 0.0) - now
            logger.warning(
                "所有模型均在冷却中，使用冷却最快结束的模型: %s（%.1f 秒后可用）",
                earliest_model, wait_time,
            )
            return earliest_model

    def mark_rate_limited(self, model_name: str) -> None:
        """标记模型触发了 429 限速，进入冷却期

        冷却时间从数据库配置读取，默认 65 秒。

        Args:
            model_name: 触发限速的模型名称
        """
        # 查找该模型的冷却时间配置
        cooldown = 65  # 默认值
        with self._lock:
            for name, _, cd in self._models:
                if name == model_name:
                    cooldown = cd
                    break
            self._cooldown_until[model_name] = time_module.time() + cooldown

        logger.warning(
            "模型 %s 触发 429 限速，冷却 %d 秒", model_name, cooldown,
        )

    def is_available(self, model_name: str) -> bool:
        """检查模型是否可用（不在冷却期）

        Args:
            model_name: 模型名称

        Returns:
            bool: 模型是否可用
        """
        with self._lock:
            return self._cooldown_until.get(model_name, 0.0) <= time_module.time()

    @property
    def model_count(self) -> int:
        """当前可用模型总数"""
        self._refresh_models()
        return len(self._models)

    def force_refresh(self) -> None:
        """强制刷新模型列表（管理后台修改模型后调用）"""
        self._last_refresh = 0.0
        self._refresh_models()


class ModerationService:
    """AI 内容审核服务类"""

    # 基础系统提示词模板
    BASE_SYSTEM_PROMPT = """你是一个专业的内容安全审核员，负责判断用户生成的文本是否包含违规信息。

审核范围：
1. 色情（porn）：仅限露骨的性行为描写、色情词汇，不包含软色情或性暗示
2. 涉政（politics）：仅限中国国内政治敏感内容，包括对领导人的负面评价、敏感历史事件、领土分裂言论等
3. 辱骂（abuse）：仅限粗口脏话，不包含隐晦的人身攻击或歧视性言论
4. 暴力（violence）：仅限极端暴力描写、恐怖主义宣传
5. 垃圾信息（spam）：仅限明显的广告、诈骗、钓鱼链接
6. 违法（illegal）：仅限教唆犯罪、贩卖违禁品等明确违法内容

判断逻辑：
- 明确违规（置信度 > 0.9）：文本明显包含上述任一违规类型
- 明确正常（置信度 < 0.4）：文本完全正常，无任何违规迹象
- 不确定（置信度 0.4 ~ 0.9）：文本疑似违规但无法确定，如隐晦表达、谐音、反讽或边缘内容

{context_specific_rules}

输出格式（必须是合法的 JSON，不含任何额外文字）：
{{
  "decision": "true/false/unknown",
  "confidence": 0.0-1.0,
  "violation_types": ["porn", "politics", "abuse", "violence", "spam", "illegal"],
  "flagged_content": "引用原文中被判定为违规的具体片段，多个片段用 | 分隔；若无违规则为空字符串"
}}

字段说明：
- decision: "true"（通过）、"false"（拒绝）或 "unknown"（不确定）
- confidence: 0~1 的浮点数，表示内容违规的置信度，越接近 1 越确信违规
- violation_types: 违规类型数组，若 decision 为 "true" 则为空数组
- flagged_content: 从原文中摘录的违规片段（原文引用，不要改写），多个片段用 | 分隔。若无违规则为空字符串

示例：

输入：[包含露骨性描写的文本]
输出：{{"decision": "false", "confidence": 0.95, "violation_types": ["porn"], "flagged_content": "她脱下了所有衣服..."}}

输入：[包含对领导人侮辱性称呼的文本]
输出：{{"decision": "false", "confidence": 0.92, "violation_types": ["politics"], "flagged_content": "xxx是个xxx..."}}

输入：[包含粗口的句子]
输出：{{"decision": "false", "confidence": 0.88, "violation_types": ["abuse"], "flagged_content": "你这个xxx"}}

输入：[正常的日常对话]
输出：{{"decision": "true", "confidence": 0.15, "violation_types": [], "flagged_content": ""}}

输入：[使用谐音或隐晦表达的疑似违规内容]
输出：{{"decision": "unknown", "confidence": 0.65, "violation_types": ["politics"], "flagged_content": "疑似违规的片段..."}}

输入：[同时包含多种违规类型的文本]
输出：{{"decision": "false", "confidence": 0.93, "violation_types": ["porn", "abuse"], "flagged_content": "违规片段1 | 违规片段2"}}

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
        self.model_pool = ModelPool()

        logger.info(
            "ModerationService 初始化成功，模型池包含 %d 个模型",
            self.model_pool.model_count,
        )
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
        max_tokens: int = 500,
        source: Optional[str] = None,
        content_id: Optional[str] = None,
        user=None,
    ) -> Dict[str, Any]:
        """对文本进行内容审核（带多模型负载均衡）

        自动从模型池选择可用模型，遇到 429 限速时切换到下一个模型重试。
        最多尝试模型池中所有模型各一次。429 错误不计入成功率统计。

        Args:
            text: 待审核的文本内容
            text_type: 文本类型（comment/post/title/content/knowledge/persona）
            temperature: 模型温度参数，越低输出越稳定
            max_tokens: 最大输出 token 数
            source: 审核来源（comment/knowledge/persona/knowledge_file），不传则从 text_type 推断
            content_id: 关联的内容 ID（可选）
            user: 触发审核的用户对象（可选）

        Returns:
            dict: 审核结果字典，包含以下字段：
                - decision: str, "true"/"false"/"unknown"
                - confidence: float, 0~1
                - violation_types: List[str]
                - _meta: dict, 元数据
        """
        import time

        if not text or not text.strip():
            logger.warning("输入文本为空，返回默认通过结果")
            return {"decision": "true", "confidence": 0.0, "violation_types": []}

        log_source = source or text_type
        user_message = f"文本类型：{text_type}\n待审核内容：{text}"
        system_prompt = self._get_system_prompt(text_type)

        # 最多尝试所有模型各一次
        max_attempts = self.model_pool.model_count
        last_error = None

        for attempt in range(max_attempts):
            model_name = self.model_pool.get_next_model()
            if model_name is None:
                break

            # 如果模型在冷却中且这是最后的选择，短暂等待
            if not self.model_pool.is_available(model_name):
                logger.info("等待模型 %s 冷却结束...", model_name)
                time.sleep(2)

            start_time = time.monotonic()
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )
                latency_ms = int((time.monotonic() - start_time) * 1000)

                # 提取 token 用量
                usage = getattr(response, 'usage', None)
                prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
                total_tokens = getattr(usage, 'total_tokens', 0) or 0

                output = response.choices[0].message.content.strip()
                logger.debug("模型 %s 原始输出: %s", model_name, output)

                # 解析 JSON 结果
                result = json.loads(output)

                if not self._validate_result(result):
                    logger.error("模型 %s 输出格式不符合要求: %s", model_name, result)
                    result = self._get_default_unknown_result()

                result['_meta'] = {
                    'model_name': model_name,
                    'api_provider': 'siliconflow',
                    'temperature': temperature,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'latency_ms': latency_ms,
                    'raw_output': output,
                    'is_success': True,
                    'error_message': None,
                }

                logger.info(
                    "审核完成 [%s] - 决策: %s, 置信度: %s, 违规: %s, "
                    "Token: %d, 耗时: %dms",
                    model_name, result['decision'], result['confidence'],
                    result['violation_types'], total_tokens, latency_ms,
                )

                ModerationService.save_moderation_log(
                    result=result, source=log_source, text_type=text_type,
                    input_text=text, content_id=content_id, user=user,
                )
                return result

            except json.JSONDecodeError as e:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                logger.error(
                    "模型 %s JSON 解析失败: %s, 原始输出: %s",
                    model_name, e, output if 'output' in locals() else 'N/A',
                )
                result = self._get_default_unknown_result()
                result['_meta'] = {
                    'model_name': model_name,
                    'api_provider': 'siliconflow',
                    'temperature': temperature,
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                    'latency_ms': latency_ms,
                    'raw_output': output if 'output' in locals() else None,
                    'is_success': False,
                    'error_message': f"JSON 解析失败: {e}",
                }
                ModerationService.save_moderation_log(
                    result=result, source=log_source, text_type=text_type,
                    input_text=text, content_id=content_id, user=user,
                )
                return result

            except Exception as e:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                error_str = str(e)
                is_rate_limited = '429' in error_str or 'rate' in error_str.lower()

                if is_rate_limited:
                    # 429 限速：标记冷却，记录日志（不计入成功率），切换模型重试
                    self.model_pool.mark_rate_limited(model_name)
                    logger.warning(
                        "模型 %s 触发 429 限速（第 %d/%d 次尝试），切换下一个模型",
                        model_name, attempt + 1, max_attempts,
                    )
                    # 记录限速日志，is_success=True 表示不计入失败率
                    rate_limit_result = self._get_default_unknown_result()
                    rate_limit_result['_meta'] = {
                        'model_name': model_name,
                        'api_provider': 'siliconflow',
                        'temperature': temperature,
                        'prompt_tokens': 0,
                        'completion_tokens': 0,
                        'total_tokens': 0,
                        'latency_ms': latency_ms,
                        'raw_output': None,
                        'is_success': True,  # 限速不计入失败
                        'error_message': f"429 Rate Limited: {error_str}",
                    }
                    ModerationService.save_moderation_log(
                        result=rate_limit_result, source=log_source,
                        text_type=text_type, input_text=text,
                        content_id=content_id, user=user,
                    )
                    last_error = e
                    continue  # 切换到下一个模型

                # 非 429 错误，直接返回
                logger.error(
                    "模型 %s 审核异常: %s", model_name, e, exc_info=True,
                )
                result = self._get_default_unknown_result()
                result['_meta'] = {
                    'model_name': model_name,
                    'api_provider': 'siliconflow',
                    'temperature': temperature,
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                    'latency_ms': latency_ms,
                    'raw_output': None,
                    'is_success': False,
                    'error_message': error_str,
                }
                ModerationService.save_moderation_log(
                    result=result, source=log_source, text_type=text_type,
                    input_text=text, content_id=content_id, user=user,
                )
                return result

        # 所有模型都被限速，返回默认结果
        logger.error("所有模型均被限速，无法完成审核: %s", last_error)
        result = self._get_default_unknown_result()
        result['_meta'] = {
            'model_name': 'all_rate_limited',
            'api_provider': 'siliconflow',
            'temperature': temperature,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'latency_ms': 0,
            'raw_output': None,
            'is_success': True,  # 限速不计入失败
            'error_message': "所有模型均被限速",
        }
        ModerationService.save_moderation_log(
            result=result, source=log_source, text_type=text_type,
            input_text=text, content_id=content_id, user=user,
        )
        return result

    def _validate_result(self, result: dict) -> bool:
        """验证审核结果格式是否正确
        
        Args:
            result: 待验证的结果字典
            
        Returns:
            bool: 格式是否正确
        """
        if not isinstance(result, dict):
            return False

        # 检查必需字段（flagged_content 为可选，缺失时补空字符串）
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
        valid_types = {"porn", "politics", "abuse", "violence", "spam", "illegal"}
        if not all(vtype in valid_types for vtype in result["violation_types"]):
            return False

        # 补全 flagged_content 字段（模型可能未返回）
        if "flagged_content" not in result:
            result["flagged_content"] = ""

        return True

    def _get_default_unknown_result(self) -> Dict[str, Any]:
        """获取默认的"不确定"结果（用于异常情况）
        
        Returns:
            dict: 默认结果字典
        """
        return {"decision": "unknown", "confidence": 0.5, "violation_types": []}

    @staticmethod
    def save_moderation_log(
        result: Dict[str, Any],
        source: str,
        text_type: str,
        input_text: str,
        content_id: Optional[str] = None,
        user=None,
    ) -> None:
        """将审核结果保存为 ModerationLog 记录

        从 moderate() 返回的 result['_meta'] 中提取元数据，
        结合业务上下文信息写入数据库。调用失败仅记录日志，不抛出异常。

        Args:
            result: moderate() 返回的审核结果字典（含 _meta 键）
            source: 审核来源（comment/knowledge/persona/knowledge_file）
            text_type: 文本类型（comment/post/title/content/knowledge/persona）
            input_text: 提交审核的原始文本
            content_id: 关联的内容 ID（评论/知识库/人设卡 ID）
            user: 触发审核的用户对象（Django User 实例）
        """
        try:
            from mainotebook.content.models import ModerationLog

            meta = result.get('_meta', {})
            if not meta:
                logger.warning("审核结果缺少 _meta 数据，跳过日志记录")
                return

            ModerationLog.objects.create(
                source=source,
                content_id=content_id,
                user=user,
                model_name=meta.get('model_name', ''),
                api_provider=meta.get('api_provider', 'siliconflow'),
                temperature=meta.get('temperature', 0.1),
                text_type=text_type,
                input_text=input_text,
                input_text_length=len(input_text),
                prompt_tokens=meta.get('prompt_tokens', 0),
                completion_tokens=meta.get('completion_tokens', 0),
                total_tokens=meta.get('total_tokens', 0),
                decision=result.get('decision', 'unknown'),
                confidence=result.get('confidence', 0.0),
                violation_types=result.get('violation_types', []),
                raw_output=meta.get('raw_output'),
                latency_ms=meta.get('latency_ms', 0),
                is_success=meta.get('is_success', True),
                error_message=meta.get('error_message'),
            )
            logger.debug("审核日志已保存: source=%s, decision=%s", source, result.get('decision'))
        except Exception as e:
            logger.error("保存审核日志失败: %s", e, exc_info=True)



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
