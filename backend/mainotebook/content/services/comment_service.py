"""评论服务模块

提供评论相关的业务逻辑，包括评论创建、删除、点赞等功能。
"""

from typing import List, Optional
from django.db.models import QuerySet
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied

from mainotebook.system.models import Users
from mainotebook.content.models import Comment, CommentReaction


class CommentService:
    """评论服务类
    
    提供评论相关的业务逻辑处理。
    """
    
    @staticmethod
    def get_comments_tree(target_id: str, target_type: str) -> List[Comment]:
        """获取评论树形结构
        
        获取指定目标的所有评论，并构建树形结构（包含嵌套回复）。
        
        Args:
            target_id: 目标 ID（知识库或人设卡的 UUID）
            target_type: 目标类型（'knowledge' 或 'persona'）
            
        Returns:
            List[Comment]: 根评论列表，每个评论包含 _prefetched_replies 属性存储子评论
        """
        # 获取所有评论（包括回复），排除已删除和 AI 拒绝的评论
        comments = Comment.objects.filter(
            target_id=target_id,
            target_type=target_type,
            is_deleted=False,
        ).exclude(
            moderation_status='rejected',
        ).select_related('user', 'reply_to', 'reply_to__user').prefetch_related('replies').order_by('create_datetime')
        
        # 构建树形结构
        comment_dict = {}
        root_comments = []
        
        # 第一遍遍历：建立字典映射，初始化回复列表
        for comment in comments:
            comment_dict[comment.id] = comment
            comment._prefetched_replies = []
        
        # 第二遍遍历：构建父子关系
        for comment in comments:
            if comment.parent_id:
                parent = comment_dict.get(comment.parent_id)
                if parent:
                    parent._prefetched_replies.append(comment)
            else:
                # 没有父评论的是根评论
                root_comments.append(comment)
        
        return root_comments
    
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
        # 验证评论内容
        content = data.get('content', '')
        if not content or not content.strip():
            raise ValidationError("评论内容不能为空")

        if len(content) > 500:
            raise ValidationError("评论内容不能超过 500 字符")

        # 验证用户是否被禁言
        if user.is_muted:
            if user.muted_until is None or user.muted_until > timezone.now():
                raise ValidationError("您已被禁言，无法发表评论")

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
            moderation_status=moderation_status,
            moderation_detail=moderation_detail,
        )

        return comment
    @staticmethod
    def _moderate_content(content: str, user=None, content_id: str = None) -> tuple:
        """调用 AI 审核评论内容

        使用 ModerationService 对评论内容进行审核，并记录审核日志。
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
        logger = logging.getLogger(__name__)

        try:
            from mainotebook.content.services.moderation_service import get_moderation_service
            service = get_moderation_service()
            result = service.moderate(
                content, text_type="comment",
                source="comment", user=user, content_id=content_id,
            )

            decision = result.get("decision", "unknown")

            # 映射 AI 决策到评论审核状态
            if decision == "false":
                moderation_status = "rejected"
            elif decision == "true":
                moderation_status = "approved"
            else:
                moderation_status = "uncertain"

            logger.info(
                "评论 AI 审核完成 - 状态: %s, 置信度: %s, 违规类型: %s",
                moderation_status, result.get("confidence"), result.get("violation_types"),
            )
            return moderation_status, result

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
