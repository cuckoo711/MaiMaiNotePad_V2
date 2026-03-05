# Content 模块测试

本目录包含 `mainotebook.content` 模块的所有测试文件。

## 目录结构

```
tests/
├── models/              # 模型层测试
│   ├── test_models.py           # 数据模型测试
│   └── test_exceptions.py       # 异常类测试
│
├── serializers/         # 序列化器测试
│   ├── test_common_serializers.py           # 通用序列化器测试
│   ├── test_comment_serializers.py          # 评论序列化器测试
│   ├── test_knowledge_base_serializers.py   # 知识库序列化器测试
│   ├── test_persona_card_serializers.py     # 人设卡序列化器测试
│   ├── test_star_serializers.py             # 收藏序列化器测试
│   └── test_tag_field*.py                   # 标签字段测试
│
├── services/            # 服务层测试
│   ├── test_auto_review_*.py                # AI 自动审核服务测试
│   ├── test_captcha_*.py                    # 验证码服务测试
│   ├── test_comment_*.py                    # 评论服务测试
│   ├── test_file_*.py                       # 文件服务测试
│   ├── test_knowledge_base_*.py             # 知识库服务测试
│   ├── test_moderation_*.py                 # 内容审核服务测试
│   ├── test_persona_card_*.py               # 人设卡服务测试
│   ├── test_review_*.py                     # 审核服务测试
│   ├── test_sensitive_info_detector_*.py    # 敏感信息检测服务测试
│   ├── test_star_*.py                       # 收藏服务测试
│   ├── test_tag_*.py                        # 标签服务测试
│   ├── test_toml_*.py                       # TOML 解析/导出服务测试
│   └── test_upload_quota_*.py               # 上传配额服务测试
│
├── views/               # 视图层测试
│   ├── test_knowledge_base_viewset*.py      # 知识库视图集测试
│   ├── test_persona_card_*.py               # 人设卡视图集测试
│   ├── test_review_*.py                     # 审核视图集测试
│   ├── test_star_viewset.py                 # 收藏视图集测试
│   └── test_user_extension_viewset.py       # 用户扩展视图集测试
│
└── integration/         # 集成测试
    ├── test_integration.py                          # 通用集成测试
    ├── test_persona_card_review_integration.py      # 人设卡审核集成测试
    ├── test_persona_card_serializer_tagfield_integration.py  # 标签字段集成测试
    ├── test_tag_*.py                                # 标签相关集成测试
    └── test_properties.py                           # 属性测试（通用）
```

## 测试类型

### 单元测试
- **模型测试** (`models/`): 测试数据模型的字段、方法、约束等
- **序列化器测试** (`serializers/`): 测试数据验证、序列化、反序列化逻辑
- **服务测试** (`services/`): 测试业务逻辑、数据处理、外部服务调用等
- **视图测试** (`views/`): 测试 API 端点、权限、请求/响应处理等

### 集成测试
- **集成测试** (`integration/`): 测试多个组件协同工作的场景
- **属性测试** (`*_properties.py`): 使用 Hypothesis 进行基于属性的测试

## 运行测试

### 运行所有测试
```bash
conda activate mai_notebook
cd backend
pytest mainotebook/content/tests/
```

### 运行特定模块的测试
```bash
# 运行服务层测试
pytest mainotebook/content/tests/services/

# 运行视图层测试
pytest mainotebook/content/tests/views/

# 运行集成测试
pytest mainotebook/content/tests/integration/
```

### 运行特定文件的测试
```bash
pytest mainotebook/content/tests/services/test_tag_service.py
```

### 运行特定测试用例
```bash
pytest mainotebook/content/tests/services/test_tag_service.py::TestTagService::test_parse_tags
```

### 查看测试覆盖率
```bash
pytest --cov=mainotebook.content --cov-report=html mainotebook/content/tests/
```

## 测试命名规范

- 测试文件: `test_<模块名>.py`
- 属性测试文件: `test_<模块名>_properties.py`
- 集成测试文件: `test_<功能名>_integration.py`
- 测试类: `Test<类名>`
- 测试方法: `test_<功能描述>`

## 注意事项

1. 所有测试必须独立运行，不依赖其他测试的执行顺序
2. 测试数据应在测试方法内创建和清理
3. 使用 fixtures 共享测试数据和配置
4. 属性测试用于验证函数在各种输入下的正确性
5. 集成测试用于验证多个组件协同工作的场景
