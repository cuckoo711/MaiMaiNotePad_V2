# 序列化器使用指南

本目录包含 mainotebook.content 应用的所有序列化器，包括通用基类和混入类。

## 通用序列化器（common.py）

### 混入类（Mixins）

#### 1. UploaderInfoMixin
为序列化器添加上传者信息字段（姓名和头像）。

**适用场景**：包含 `uploader` 外键的模型（如知识库、人设卡）

**提供字段**：
- `uploader_name`: 上传者姓名（只读）
- `uploader_avatar`: 上传者头像（只读）

**使用示例**：
```python
class MyContentSerializer(UploaderInfoMixin, CustomModelSerializer):
    class Meta:
        model = MyContent
        fields = ['id', 'name', 'uploader_name', 'uploader_avatar']
```

#### 2. StarStatusMixin
为序列化器添加收藏状态字段。

**适用场景**：可被用户收藏的内容

**提供字段**：
- `is_starred`: 当前用户是否已收藏（只读）

**使用要求**：
- 必须在 Meta 中指定 `target_type` 属性（'knowledge' 或 'persona'）

**使用示例**：
```python
class MyContentSerializer(StarStatusMixin, CustomModelSerializer):
    class Meta:
        model = MyContent
        target_type = 'knowledge'  # 必须指定
        fields = ['id', 'name', 'is_starred']
```

#### 3. UserInfoMixin
为序列化器添加用户信息字段（姓名和头像）。

**适用场景**：包含 `user` 外键的模型（如评论）

**提供字段**：
- `user_name`: 用户姓名（只读）
- `user_avatar`: 用户头像（只读）

**使用示例**：
```python
class CommentSerializer(UserInfoMixin, CustomModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'content', 'user_name', 'user_avatar']
```

#### 4. OwnershipValidationMixin
提供所有权验证方法。

**适用场景**：需要验证用户是否为资源创建者的场景

**提供方法**：
- `validate_ownership(instance, user, owner_field='uploader', error_message='...')`

**使用示例**：
```python
class MyUpdateSerializer(OwnershipValidationMixin, CustomModelSerializer):
    def validate(self, attrs):
        request = self.context.get('request')
        self.validate_ownership(
            instance=self.instance,
            user=request.user,
            error_message="只有创建者可以修改"
        )
        return attrs
```

#### 5. UniqueNameValidationMixin
提供名称唯一性验证方法。

**适用场景**：需要在用户范围内验证名称唯一性的场景

**提供方法**：
- `validate_unique_name(value, user, model_class, owner_field='uploader', exclude_instance=None, error_message='...')`

**使用示例**：
```python
class MyCreateSerializer(UniqueNameValidationMixin, CustomModelSerializer):
    def validate_name(self, value):
        request = self.context.get('request')
        return self.validate_unique_name(
            value=value,
            user=request.user,
            model_class=MyModel,
            error_message="您已经创建了同名的资源"
        )
```

#### 6. AuthenticationValidationMixin
提供用户认证验证方法。

**适用场景**：需要验证用户是否已认证的场景

**提供方法**：
- `validate_user_authenticated(request)`

**使用示例**：
```python
class MySerializer(AuthenticationValidationMixin, CustomModelSerializer):
    def validate(self, attrs):
        request = self.context.get('request')
        self.validate_user_authenticated(request)
        return attrs
```

### 基类（Base Classes）

#### 1. ContentSerializer
内容序列化器基类，适用于知识库和人设卡等内容类型。

**包含混入**：
- UploaderInfoMixin
- StarStatusMixin

**提供字段**：
- 上传者信息（uploader_name, uploader_avatar）
- 收藏状态（is_starred）
- 文件列表（files）

**使用要求**：
- 子类必须在 Meta 中指定 `target_type` 属性
- 子类必须实现 `get_files(self, obj)` 方法

**使用示例**：
```python
class MyContentSerializer(ContentSerializer):
    class Meta(ContentSerializer.Meta):
        model = MyContent
        target_type = 'knowledge'
    
    def get_files(self, obj):
        return MyFileSerializer(obj.files.all(), many=True).data
```

#### 2. ContentCreateSerializer
内容创建序列化器基类。

**包含混入**：
- AuthenticationValidationMixin
- UniqueNameValidationMixin

**功能**：
- 自动设置上传者
- 验证名称唯一性
- 验证用户认证

**可自定义属性**：
- `error_message_duplicate_name`: 名称重复时的错误消息

**使用示例**：
```python
class MyContentCreateSerializer(ContentCreateSerializer):
    error_message_duplicate_name = "您已经创建了同名的内容"
    
    class Meta(ContentCreateSerializer.Meta):
        model = MyContent
```

#### 3. ContentUpdateSerializer
内容更新序列化器基类。

**包含混入**：
- AuthenticationValidationMixin
- OwnershipValidationMixin
- UniqueNameValidationMixin

**功能**：
- 验证用户权限
- 验证名称唯一性（排除当前实例）
- 验证用户认证

**可自定义属性**：
- `error_message_permission_denied`: 权限不足时的错误消息
- `error_message_duplicate_name`: 名称重复时的错误消息

**使用示例**：
```python
class MyContentUpdateSerializer(ContentUpdateSerializer):
    error_message_permission_denied = "只有创建者可以修改内容"
    error_message_duplicate_name = "您已经创建了同名的内容"
    
    class Meta(ContentUpdateSerializer.Meta):
        model = MyContent
```

#### 4. FileSerializer
文件序列化器基类。

**提供字段**：
- id, file_name, original_name, file_path, file_type, file_size, create_datetime

**使用示例**：
```python
class MyFileSerializer(FileSerializer):
    class Meta(FileSerializer.Meta):
        model = MyFile
```

## 完整使用示例

### 知识库序列化器

```python
from mainotebook.content.serializers.common import (
    ContentSerializer,
    ContentCreateSerializer,
    ContentUpdateSerializer,
    FileSerializer,
)

class KnowledgeBaseFileSerializer(FileSerializer):
    class Meta(FileSerializer.Meta):
        model = KnowledgeBaseFile

class KnowledgeBaseSerializer(ContentSerializer):
    class Meta(ContentSerializer.Meta):
        model = KnowledgeBase
        target_type = 'knowledge'
    
    def get_files(self, obj):
        return KnowledgeBaseFileSerializer(obj.files.all(), many=True).data

class KnowledgeBaseCreateSerializer(ContentCreateSerializer):
    error_message_duplicate_name = "您已经创建了同名的知识库"
    
    class Meta(ContentCreateSerializer.Meta):
        model = KnowledgeBase

class KnowledgeBaseUpdateSerializer(ContentUpdateSerializer):
    error_message_permission_denied = "只有创建者可以修改知识库"
    error_message_duplicate_name = "您已经创建了同名的知识库"
    
    class Meta(ContentUpdateSerializer.Meta):
        model = KnowledgeBase
```

## 设计原则

1. **DRY（Don't Repeat Yourself）**：通过混入类和基类减少代码重复
2. **单一职责**：每个混入类只负责一个特定功能
3. **可组合性**：混入类可以自由组合使用
4. **可扩展性**：子类可以覆盖属性和方法来自定义行为
5. **类型安全**：所有方法都包含类型提示

## 注意事项

1. 使用 `StarStatusMixin` 时必须在 Meta 中指定 `target_type`
2. 使用 `ContentSerializer` 时必须实现 `get_files` 方法
3. 所有序列化器都需要在 context 中传递 request 对象
4. 混入类的顺序很重要，应该放在 CustomModelSerializer 之前

## 验证需求

本通用序列化器实现满足以下需求：

- **需求 10.1**：保持与 FastAPI 应用相同的 API 端点路径
- **需求 10.2**：保持与 FastAPI 应用相同的请求参数格式
- **需求 10.3**：保持与 FastAPI 应用相同的响应数据结构

通过提供统一的基类和混入类，确保所有序列化器遵循相同的模式和规范。
