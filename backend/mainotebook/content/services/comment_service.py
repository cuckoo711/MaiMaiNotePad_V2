"""评论服务模块

提供评论相关的业务逻辑，包括评论创建、删除、点赞等功能。
"""

from typing import List, Optional
from django.db.models import QuerySet, Q
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied

from mainotebook.system.models import Users
from mainotebook.content.models import Comment, CommentReaction


class CommentService:
    """评论服务类
    
    提供评论相关的业务逻辑处理。
    """
    
    @staticmethod
    @staticmethod
    def get_comments_tree(target_id: str, target_type: str, page: int = 1, page_size: int = 10, user=None) -> dict:
        """获取评论树形结构（个性化推荐排序）
        
        使用个性化推荐算法对评论进行排序：
        1. 基础热度分数：综合时间、点赞、回复
        2. 用户兴趣权重：基于用户历史互动（点赞、回复、浏览）
        3. 多样性因子：避免信息茧房，保证内容多样性
        4. 向量相似度：使用 BGE-M3 嵌入模型计算语义相似度
        5. 重排序：使用 BGE-Reranker 精细调整（可选）
        
        排序策略：
        - 已登录用户：个性化排序（70%兴趣 + 30%热度）
        - 未登录用户：纯热度排序
        
        Args:
            target_id: 目标 ID（知识库或人设卡的 UUID）
            target_type: 目标类型（'knowledge' 或 'persona'）
            page: 页码（从1开始）
            page_size: 每页数量（默认10）
            user: 当前用户对象（可选，用于个性化）
            
        Returns:
            dict: {
                'comments': 根评论列表，
                'total': 总数，
                'page': 当前页，
                'page_size': 每页数量，
                'has_more': 是否还有更多
            }
        """
        from django.utils import timezone
        from django.db.models import Count, Q
        from mainotebook.content.services.recommendation_service import RecommendationService
        import math
        
        # 获取所有根评论（parent_id 为 None），排除已删除和 AI 拒绝的评论
        root_comments_query = Comment.objects.filter(
            target_id=target_id,
            target_type=target_type,
            is_deleted=False,
            parent_id__isnull=True,
        ).exclude(
            moderation_status='rejected',
        ).select_related('user').annotate(
            reply_count=Count('replies', filter=~Q(replies__is_deleted=True) & ~Q(replies__moderation_status='rejected'))
        )
        
        now = timezone.now()
        comments_with_score = []
        
        # 获取用户兴趣数据（带缓存）
        user_interests = None
        if user and user.is_authenticated:
            user_interests = RecommendationService.get_user_interests(user)
        
        for comment in root_comments_query:
            # ========== 1. 基础热度分数 ==========
            time_diff_hours = (now - comment.create_datetime).total_seconds() / 3600
            
            # 双阶段时间衰减
            if time_diff_hours < 24:
                # 24小时内不衰减（黄金期）
                time_decay = 1.0
            elif time_diff_hours < 168:  # 7天内
                # 每48小时衰减50%
                time_decay = math.pow(0.5, (time_diff_hours - 24) / 48)
            else:
                # 7天后快速衰减
                time_decay = math.pow(0.5, (time_diff_hours - 24) / 48) * 0.1
            
            # 互动分数（点赞权重更高，回复次之）
            engagement_score = (
                comment.like_count * 2.0 +
                comment.reply_count * 1.5 -
                comment.dislike_count * 0.5
            )
            
            # 质量加成（高互动评论额外加分，上限10分）
            quality_bonus = min(engagement_score * 0.1, 10)
            
            # 基础热度分数
            base_hot_score = engagement_score * time_decay + quality_bonus + 10
            
            # ========== 2. 用户兴趣权重 ==========
            interest_weight = 1.0
            if user_interests:
                # 评论作者兴趣匹配
                if comment.user_id in user_interests['favorite_authors']:
                    interest_weight *= 1.5  # 喜欢的作者，权重提升50%
                
                # 内容相似度（使用推荐服务计算）
                content_similarity = RecommendationService.calculate_content_similarity(
                    comment.content,
                    user_interests
                )
                interest_weight *= (1.0 + content_similarity * 0.5)  # 最多提升50%
            
            # ========== 3. 多样性因子 ==========
            diversity_factor = 1.0
            if user_interests and comment.user_id in user_interests.get('recent_seen_authors', []):
                diversity_factor = 0.7  # 最近看过该作者的评论，降低权重
            
            # ========== 4. 最终分数计算 ==========
            if user and user.is_authenticated:
                # 个性化排序：70%兴趣 + 30%热度
                final_score = (
                    base_hot_score * 0.3 +
                    base_hot_score * interest_weight * 0.7
                ) * diversity_factor
            else:
                # 未登录用户：纯热度排序
                final_score = base_hot_score
            
            comments_with_score.append((comment, final_score))
        
        # 按最终分数降序排序
        comments_with_score.sort(key=lambda x: x[1], reverse=True)
        
        # 提取评论列表
        sorted_comments = [item[0] for item in comments_with_score]
        
        # ========== 5. 重排序（可选，仅对前30条）==========
        # 对于已登录用户，使用 BGE-Reranker 对候选集进行精细重排序
        if user and user.is_authenticated and user_interests and len(sorted_comments) > 5:
            # 只对前30条候选进行重排序（平衡效果和性能）
            candidates = sorted_comments[:30]
            reranked = RecommendationService.rerank_comments(
                candidates,
                user_interests,
                top_k=None
            )
            # 合并重排序结果和剩余评论
            sorted_comments = reranked + sorted_comments[30:]
        
        # 分页
        total = len(sorted_comments)
        start = (page - 1) * page_size
        end = start + page_size
        page_comments = sorted_comments[start:end]
        
        # 为每个根评论加载前10条二级评论
        for comment in page_comments:
            replies = Comment.objects.filter(
                parent_id=comment.id,
                is_deleted=False,
            ).exclude(
                moderation_status='rejected',
            ).select_related('user', 'reply_to', 'reply_to__user').order_by('create_datetime')[:10]
            
            comment._prefetched_replies = list(replies)
            comment._reply_total = Comment.objects.filter(
                parent_id=comment.id,
                is_deleted=False,
            ).exclude(
                moderation_status='rejected',
            ).count()
        
        # 记录用户浏览行为（用于后续个性化）
        if user and user.is_authenticated and page_comments:
            RecommendationService.record_user_view(user.id, page_comments)
        
        return {
            'comments': page_comments,
            'total': total,
            'page': page,
            'page_size': page_size,
            'has_more': end < total
        }
    
    
    @staticmethod
    def get_replies(parent_id: str, page: int = 1, page_size: int = 10) -> dict:
        """获取指定评论的二级回复（分页）
        
        Args:
            parent_id: 父评论 ID
            page: 页码（从1开始）
            page_size: 每页数量（默认10条）
            
        Returns:
            dict: {
                'replies': 回复列表，
                'total': 总数，
                'page': 当前页，
                'page_size': 每页数量，
                'has_more': 是否还有更多
            }
        """
        # 获取二级回复，按时间正序排列
        replies_query = Comment.objects.filter(
            parent_id=parent_id,
            is_deleted=False,
        ).exclude(
            moderation_status='rejected',
        ).select_related('user', 'reply_to', 'reply_to__user').order_by('create_datetime')
        
        total = replies_query.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        replies = list(replies_query[start:end])
        
        return {
            'replies': replies,
            'total': total,
            'page': page,
            'page_size': page_size,
            'has_more': end < total
        }
    
    @staticmethod
    def create_comment(user: Users, data: dict) -> Comment:
        """创建评论（含 AI 内容审核）

        创建新评论或回复。验证用户禁言状态和父评论有效性。
        评论内容会经过 AI 审核，拒绝的评论不会被创建。

        Args:
            user: 评论用户
            data: 评论数据，包含 target_id, target_type, content, parent（可选）

        Returns:
            Comment: 创建的评论对象

        Raises:
            ValidationError: 当用户被禁言、父评论无效或评论被 AI 拒绝时
        """
        from django.db import transaction
        import logging
        
        logger = logging.getLogger(__name__)
        
        # 验证评论内容
        content = data.get('content', '')
        if not content or not content.strip():
            raise ValidationError("评论内容不能为空")

        if len(content) > 500:
            raise ValidationError("评论内容不能超过 500 字符")

        # 验证用户是否被禁言
        if user.is_muted:
            # 检查是否为永久禁言
            if user.muted_until is None:
                raise ValidationError(f"您已被永久禁言，无法发表评论。原因：{user.mute_reason or '违反社区规则'}")
            
            # 检查禁言是否未过期
            if user.muted_until > timezone.now():
                # 格式化剩余时间
                remaining = user.muted_until - timezone.now()
                days = remaining.days
                hours = remaining.seconds // 3600
                if days > 0:
                    time_str = f"{days}天{hours}小时" if hours > 0 else f"{days}天"
                else:
                    time_str = f"{hours}小时"
                
                raise ValidationError(
                    f"您已被禁言至 {user.muted_until.strftime('%Y-%m-%d %H:%M')}（还剩{time_str}），无法发表评论。"
                    f"原因：{user.mute_reason or '违反社区规则'}"
                )
            
            # 禁言已过期，自动解除
            try:
                with transaction.atomic():
                    # 更新用户表
                    user.is_muted = False
                    user.save(update_fields=['is_muted'])
                    
                    # 更新禁言记录表
                    from mainotebook.content.models import UserMuteRecord
                    active_mute_records = UserMuteRecord.objects.filter(
                        user=user,
                        is_active=True
                    )
                    active_mute_records.update(
                        is_active=False,
                        unmuted_at=timezone.now()
                    )
                    
                    logger.info(f"自动解除过期禁言：user_id={user.id}")
            except Exception as e:
                logger.error(f"自动解除禁言失败：user_id={user.id}, error={str(e)}")
                # 即使解除失败，也允许用户继续发表评论（因为禁言已过期）

        # 验证父评论（如果是回复）
        parent_id = data.get('parent')
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id)
                if parent.is_deleted:
                    raise ValidationError("父评论已被删除，无法回复")
            except Comment.DoesNotExist:
                raise ValidationError("父评论不存在")

        # AI 内容审核
        moderation_status, moderation_detail = CommentService._moderate_content(content)

        # AI 拒绝的评论直接抛出异常，不创建
        if moderation_status == 'rejected':
            violation_label_map = {
                'porn': '色情内容',
                'politics': '涉政内容',
                'abuse': '辱骂内容',
            }
            violation_types = moderation_detail.get('violation_types', [])
            violation_labels = [violation_label_map.get(v, v) for v in violation_types]
            if violation_labels:
                msg = f"您的评论未通过内容审核（违规类型：{'、'.join(violation_labels)}），请修改后重试"
            else:
                msg = "您的评论未通过内容审核，请修改后重试"
            raise ValidationError(msg)

        # 创建评论（通过和不确定的都允许展示）
        comment = Comment.objects.create(
            user=user,
            target_id=data['target_id'],
            target_type=data['target_type'],
            content=content,
            parent_id=parent_id,
            reply_to_id=data.get('reply_to'),
            moderation_status=moderation_status,
            moderation_detail=moderation_detail,
        )
        
        # 清除用户推荐缓存（回复是强兴趣信号）
        from mainotebook.content.services.recommendation_service import RecommendationService
        RecommendationService.clear_user_cache(user.id)

        return comment
    @staticmethod
    def _moderate_content(content: str, user=None, content_id: str = None) -> tuple:
        """调用 AI 审核评论内容

        使用 ModerationService 对评论内容进行审核，并记录审核日志。
        评论审核优先使用 THUDM/glm-4-9b-chat 模型，如果该模型失败则自动切换到模型池的其他模型。
        AI 异常时默认放行（返回 uncertain），不阻塞用户发言。

        Args:
            content: 评论文本内容
            user: 触发审核的用户对象（可选，用于日志记录）
            content_id: 关联的评论 ID（可选，用于日志记录）

        Returns:
            tuple: (moderation_status, moderation_detail)
                - moderation_status: 'approved' / 'rejected' / 'uncertain'
                - moderation_detail: AI 返回的原始审核结果字典
        """
        import logging
        import time
        from openai import OpenAI
        
        logger = logging.getLogger(__name__)

        try:
            from mainotebook.content.services.moderation_service import get_moderation_service, _get_api_key
            from mainotebook.content.models import ModerationLog
            
            service = get_moderation_service()
            preferred_model = 'THUDM/glm-4-9b-chat'
            
            # 第一步：尝试使用 THUDM/glm-4-9b-chat
            try:
                logger.info("评论审核优先使用模型: %s", preferred_model)
                
                # 获取系统提示词
                system_prompt = service._get_system_prompt("comment")
                user_message = f"文本类型：comment\n待审核内容：{content}"
                
                # 创建待审核日志
                moderation_log = ModerationLog.objects.create(
                    source="comment",
                    content_id=content_id,
                    user=user,
                    model_name=preferred_model,
                    api_provider='siliconflow',
                    temperature=0.1,
                    text_type="comment",
                    input_text=content,
                    input_text_length=len(content),
                    decision='pending',
                    confidence=0.0,
                    violation_types=[],
                    is_success=False,
                )
                
                start_time = time.monotonic()
                
                # 直接调用 API
                api_key = _get_api_key()
                client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")
                
                response = client.chat.completions.create(
                    model=preferred_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "今天天气真好"},
                        {"role": "assistant", "content": '{"decision": "approved", "confidence": 0.9, "violation_types": [], "flagged_content": ""}'},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                    stream=False,
                    timeout=60,
                    extra_body={"enable_thinking": False},
                )
                
                latency_ms = int((time.monotonic() - start_time) * 1000)
                
                # 提取 token 用量
                usage = getattr(response, 'usage', None)
                prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
                total_tokens = getattr(usage, 'total_tokens', 0) or 0
                
                output = response.choices[0].message.content.strip()
                
                # 解析 JSON 结果
                from mainotebook.utils.json_helper import extract_json
                result = extract_json(output)
                
                if not service._validate_result(result):
                    raise ValueError(f"模型输出格式不符合要求: {result}")
                
                # 兼容旧格式：将 true/false 转换为 approved/rejected
                if result.get('decision') == 'true':
                    result['decision'] = 'approved'
                elif result.get('decision') == 'false':
                    result['decision'] = 'rejected'
                
                result['_meta'] = {
                    'model_name': preferred_model,
                    'api_provider': 'siliconflow',
                    'temperature': 0.1,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'latency_ms': latency_ms,
                    'raw_output': output,
                    'is_success': True,
                    'error_message': None,
                }
                
                # 更新日志为成功
                moderation_log.decision = result['decision']
                moderation_log.confidence = result['confidence']
                moderation_log.violation_types = result['violation_types']
                moderation_log.prompt_tokens = prompt_tokens
                moderation_log.completion_tokens = completion_tokens
                moderation_log.total_tokens = total_tokens
                moderation_log.raw_output = output
                moderation_log.latency_ms = latency_ms
                moderation_log.is_success = True
                moderation_log.save()
                
                logger.info(
                    "审核完成 [%s] - 决策: %s, 置信度: %s, 违规: %s, Token: %d, 耗时: %dms",
                    preferred_model, result['decision'], result['confidence'],
                    result['violation_types'], total_tokens, latency_ms,
                )
                
                # 映射 AI 决策到评论审核状态
                decision = result.get("decision", "unknown")
                if decision == "rejected":
                    moderation_status = "rejected"
                elif decision == "approved":
                    moderation_status = "approved"
                else:
                    moderation_status = "uncertain"
                
                return moderation_status, result
                
            except Exception as e:
                error_str = str(e)
                is_rate_limited = '429' in error_str or 'rate' in error_str.lower()
                
                if is_rate_limited:
                    logger.warning("%s 触发 429 限速，切换到模型池其他模型", preferred_model)
                    # 标记该模型进入冷却期
                    service.model_pool.mark_rate_limited(preferred_model)
                else:
                    logger.warning("%s 审核失败: %s，切换到模型池其他模型", preferred_model, e)
                
                # 更新日志为错误
                if 'moderation_log' in locals():
                    latency_ms = int((time.monotonic() - start_time) * 1000) if 'start_time' in locals() else 0
                    moderation_log.decision = 'error'
                    moderation_log.latency_ms = latency_ms
                    moderation_log.is_success = is_rate_limited  # 限速不计入失败
                    moderation_log.error_message = error_str
                    moderation_log.save()
            
            # 第二步：使用模型池的其他模型（跳过 THUDM/glm-4-9b-chat）
            logger.info("使用模型池进行审核（跳过 %s）", preferred_model)
            
            # 临时从模型池中移除 THUDM/glm-4-9b-chat
            with service.model_pool._lock:
                original_models = service.model_pool._models[:]
                filtered_models = [m for m in original_models if m[0] != preferred_model]
                service.model_pool._models = filtered_models
            
            try:
                result = service.moderate(
                    content, text_type="comment",
                    source="comment", user=user, content_id=content_id,
                )
                
                decision = result.get("decision", "unknown")
                
                # 映射 AI 决策到评论审核状态
                if decision == "rejected":
                    moderation_status = "rejected"
                elif decision == "approved":
                    moderation_status = "approved"
                else:
                    moderation_status = "uncertain"
                
                logger.info(
                    "评论 AI 审核完成 - 状态: %s, 置信度: %s, 违规类型: %s",
                    moderation_status, result.get("confidence"), result.get("violation_types"),
                )
                return moderation_status, result
            finally:
                # 恢复原始模型列表
                with service.model_pool._lock:
                    service.model_pool._models = original_models

        except Exception as e:
            # AI 服务异常时默认放行，不阻塞用户
            logger.warning("评论 AI 审核异常，默认放行: %s", e)
            return "uncertain", {"error": str(e), "decision": "unknown"}
    
    @staticmethod
    def delete_comment(comment: Comment, user: Users) -> None:
        """删除评论（软删除，级联删除子评论）
        
        软删除评论及其所有子评论。只有评论创建者或管理员可以删除。
        
        Args:
            comment: 评论对象
            user: 当前用户
            
        Raises:
            PermissionDenied: 当用户无权限删除时
        """
        # 验证权限（创建者或管理员）
        if comment.user != user and not user.is_staff:
            raise PermissionDenied("只有创建者或管理员可以删除评论")
        
        # 递归软删除评论及其所有子评论
        def delete_recursive(c: Comment) -> None:
            """递归删除评论及其子评论
            
            Args:
                c: 要删除的评论对象
            """
            c.is_deleted = True
            c.save()
            # 递归删除所有子评论
            for reply in c.replies.all():
                delete_recursive(reply)
        
        delete_recursive(comment)
    
    @staticmethod
    def react_comment(comment: Comment, user: Users, action: str) -> dict:
        """处理评论反应（点赞/点踩/取消）
        
        统一处理用户对评论的反应操作，支持点赞、点踩和取消。
        
        Args:
            comment: 评论对象
            user: 当前用户
            action: 操作类型，'like'、'dislike' 或 'clear'
            
        Returns:
            dict: 包含 like_count、dislike_count 和 my_reaction 的字典
            
        Raises:
            ValidationError: 当 action 无效时
        """
        if action not in ('like', 'dislike', 'clear'):
            raise ValidationError("无效的操作类型，仅支持 like、dislike、clear")
        
        # 获取当前用户的反应记录
        existing = CommentReaction.objects.filter(
            user=user, comment=comment
        ).first()
        
        if action == 'clear':
            # 取消当前反应
            if existing:
                if existing.reaction_type == 'like':
                    comment.like_count = max(0, comment.like_count - 1)
                elif existing.reaction_type == 'dislike':
                    comment.dislike_count = max(0, comment.dislike_count - 1)
                existing.delete()
            comment.save()
            my_reaction = None
        elif existing:
            # 已有反应记录
            if existing.reaction_type == action:
                # 重复操作，不做任何变更
                pass
            else:
                # 切换反应类型
                if existing.reaction_type == 'like':
                    comment.like_count = max(0, comment.like_count - 1)
                else:
                    comment.dislike_count = max(0, comment.dislike_count - 1)
                
                existing.reaction_type = action
                existing.save()
                
                if action == 'like':
                    comment.like_count += 1
                else:
                    comment.dislike_count += 1
                comment.save()
            my_reaction = action
        else:
            # 新增反应
            CommentReaction.objects.create(
                user=user, comment=comment, reaction_type=action
            )
            if action == 'like':
                comment.like_count += 1
            else:
                comment.dislike_count += 1
            comment.save()
            my_reaction = action
        
        comment.refresh_from_db()
        
        # 清除用户推荐缓存（点赞是兴趣信号）
        from mainotebook.content.services.recommendation_service import RecommendationService
        RecommendationService.clear_user_cache(user.id)
        
        return {
            'like_count': comment.like_count,
            'dislike_count': comment.dislike_count,
            'my_reaction': my_reaction,
        }
    
    @staticmethod
    def like_comment(comment: Comment, user: Users) -> None:
        """点赞评论（兼容旧接口）
        
        Args:
            comment: 评论对象
            user: 当前用户
        """
        CommentService.react_comment(comment, user, 'like')
    
    @staticmethod
    def unlike_comment(comment: Comment, user: Users) -> None:
        """取消点赞评论（兼容旧接口）
        
        Args:
            comment: 评论对象
            user: 当前用户
        """
        CommentService.react_comment(comment, user, 'clear')
