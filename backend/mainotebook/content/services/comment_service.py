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
        # 获取所有评论（包括回复），按创建时间排序
        comments = Comment.objects.filter(
            target_id=target_id,
            target_type=target_type,
            is_deleted=False
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
        """创建评论
        
        创建新评论或回复。验证用户禁言状态和父评论有效性。
        
        Args:
            user: 评论用户
            data: 评论数据，包含 target_id, target_type, content, parent（可选）
            
        Returns:
            Comment: 创建的评论对象
            
        Raises:
            ValidationError: 当用户被禁言或父评论无效时
        """
        # 验证评论内容
        content = data.get('content', '')
        if not content or not content.strip():
            raise ValidationError("评论内容不能为空")
        
        if len(content) > 500:
            raise ValidationError("评论内容不能超过 500 字符")
        
        # 验证用户是否被禁言
        if user.is_muted:
            # 检查是否是永久禁言或禁言期未过
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
        
        # 创建评论
        comment = Comment.objects.create(
            user=user,
            target_id=data['target_id'],
            target_type=data['target_type'],
            content=content,
            parent_id=parent_id
        )
        
        return comment
    
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
