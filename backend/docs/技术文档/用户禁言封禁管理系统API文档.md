# 用户禁言封禁管理系统 API 文档

## 概述

用户禁言封禁管理系统提供完整的用户行为管控能力，包括手动禁言/封禁、AI自动禁言、批量操作、操作日志记录和通知机制。本文档详细说明所有API端点的使用方法。

## 基础信息

- **基础路径**: `/api/content/moderation/`
- **认证方式**: JWT Token
- **权限要求**: 需要 `moderation_admin` 角色或超级管理员权限
- **响应格式**: JSON

### 统一响应格式

```json
{
  "code": 2000,
  "msg": "操作成功",
  "data": {
    // 响应数据
  }
}
```

### 错误响应格式

```json
{
  "code": 4000,
  "msg": "错误描述",
  "data": null
}
```

### 常见错误码

- `2000`: 操作成功
- `4000`: 参数验证失败
- `4003`: 权限不足
- `4004`: 资源不存在
- `4009`: 业务逻辑错误
- `5000`: 服务器内部错误

---

## API 端点列表

### 1. 禁言用户

**端点**: `POST /api/content/moderation/mute/`

**权限**: `mute:Create`

**描述**: 对指定用户执行禁言操作

**请求参数**:

```json
{
  "user_id": 123,
  "duration": "3d",
  "reason": "发布违规内容"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | integer | 是 | 被禁言用户ID |
| duration | string | 是 | 禁言时长，支持格式：`3h`(小时)、`2d`(天)、`1w`(周)、`1m`(月)、`permanent`(永久) |
| reason | string | 是 | 禁言原因，不能为空 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "禁言成功",
  "data": {
    "success": true,
    "user_id": 123,
    "mute_record_id": 456,
    "muted_until": "2026-03-10T15:30:00Z",
    "mute_type": "manual"
  }
}
```

**错误示例**:

```json
{
  "code": 4003,
  "msg": "权限不足：普通管理员不能禁言其他管理员",
  "data": null
}
```

---

### 2. 解除禁言

**端点**: `POST /api/content/moderation/unmute/`

**权限**: `mute:Unmute`

**描述**: 解除指定用户的禁言状态

**请求参数**:

```json
{
  "user_id": 123,
  "reason": "申诉成功"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | integer | 是 | 被解除禁言的用户ID |
| reason | string | 否 | 解除原因 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "解除禁言成功",
  "data": {
    "success": true,
    "user_id": 123,
    "mute_record_id": 456
  }
}
```

---

### 3. 封禁用户

**端点**: `POST /api/content/moderation/ban/`

**权限**: `ban:Create`

**描述**: 对指定用户执行封禁操作，封禁后用户无法登录

**请求参数**:

```json
{
  "user_id": 123,
  "duration": "7d",
  "reason": "严重违规行为"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | integer | 是 | 被封禁用户ID |
| duration | string | 是 | 封禁时长，格式同禁言 |
| reason | string | 是 | 封禁原因，不能为空 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "封禁成功",
  "data": {
    "success": true,
    "user_id": 123,
    "locked_until": "2026-03-14T15:30:00Z"
  }
}
```

---

### 4. 解除封禁

**端点**: `POST /api/content/moderation/unban/`

**权限**: `ban:Unban`

**描述**: 解除指定用户的封禁状态

**请求参数**:

```json
{
  "user_id": 123,
  "reason": "申诉成功"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | integer | 是 | 被解除封禁的用户ID |
| reason | string | 否 | 解除原因 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "解除封禁成功",
  "data": {
    "success": true,
    "user_id": 123
  }
}
```

---

### 5. 修改时长

**端点**: `PUT /api/content/moderation/modify-duration/`

**权限**: `mute:ModifyDuration` 或 `ban:ModifyDuration`

**描述**: 修改用户的禁言或封禁时长

**请求参数**:

```json
{
  "user_id": 123,
  "operation_type": "mute",
  "new_duration": "1w",
  "reason": "根据情况调整时长"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | integer | 是 | 用户ID |
| operation_type | string | 是 | 操作类型：`mute`(禁言) 或 `ban`(封禁) |
| new_duration | string | 是 | 新的时长 |
| reason | string | 是 | 修改原因，不能为空 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "修改时长成功",
  "data": {
    "success": true,
    "user_id": 123,
    "old_hours": 72,
    "new_hours": 168,
    "new_muted_until": "2026-03-14T15:30:00Z"
  }
}
```

---

### 6. 批量禁言

**端点**: `POST /api/content/moderation/batch-mute/`

**权限**: `mute:BatchMute`

**描述**: 批量禁言多个用户，最多支持20个用户

**请求参数**:

```json
{
  "user_ids": [123, 456, 789],
  "duration": "1d",
  "reason": "批量违规"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_ids | array | 是 | 用户ID列表，最多20个 |
| duration | string | 是 | 禁言时长 |
| reason | string | 是 | 禁言原因 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "批量禁言成功",
  "data": {
    "success": true,
    "total": 3,
    "success_count": 3,
    "failed_count": 0,
    "results": [
      {
        "user_id": 123,
        "success": true,
        "message": "禁言成功"
      },
      {
        "user_id": 456,
        "success": true,
        "message": "禁言成功"
      },
      {
        "user_id": 789,
        "success": true,
        "message": "禁言成功"
      }
    ]
  }
}
```

---

### 7. 批量封禁

**端点**: `POST /api/content/moderation/batch-ban/`

**权限**: `ban:BatchBan`

**描述**: 批量封禁多个用户，最多支持20个用户

**请求参数**:

```json
{
  "user_ids": [123, 456],
  "duration": "7d",
  "reason": "批量严重违规"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_ids | array | 是 | 用户ID列表，最多20个 |
| duration | string | 是 | 封禁时长 |
| reason | string | 是 | 封禁原因 |

**响应格式**: 同批量禁言

---

### 8. 批量解除禁言

**端点**: `POST /api/content/moderation/batch-unmute/`

**权限**: `mute:BatchUnmute`

**描述**: 批量解除多个用户的禁言

**请求参数**:

```json
{
  "user_ids": [123, 456],
  "reason": "批量申诉成功"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_ids | array | 是 | 用户ID列表，最多20个 |
| reason | string | 否 | 解除原因 |

**响应格式**: 同批量禁言

---

### 9. 批量解除封禁

**端点**: `POST /api/content/moderation/batch-unban/`

**权限**: `ban:BatchUnban`

**描述**: 批量解除多个用户的封禁

**请求参数**:

```json
{
  "user_ids": [123, 456],
  "reason": "批量申诉成功"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_ids | array | 是 | 用户ID列表，最多20个 |
| reason | string | 否 | 解除原因 |

**响应格式**: 同批量禁言

---

### 10. 禁言列表查询

**端点**: `GET /api/content/moderation/mute-list/`

**权限**: `mute:Search`

**描述**: 查询禁言记录列表，支持多种筛选条件

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认20 |
| username | string | 否 | 用户名（模糊匹配） |
| user_id | integer | 否 | 用户ID（精确匹配） |
| status | string | 否 | 状态：`active`(禁言中)、`inactive`(已解除) |
| mute_type | string | 否 | 禁言类型：`manual`(手动)、`auto`(自动) |
| operator_id | integer | 否 | 操作人ID |
| start_date | string | 否 | 开始日期，格式：YYYY-MM-DD |
| end_date | string | 否 | 结束日期，格式：YYYY-MM-DD |
| is_permanent | boolean | 否 | 是否永久禁言 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "查询成功",
  "data": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "results": [
      {
        "id": 456,
        "user": {
          "id": 123,
          "username": "test_user",
          "avatar": "https://example.com/avatar.jpg"
        },
        "mute_type": "manual",
        "mute_type_display": "手动禁言",
        "muted_by": {
          "id": 1,
          "username": "admin"
        },
        "mute_reason": "发布违规内容",
        "muted_until": "2026-03-10T15:30:00Z",
        "is_active": true,
        "is_manually_modified": false,
        "create_datetime": "2026-03-07T15:30:00Z",
        "remaining_time": "还剩2天23小时"
      }
    ]
  }
}
```

---

### 11. 封禁列表查询

**端点**: `GET /api/content/moderation/ban-list/`

**权限**: `ban:Search`

**描述**: 查询封禁记录列表

**请求参数**: 类似禁言列表，但不包含 `mute_type` 参数

**响应格式**: 类似禁言列表

---

### 12. AI自动禁言列表查询

**端点**: `GET /api/content/moderation/auto-mute-list/`

**权限**: `autoMute:Search`

**描述**: 查询AI自动触发的禁言记录

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认20 |
| username | string | 否 | 用户名（模糊匹配） |
| status | string | 否 | 状态：`active`、`inactive`、`modified` |
| is_manually_modified | boolean | 否 | 是否被人工修改 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "查询成功",
  "data": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "results": [
      {
        "id": 789,
        "user": {
          "id": 123,
          "username": "test_user"
        },
        "mute_type": "auto",
        "mute_reason": "24小时内评论被拒绝6次",
        "muted_until": "2026-03-08T15:30:00Z",
        "is_active": true,
        "is_manually_modified": false,
        "auto_unmute_status": "pending",
        "auto_unmute_status_display": "等待自动解封",
        "create_datetime": "2026-03-07T15:30:00Z",
        "remaining_time": "还剩23小时"
      }
    ]
  }
}
```

**自动解封状态说明**:
- `pending`: 等待中（将自动解封）
- `completed`: 已解封
- `modified`: 已被人工修改（不会自动解封）

---

### 13. 操作日志查询

**端点**: `GET /api/content/moderation/logs/`

**权限**: `mute:Detail` 或 `ban:Detail` 或 `autoMute:Detail`

**描述**: 查询管理操作日志

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认20 |
| operator_id | integer | 否 | 操作人ID |
| target_user_id | integer | 否 | 目标用户ID |
| operation_type | string | 否 | 操作类型：`mute`、`unmute`、`ban`、`unban`、`modify_duration` |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "查询成功",
  "data": {
    "total": 200,
    "page": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1001,
        "operator": {
          "id": 1,
          "username": "admin"
        },
        "target_user": {
          "id": 123,
          "username": "test_user"
        },
        "operation_type": "mute",
        "operation_type_display": "禁言",
        "reason": "发布违规内容",
        "duration_hours": 72,
        "duration_display": "3天",
        "old_duration_hours": null,
        "ip_address": "192.168.1.1",
        "create_datetime": "2026-03-07T15:30:00Z",
        "extra_data": {}
      }
    ]
  }
}
```

---

### 14. 数据导出

**端点**: `GET /api/content/moderation/export/`

**权限**: `mute:Export` 或 `ban:Export` 或 `autoMute:Export`

**描述**: 导出禁言/封禁记录为CSV或Excel文件

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | 导出类型：`mute`(禁言)、`ban`(封禁)、`auto_mute`(AI自动禁言) |
| format | string | 是 | 文件格式：`csv` 或 `excel` |
| username | string | 否 | 用户名筛选 |
| status | string | 否 | 状态筛选 |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

**响应**: 文件下载

**文件名格式**: `{type}_export_{timestamp}.{ext}`

例如: `mute_export_20260307153000.csv`

---

## 权限说明

### 角色定义

系统定义了 `moderation_admin` 角色，拥有以下权限：

**禁言管理权限**:
- `mute:Search` - 查询禁言列表
- `mute:Create` - 添加禁言
- `mute:Unmute` - 解除禁言
- `mute:ModifyDuration` - 修改禁言时长
- `mute:BatchMute` - 批量禁言
- `mute:BatchUnmute` - 批量解除禁言
- `mute:Detail` - 查看详情
- `mute:Export` - 导出数据

**封禁管理权限**:
- `ban:Search` - 查询封禁列表
- `ban:Create` - 添加封禁
- `ban:Unban` - 解除封禁
- `ban:ModifyDuration` - 修改封禁时长
- `ban:BatchBan` - 批量封禁
- `ban:BatchUnban` - 批量解除封禁
- `ban:Detail` - 查看详情
- `ban:Export` - 导出数据

**AI自动禁言权限**:
- `autoMute:Search` - 查询AI自动禁言列表
- `autoMute:Unmute` - 解除AI自动禁言
- `autoMute:ModifyDuration` - 修改AI自动禁言时长
- `autoMute:Detail` - 查看详情
- `autoMute:Export` - 导出数据

### 权限分级规则

1. **超级管理员** (`is_superuser=True`)
   - 可以操作所有用户（包括普通管理员和普通用户）
   - 拥有所有权限

2. **普通管理员** (`is_staff=True` 且拥有 `moderation_admin` 角色)
   - 只能操作普通用户
   - 不能操作其他管理员
   - 拥有 `moderation_admin` 角色的所有权限

3. **限制规则**
   - 任何管理员都不能操作自己
   - 普通管理员尝试操作其他管理员时会返回权限不足错误

---

## 时长格式说明

系统支持以下时长格式：

| 格式 | 说明 | 示例 | 转换为小时 |
|------|------|------|-----------|
| `Xh` | X小时 | `3h` | 3小时 |
| `Xd` | X天 | `2d` | 48小时 |
| `Xw` | X周 | `1w` | 168小时 |
| `Xm` | X月（按30天计算） | `1m` | 720小时 |
| `permanent` | 永久 | `permanent` | NULL（永久） |

**示例**:
- `3h` - 3小时
- `1d` - 1天（24小时）
- `2w` - 2周（336小时）
- `1m` - 1个月（720小时）
- `permanent` - 永久

---

## AI自动禁言机制

### 触发条件

当用户在滚动时间窗口内的评论被AI拒绝次数达到阈值时，系统会自动触发禁言。

**默认配置**:
- 时间窗口: 24小时
- 拒绝次数阈值: 6次
- 自动禁言时长: 24小时

**配置方式**:

在环境变量中设置：

```bash
AUTO_MUTE_WINDOW_HOURS=24      # 滚动时间窗口（小时）
AUTO_MUTE_THRESHOLD=6          # 触发阈值
AUTO_MUTE_DURATION_HOURS=24    # 自动禁言时长（小时）
```

### 自动解封机制

AI自动禁言会创建Celery定时任务，在禁言到期时自动解除。

**自动解封规则**:
1. 如果禁言记录的 `is_manually_modified=False`，到期时自动解除
2. 如果禁言记录的 `is_manually_modified=True`（被管理员修改过），取消自动解封

**人工干预**:
- 管理员可以手动解除AI自动禁言
- 管理员可以修改AI自动禁言的时长
- 任何人工修改都会设置 `is_manually_modified=True`，取消自动解封任务

---

## 通知机制

系统会在以下情况发送通知：

### 禁言通知
- **触发时机**: 用户被禁言时
- **通知方式**: 消息中心 + 邮件
- **通知内容**: 禁言原因、时长/截止时间、禁言类型（手动/自动）

### 解除禁言通知
- **触发时机**: 禁言被解除时
- **通知方式**: 消息中心 + 邮件
- **通知内容**: 解除类型、解除原因（如有）

### 封禁通知
- **触发时机**: 用户被封禁时
- **通知方式**: 消息中心 + 邮件
- **通知内容**: 封禁原因、时长/截止时间

### 解除封禁通知
- **触发时机**: 封禁被解除时
- **通知方式**: 消息中心 + 邮件
- **通知内容**: 解除类型、解除原因（如有）

### 评论拒绝警告
- **触发时机**: 评论被AI拒绝但未达到自动禁言阈值时
- **通知方式**: 仅消息中心
- **通知内容**: 拒绝原因、当前次数、剩余机会、自动禁言后果说明

---

## 使用示例

### 示例1：禁言用户3天

```bash
curl -X POST "https://api.example.com/api/content/moderation/mute/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "duration": "3d",
    "reason": "发布违规内容"
  }'
```

### 示例2：永久封禁用户

```bash
curl -X POST "https://api.example.com/api/content/moderation/ban/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 456,
    "duration": "permanent",
    "reason": "严重违规，永久封禁"
  }'
```

### 示例3：批量禁言

```bash
curl -X POST "https://api.example.com/api/content/moderation/batch-mute/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": [123, 456, 789],
    "duration": "1d",
    "reason": "批量违规"
  }'
```

### 示例4：查询禁言列表

```bash
curl -X GET "https://api.example.com/api/content/moderation/mute-list/?page=1&page_size=20&status=active" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 示例5：导出禁言记录为CSV

```bash
curl -X GET "https://api.example.com/api/content/moderation/export/?type=mute&format=csv" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o mute_records.csv
```

---

## 注意事项

1. **权限验证**: 所有操作都会进行权限验证，确保操作人有足够的权限
2. **幂等性**: 解除操作支持幂等，重复解除已解除的用户不会报错
3. **事务完整性**: 所有涉及多表操作的业务逻辑都使用数据库事务，确保数据一致性
4. **降级策略**: 通知发送失败不会影响主流程，会记录错误日志但操作仍然成功
5. **批量操作限制**: 批量操作最多支持20个用户，超过会返回错误
6. **时长格式**: 时长格式必须符合规范，否则会返回格式错误提示
7. **日志记录**: 所有操作都会记录详细的操作日志，包括操作人、目标用户、操作时间、IP地址等

---

## 更新日志

### v1.0.0 (2026-03-07)
- 初始版本发布
- 实现手动禁言/封禁功能
- 实现AI自动禁言功能
- 实现批量操作功能
- 实现操作日志记录
- 实现通知机制
- 实现数据导出功能
