# -*- coding: utf-8 -*-

"""修复评论树结构中的三级及以上嵌套

将所有 parent 指向非根评论的评论修正为指向真正的根评论（parent=None），
确保评论树只有两层结构。
"""

from django.core.management.base import BaseCommand

from mainotebook.content.models import Comment


class Command(BaseCommand):
    help = '修复评论树结构，将三级及以上评论的 parent 修正为根评论'

    def handle(self, *args, **options):
        """遍历所有非根评论，检查并修正 parent 指向"""
        # 找出所有 parent 不为空的评论
        child_comments = Comment.objects.filter(
            parent__isnull=False
        ).select_related('parent')

        fixed_count = 0
        for comment in child_comments:
            if comment.parent_id and comment.parent and comment.parent.parent_id:
                # parent 本身也有 parent，说明是三级或更深
                root = comment.parent
                max_depth = 10
                while root.parent_id and max_depth > 0:
                    root = Comment.objects.filter(id=root.parent_id).first()
                    if not root:
                        break
                    max_depth -= 1

                if root and root.id != comment.parent_id:
                    old_parent_id = comment.parent_id
                    comment.parent_id = root.id
                    comment.save(update_fields=['parent_id'])
                    fixed_count += 1
                    self.stdout.write(
                        f'  修正: 评论 {comment.id} 的 parent '
                        f'从 {old_parent_id} -> {root.id}'
                    )

        self.stdout.write(self.style.SUCCESS(
            f'完成，共修正 {fixed_count} 条评论的 parent 指向'
        ))
