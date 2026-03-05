"""内容管理应用的过滤器类

本模块定义了内容管理相关的过滤器，用于 API 列表查询的筛选和搜索功能。
使用 django-filter 库实现声明式过滤。
"""

from django_filters import rest_framework as filters
from mainotebook.content.models import KnowledgeBase, PersonaCard, Comment


class KnowledgeBaseFilter(filters.FilterSet):
    """知识库过滤器
    
    支持按名称、标签、创建时间、收藏数等字段进行筛选和搜索。
    用于知识库列表的过滤功能。
    """
    
    # 名称模糊搜索
    name = filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        label='知识库名称'
    )
    
    # 描述模糊搜索
    description = filters.CharFilter(
        field_name='description',
        lookup_expr='icontains',
        label='知识库描述'
    )
    
    # 标签筛选（支持多标签查询，支持逗号分隔和数组格式）
    tags = filters.CharFilter(
        method='filter_tags',
        label='标签'
    )
    
    # 上传者筛选
    uploader = filters.UUIDFilter(
        field_name='uploader',
        label='上传者ID'
    )
    
    # 是否公开筛选
    is_public = filters.BooleanFilter(
        field_name='is_public',
        label='是否公开'
    )
    
    # 是否待审核筛选
    is_pending = filters.BooleanFilter(
        field_name='is_pending',
        label='是否待审核'
    )
    
    # 创建时间范围筛选
    create_datetime_after = filters.DateTimeFilter(
        field_name='create_datetime',
        lookup_expr='gte',
        label='创建时间起始'
    )
    
    create_datetime_before = filters.DateTimeFilter(
        field_name='create_datetime',
        lookup_expr='lte',
        label='创建时间结束'
    )
    
    # 收藏数范围筛选
    star_count_min = filters.NumberFilter(
        field_name='star_count',
        lookup_expr='gte',
        label='最小收藏数'
    )
    
    star_count_max = filters.NumberFilter(
        field_name='star_count',
        lookup_expr='lte',
        label='最大收藏数'
    )
    
    # 下载次数范围筛选
    downloads_min = filters.NumberFilter(
        field_name='downloads',
        lookup_expr='gte',
        label='最小下载次数'
    )
    
    downloads_max = filters.NumberFilter(
        field_name='downloads',
        lookup_expr='lte',
        label='最大下载次数'
    )
    
    # 综合搜索（名称、描述、标签）
    # 注意：字段名不能用 search，会和 DRF SearchFilter 自动生成的 search 参数冲突
    keyword = filters.CharFilter(
        method='filter_search',
        label='综合搜索'
    )
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'name', 'description', 'tags', 'uploader',
            'is_public', 'is_pending',
            'create_datetime_after', 'create_datetime_before',
            'star_count_min', 'star_count_max',
            'downloads_min', 'downloads_max',
            'keyword'
        ]
    
    def filter_tags(self, queryset, name, value):
        """标签筛选过滤方法

        支持单标签和多标签查询（数组格式）。
        前端应使用标准的数组参数格式：tags=标签1&tags=标签2
        tags 字段是 JSONField 数组格式，使用 contains 查询。
        多个标签之间是 OR 关系（满足任一标签即可）。

        Args:
            queryset: 查询集
            name: 字段名
            value: 标签字符串（CharFilter 只会传递最后一个值）

        Returns:
            QuerySet: 过滤后的查询集
        """
        from django.db.models import Q

        # 从 request 中获取完整的标签列表
        # CharFilter 的 value 参数只包含最后一个值，需要直接从 request 获取
        tag_list = self.request.GET.getlist('tags') if hasattr(self, 'request') else []

        # 如果没有从 request 获取到，使用传入的 value
        if not tag_list and value:
            tag_list = [value.strip()] if value.strip() else []

        # 清理标签列表
        tag_list = [tag.strip() for tag in tag_list if tag and tag.strip()]

        if not tag_list:
            return queryset

        # 使用 Q 对象组合多个标签的查询条件（OR 关系）
        # 对于 JSONField 数组，使用 contains 查询
        q_objects = Q()
        for tag in tag_list:
            # PostgreSQL JSONField 的 contains 查询
            q_objects |= Q(tags__contains=[tag])

        return queryset.filter(q_objects)
    
    def filter_search(self, queryset, name, value):
        """综合搜索过滤方法
        
        在名称、描述字段中进行模糊搜索。
        注意：标签字段现在是 JSONField，不再使用 icontains。
        
        Args:
            queryset: 查询集
            name: 字段名
            value: 搜索值
            
        Returns:
            QuerySet: 过滤后的查询集
        """
        if not value:
            return queryset
        
        from django.db.models import Q
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value)
        )


class PersonaCardFilter(filters.FilterSet):
    """人设卡过滤器
    
    支持按名称、标签、创建时间、收藏数等字段进行筛选和搜索。
    用于人设卡列表的过滤功能。
    """
    
    # 名称模糊搜索
    name = filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        label='人设卡名称'
    )
    
    # 描述模糊搜索
    description = filters.CharFilter(
        field_name='description',
        lookup_expr='icontains',
        label='人设卡描述'
    )
    
    # 标签筛选（支持多标签查询）
    tags = filters.CharFilter(
        method='filter_tags',
        label='标签'
    )
    
    # 上传者筛选
    uploader = filters.UUIDFilter(
        field_name='uploader',
        label='上传者ID'
    )
    
    # 是否公开筛选
    is_public = filters.BooleanFilter(
        field_name='is_public',
        label='是否公开'
    )
    
    # 是否待审核筛选
    is_pending = filters.BooleanFilter(
        field_name='is_pending',
        label='是否待审核'
    )
    
    # 创建时间范围筛选
    create_datetime_after = filters.DateTimeFilter(
        field_name='create_datetime',
        lookup_expr='gte',
        label='创建时间起始'
    )
    
    create_datetime_before = filters.DateTimeFilter(
        field_name='create_datetime',
        lookup_expr='lte',
        label='创建时间结束'
    )
    
    # 收藏数范围筛选
    star_count_min = filters.NumberFilter(
        field_name='star_count',
        lookup_expr='gte',
        label='最小收藏数'
    )
    
    star_count_max = filters.NumberFilter(
        field_name='star_count',
        lookup_expr='lte',
        label='最大收藏数'
    )
    
    # 下载次数范围筛选
    downloads_min = filters.NumberFilter(
        field_name='downloads',
        lookup_expr='gte',
        label='最小下载次数'
    )
    
    downloads_max = filters.NumberFilter(
        field_name='downloads',
        lookup_expr='lte',
        label='最大下载次数'
    )
    
    # 版本号筛选（支持泛筛选）
    version = filters.CharFilter(
        method='filter_version',
        label='版本号'
    )
    
    # 综合搜索（名称、描述、标签）
    # 注意：字段名不能用 search，会和 DRF SearchFilter 自动生成的 search 参数冲突
    keyword = filters.CharFilter(
        method='filter_search',
        label='综合搜索'
    )
    
    class Meta:
        model = PersonaCard
        fields = [
            'name', 'description', 'tags', 'uploader',
            'is_public', 'is_pending',
            'create_datetime_after', 'create_datetime_before',
            'star_count_min', 'star_count_max',
            'downloads_min', 'downloads_max',
            'version', 'keyword'
        ]
    
    def filter_version(self, queryset, name, value):
        """版本号筛选过滤方法
        
        支持以下格式：
        - 精确匹配：1.2.3
        - 主版本泛筛选：1.* 或 1（匹配 1.x.x）
        - 主次版本泛筛选：1.2.* 或 1.2（匹配 1.2.x）
        
        Args:
            queryset: 查询集
            name: 字段名
            value: 版本号字符串
            
        Returns:
            QuerySet: 过滤后的查询集
        """
        if not value:
            return queryset
        
        # 移除空格
        value = value.strip()
        
        # 处理通配符 *
        if value.endswith('.*'):
            # 移除 .* 后缀
            prefix = value[:-2]
            return queryset.filter(version__startswith=prefix + '.')
        elif value.endswith('*'):
            # 移除 * 后缀
            prefix = value[:-1]
            return queryset.filter(version__startswith=prefix)
        elif '.' not in value:
            # 只有主版本号，如 "1"，匹配 1.x.x
            return queryset.filter(version__startswith=value + '.')
        elif value.count('.') == 1:
            # 主次版本号，如 "1.2"，匹配 1.2.x
            return queryset.filter(version__startswith=value + '.')
        else:
            # 完整版本号，精确匹配
            return queryset.filter(version=value)
    
    def filter_tags(self, queryset, name, value):
        """标签筛选过滤方法

        支持单标签和多标签查询（数组格式）。
        前端应使用标准的数组参数格式：tags=标签1&tags=标签2
        tags 字段是 JSONField 数组格式，使用 contains 查询。
        多个标签之间是 OR 关系（满足任一标签即可）。

        Args:
            queryset: 查询集
            name: 字段名
            value: 标签字符串（CharFilter 只会传递最后一个值）

        Returns:
            QuerySet: 过滤后的查询集
        """
        from django.db.models import Q

        # 从 request 中获取完整的标签列表
        # CharFilter 的 value 参数只包含最后一个值，需要直接从 request 获取
        tag_list = self.request.GET.getlist('tags') if hasattr(self, 'request') else []

        # 如果没有从 request 获取到，使用传入的 value
        if not tag_list and value:
            tag_list = [value.strip()] if value.strip() else []

        # 清理标签列表
        tag_list = [tag.strip() for tag in tag_list if tag and tag.strip()]

        if not tag_list:
            return queryset

        # 使用 Q 对象组合多个标签的查询条件（OR 关系）
        # 对于 JSONField 数组，使用 contains 查询
        q_objects = Q()
        for tag in tag_list:
            # PostgreSQL JSONField 的 contains 查询
            q_objects |= Q(tags__contains=[tag])

        return queryset.filter(q_objects)
    
    def filter_search(self, queryset, name, value):
        """综合搜索过滤方法
        
        在名称、描述字段中进行模糊搜索。
        注意：标签字段现在是 JSONField，不再使用 icontains。
        
        Args:
            queryset: 查询集
            name: 字段名
            value: 搜索值
            
        Returns:
            QuerySet: 过滤后的查询集
        """
        if not value:
            return queryset
        
        from django.db.models import Q
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value)
        )


class CommentFilter(filters.FilterSet):
    """评论过滤器
    
    支持按目标ID、目标类型、用户、父评论等字段进行筛选。
    用于评论列表的过滤功能。
    """
    
    # 目标ID筛选
    target_id = filters.CharFilter(
        field_name='target_id',
        lookup_expr='exact',
        label='目标ID'
    )
    
    # 目标类型筛选
    target_type = filters.ChoiceFilter(
        field_name='target_type',
        choices=[
            ('knowledge', '知识库'),
            ('persona', '人设卡')
        ],
        label='目标类型'
    )
    
    # 用户筛选
    user = filters.UUIDFilter(
        field_name='user',
        label='用户ID'
    )
    
    # 父评论筛选（用于获取某条评论的回复）
    parent = filters.UUIDFilter(
        field_name='parent',
        label='父评论ID'
    )
    
    # 是否为顶级评论（没有父评论）
    is_root = filters.BooleanFilter(
        method='filter_is_root',
        label='是否为顶级评论'
    )
    
    # 是否已删除筛选
    is_deleted = filters.BooleanFilter(
        field_name='is_deleted',
        label='是否已删除'
    )
    
    # 创建时间范围筛选
    create_datetime_after = filters.DateTimeFilter(
        field_name='create_datetime',
        lookup_expr='gte',
        label='创建时间起始'
    )
    
    create_datetime_before = filters.DateTimeFilter(
        field_name='create_datetime',
        lookup_expr='lte',
        label='创建时间结束'
    )
    
    # 点赞数范围筛选
    like_count_min = filters.NumberFilter(
        field_name='like_count',
        lookup_expr='gte',
        label='最小点赞数'
    )
    
    like_count_max = filters.NumberFilter(
        field_name='like_count',
        lookup_expr='lte',
        label='最大点赞数'
    )
    
    # 内容模糊搜索
    content = filters.CharFilter(
        field_name='content',
        lookup_expr='icontains',
        label='评论内容'
    )
    
    class Meta:
        model = Comment
        fields = [
            'target_id', 'target_type', 'user', 'parent',
            'is_root', 'is_deleted',
            'create_datetime_after', 'create_datetime_before',
            'like_count_min', 'like_count_max',
            'content'
        ]
    
    def filter_is_root(self, queryset, name, value):
        """筛选顶级评论的过滤方法
        
        Args:
            queryset: 查询集
            name: 字段名
            value: 布尔值，True 表示只返回顶级评论
            
        Returns:
            QuerySet: 过滤后的查询集
        """
        if value is True:
            # 返回没有父评论的评论
            return queryset.filter(parent__isnull=True)
        elif value is False:
            # 返回有父评论的评论（回复）
            return queryset.filter(parent__isnull=False)
        return queryset
