# MaiMaiNotePad API 接口文档

## 概述

本文档提供了 MaiMaiNotePad 后端系统的完整 API 接口说明，包括用户管理、知识库、人设卡、消息和管理功能等模块。

## 通用响应格式

所有 API 接口遵循统一的响应格式：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

分页响应格式：

```json
{
  "success": true,
  "message": "获取成功",
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 错误响应

```json
{
  "success": false,
  "message": "错误信息",
  "data": null,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 认证

大部分接口需要用户认证，通过 JWT Token 进行验证。在请求头中添加：

```
Authorization: Bearer {token}
```

---

## 用户管理接口

### 用户登录

- **路径**: `POST /token`
- **描述**: 用户登录获取访问令牌
- **参数**:
  - `username` (form): 用户名
  - `password` (form): 密码
- **响应**:
  ```json
  {
    "success": true,
    "message": "登录成功",
    "data": {
      "access_token": "jwt_token",
      "refresh_token": "refresh_token",
      "token_type": "bearer",
      "expires_in": 5184000,
      "user": {
        "id": "user_id",
        "username": "username",
        "email": "email@example.com",
        "role": "user"
      }
    }
  }
  ```

### 刷新令牌

- **路径**: `POST /refresh`
- **描述**: 刷新访问令牌
- **参数**:
  - `refresh_token` (form): 刷新令牌
- **响应**:
  ```json
  {
    "success": true,
    "message": "令牌刷新成功",
    "data": {
      "access_token": "new_access_token",
      "token_type": "bearer",
      "expires_in": 5184000
    }
  }
  ```

### 发送验证码

- **路径**: `POST /send_verification_code`
- **描述**: 发送邮箱验证码
- **参数**:
  - `email` (form): 邮箱地址
- **响应**:
  ```json
  {
    "success": true,
    "message": "验证码已发送",
    "data": null
  }
  ```

### 发送重置密码验证码

- **路径**: `POST /send_reset_password_code`
- **描述**: 发送重置密码验证码
- **参数**:
  - `email` (form): 邮箱地址
- **响应**:
  ```json
  {
    "success": true,
    "message": "重置密码验证码已发送",
    "data": null
  }
  ```

### 重置密码

- **路径**: `POST /reset_password`
- **描述**: 通过邮箱验证码重置密码
- **参数**:
  - `email` (form): 邮箱地址
  - `verification_code` (form): 验证码
  - `new_password` (form): 新密码
- **响应**:
  ```json
  {
    "success": true,
    "message": "密码重置成功",
    "data": null
  }
  ```

### 用户注册

- **路径**: `POST /user/register`
- **描述**: 用户注册
- **参数**:
  - `username` (form): 用户名
  - `password` (form): 密码
  - `email` (form): 邮箱
  - `verification_code` (form): 验证码
- **响应**:
  ```json
  {
    "success": true,
    "message": "注册成功",
    "data": null
  }
  ```

### 获取当前用户信息

- **路径**: `GET /users/me`
- **描述**: 获取当前用户信息
- **认证**: 需要 JWT Token
- **响应**:
  ```json
  {
    "success": true,
    "message": "用户信息获取成功",
    "data": {
      "id": "user_id",
      "username": "username",
      "email": "email@example.com",
      "role": "user",
      "avatar_url": "/path/to/avatar.jpg",
      "avatar_updated_at": "2024-01-01T12:00:00Z"
    }
  }
  ```

### 修改密码

- **路径**: `PUT /users/me/password`
- **描述**: 修改当前用户密码
- **认证**: 需要 JWT Token
- **参数**:
  ```json
  {
    "current_password": "当前密码",
    "new_password": "新密码",
    "confirm_password": "确认新密码"
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "message": "密码修改成功，请重新登录",
    "data": null
  }
  ```

### 上传头像

- **路径**: `POST /users/me/avatar`
- **描述**: 上传/更新用户头像
- **认证**: 需要 JWT Token
- **参数**:
  - `avatar` (file): 头像文件
- **响应**:
  ```json
  {
    "success": true,
    "message": "头像上传成功",
    "data": {
      "avatar_url": "/path/to/avatar.jpg",
      "avatar_updated_at": "2024-01-01T12:00:00Z"
    }
  }
  ```

### 删除头像

- **路径**: `DELETE /users/me/avatar`
- **描述**: 删除当前用户头像（恢复为默认头像）
- **认证**: 需要 JWT Token
- **响应**:
  ```json
  {
    "success": true,
    "message": "头像删除成功",
    "data": null
  }
  ```

### 获取用户头像

- **路径**: `GET /users/{user_id}/avatar`
- **描述**: 获取指定用户的头像
- **参数**:
  - `user_id` (path): 用户ID
  - `size` (query, default=200): 头像大小
- **响应**: 图片文件

### 获取用户Star记录

- **路径**: `GET /user/stars`
- **描述**: 获取当前用户的Star记录
- **认证**: 需要 JWT Token
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20, max=100): 每页数量
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取Star记录成功",
    "data": [],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### 获取用户上传历史

- **路径**: `GET /me/upload-history`
- **描述**: 获取当前用户的上传历史
- **认证**: 需要 JWT Token
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20): 每页条数，最大100
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取上传历史成功",
    "data": [],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### 获取用户上传统计

- **路径**: `GET /me/upload-stats`
- **描述**: 获取当前用户的上传统计信息
- **认证**: 需要 JWT Token
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取上传统计成功",
    "data": {
      "total_knowledge": 10,
      "total_persona": 5,
      "total_downloads": 100
    }
  }
  ```

---

## 知识库接口

### 上传知识库

- **路径**: `POST /knowledge/upload`
- **描述**: 上传知识库
- **认证**: 需要 JWT Token
- **参数**:
  - `files` (file): 知识库文件（支持多文件）
  - `name` (form): 知识库名称
  - `description` (form): 知识库描述
  - `copyright_owner` (form, optional): 版权所有者
  - `content` (form, optional): 内容
  - `tags` (form, optional): 标签
- **响应**:
  ```json
  {
    "success": true,
    "message": "知识库上传成功",
    "data": {
      "id": "kb_id",
      "name": "知识库名称",
      "description": "知识库描述",
      "uploader_id": "uploader_id",
      "is_public": false,
      "is_pending": true,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "downloads": 0,
      "star_count": 0,
      "tags": ["标签"],
      "copyright_owner": "版权所有者",
      "files": [],
      "content": "内容",
      "base_path": "[]",
      "download_url": "/api/knowledge/kb_id/download",
      "size": 1024,
      "author": "上传者用户名",
      "author_id": "uploader_id"
    }
  }
  ```

### 获取公开知识库

- **路径**: `GET /knowledge/public`
- **描述**: 获取所有公开的知识库
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20, max=100): 每页数量
  - `name` (query, optional): 按名称搜索
  - `uploader_id` (query, optional): 按上传者ID筛选
  - `sort_by` (query, default="created_at"): 排序字段(created_at, updated_at, star_count)
  - `sort_order` (query, default="desc"): 排序顺序(asc, desc)
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取公开知识库成功",
    "data": [
      {
        "id": "kb_id",
        "name": "知识库名称",
        "description": "知识库描述",
        "uploader_id": "uploader_id",
        "is_public": true,
        "is_pending": false,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "downloads": 10,
        "star_count": 5,
        "tags": ["标签1", "标签2"],
        "copyright_owner": "版权所有者",
        "files": [
          {
            "file_id": "file_id",
            "original_name": "原始文件名",
            "file_size": 1024
          }
        ],
        "content": "内容",
        "base_path": "[]",
        "download_url": "/api/knowledge/kb_id/download",
        "size": 1024,
        "author": "上传者用户名",
        "author_id": "uploader_id",
        "version": "1.0"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### 获取知识库详情

- **路径**: `GET /knowledge/{kb_id}`
- **描述**: 获取知识库基本信息
- **参数**:
  - `kb_id` (path): 知识库ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取知识库成功",
    "data": {
      "id": "kb_id",
      "name": "知识库名称",
      "description": "知识库描述",
      "uploader_id": "uploader_id",
      "is_public": true,
      "is_pending": false,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "downloads": 10,
      "star_count": 5,
      "tags": ["标签1", "标签2"],
      "copyright_owner": "版权所有者",
      "files": [
        {
          "file_id": "file_id",
          "original_name": "原始文件名",
          "file_size": 1024
        }
      ],
      "content": "内容",
      "base_path": "[]",
      "download_url": "/api/knowledge/kb_id/download",
      "size": 1024,
      "author": "上传者用户名",
      "author_id": "uploader_id",
      "version": "1.0"
    }
  }
  ```

### 检查知识库Star状态

- **路径**: `GET /knowledge/{kb_id}/starred`
- **描述**: 检查知识库是否已被当前用户Star
- **认证**: 需要 JWT Token
- **参数**:
  - `kb_id` (path): 知识库ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "检查Star状态成功",
    "data": {
      "starred": true
    }
  }
  ```

### 获取用户知识库

- **路径**: `GET /knowledge/user/{user_id}`
- **描述**: 获取指定用户上传的知识库
- **认证**: 需要 JWT Token
- **参数**:
  - `user_id` (path): 用户ID
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20, max=100): 每页数量
  - `name` (query, optional): 按名称搜索
  - `tag` (query, optional): 按标签搜索
  - `status` (query, default="all"): 状态过滤: all/pending/approved/rejected
  - `sort_by` (query, default="created_at"): 排序字段: created_at/updated_at/name/downloads/star_count
  - `sort_order` (query, default="desc"): 排序方向: asc/desc
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取用户知识库成功",
    "data": [
      {
        "id": "kb_id",
        "name": "知识库名称",
        "description": "知识库描述",
        "uploader_id": "uploader_id",
        "is_public": true,
        "is_pending": false,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "downloads": 10,
        "star_count": 5,
        "tags": ["标签1", "标签2"],
        "copyright_owner": "版权所有者",
        "files": [
          {
            "file_id": "file_id",
            "original_name": "原始文件名",
            "file_size": 1024
          }
        ],
        "content": "内容",
        "base_path": "[]",
        "download_url": "/api/knowledge/kb_id/download",
        "size": 1024,
        "author": "上传者用户名",
        "author_id": "uploader_id",
        "version": "1.0"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### Star知识库

- **路径**: `POST /knowledge/{kb_id}/star`
- **描述**: Star知识库（如果已Star则取消Star）
- **认证**: 需要 JWT Token
- **参数**:
  - `kb_id` (path): 知识库ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "Star成功",
    "data": null
  }
  ```

### 取消Star知识库

- **路径**: `DELETE /knowledge/{kb_id}/star`
- **描述**: 取消Star知识库
- **认证**: 需要 JWT Token
- **参数**:
  - `kb_id` (path): 知识库ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "取消Star成功",
    "data": null
  }
  ```

### 更新知识库

- **路径**: `PUT /knowledge/{kb_id}`
- **描述**: 修改知识库的基本信息
- **认证**: 需要 JWT Token
- **参数**:
  - `kb_id` (path): 知识库ID
  - `name` (form, optional): 知识库名称
  - `description` (form, optional): 知识库描述
  - `copyright_owner` (form, optional): 版权所有者
- **响应**:
  ```json
  {
    "success": true,
    "message": "修改知识库成功",
    "data": {
      "id": "kb_id",
      "name": "知识库名称",
      "description": "知识库描述",
      "uploader_id": "uploader_id",
      "is_public": true,
      "is_pending": false,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "downloads": 10,
      "star_count": 5,
      "tags": ["标签1", "标签2"],
      "copyright_owner": "版权所有者",
      "files": [
        {
          "file_id": "file_id",
          "original_name": "原始文件名",
          "file_size": 1024
        }
      ],
      "content": "内容",
      "base_path": "[]",
      "download_url": "/api/knowledge/kb_id/download",
      "size": 1024,
      "author": "上传者用户名",
      "author_id": "uploader_id",
      "version": "1.0"
    }
  }
  ```

### 向知识库添加文件

- **路径**: `POST /knowledge/{kb_id}/files`
- **描述**: 新增知识库中的文件
- **认证**: 需要 JWT Token
- **参数**:
  - `kb_id` (path): 知识库ID
  - `files` (file): 文件（支持多文件）
- **响应**:
  ```json
  {
    "success": true,
    "message": "文件添加成功",
    "data": null
  }
  ```

### 从知识库删除文件

- **路径**: `DELETE /knowledge/{kb_id}/{file_id}`
- **描述**: 删除知识库中的文件
- **认证**: 需要 JWT Token
- **参数**:
  - `kb_id` (path): 知识库ID
  - `file_id` (path): 文件ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "文件删除成功",
    "data": null
  }
  ```

### 删除知识库

- **路径**: `DELETE /knowledge/{kb_id}`
- **描述**: 删除知识库
- **认证**: 需要 JWT Token
- **参数**:
  - `kb_id` (path): 知识库ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "知识库删除成功",
    "data": null
  }
  ```

### 下载知识库

- **路径**: `GET /knowledge/{kb_id}/download`
- **描述**: 下载知识库文件
- **认证**: 需要 JWT Token
- **参数**:
  - `kb_id` (path): 知识库ID
- **响应**: 文件下载

### 获取知识库文件

- **路径**: `GET /knowledge/{kb_id}/file/{file_id}`
- **描述**: 获取知识库中的特定文件
- **认证**: 需要 JWT Token
- **参数**:
  - `kb_id` (path): 知识库ID
  - `file_id` (path): 文件ID
- **响应**: 文件内容

---

## 人设卡接口

### 上传人设卡

- **路径**: `POST /persona/upload`
- **描述**: 上传人设卡
- **认证**: 需要 JWT Token
- **参数**:
  - `files` (file): 人设卡文件（支持多文件）
  - `name` (form): 人设卡名称
  - `description` (form): 人设卡描述
  - `copyright_owner` (form, optional): 版权所有者
  - `content` (form, optional): 内容
  - `tags` (form, optional): 标签
- **响应**:
  ```json
  {
    "success": true,
    "message": "人设卡上传成功",
    "data": {
      "id": "pc_id",
      "name": "人设卡名称",
      "description": "人设卡描述",
      "uploader_id": "uploader_id",
      "is_public": false,
      "is_pending": true,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "downloads": 0,
      "star_count": 0,
      "tags": ["标签1", "标签2"],
      "copyright_owner": "版权所有者",
      "files": [],
      "content": "内容",
      "base_path": "base_path",
      "download_url": "/api/persona/pc_id/download",
      "size": 1024,
      "author": "上传者用户名",
      "author_id": "uploader_id",
      "version": "1.0",
      "stars": 0
    }
  }
  ```

### 获取公开人设卡

- **路径**: `GET /persona/public`
- **描述**: 获取所有公开的人设卡
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20, max=100): 每页数量
  - `name` (query, optional): 按名称搜索
  - `uploader_id` (query, optional): 按上传者ID筛选
  - `sort_by` (query, default="created_at"): 排序字段(created_at, updated_at, star_count)
  - `sort_order` (query, default="desc"): 排序顺序(asc, desc)
- **响应**:
  ```json
  {
    "success": true,
    "message": "公开人设卡获取成功",
    "data": [
      {
        "id": "pc_id",
        "name": "人设卡名称",
        "description": "人设卡描述",
        "uploader_id": "uploader_id",
        "is_public": true,
        "is_pending": false,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "downloads": 10,
        "star_count": 5,
        "tags": ["标签1", "标签2"],
        "copyright_owner": "版权所有者",
        "files": [
          {
            "file_id": "file_id",
            "original_name": "原始文件名",
            "file_size": 1024
          }
        ],
        "content": "内容",
        "base_path": "base_path",
        "download_url": "/api/persona/pc_id/download",
        "size": 1024,
        "author": "上传者用户名",
        "author_id": "uploader_id",
        "version": "1.0",
        "stars": 5
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### 获取人设卡详情

- **路径**: `GET /persona/{pc_id}`
- **描述**: 获取人设卡详情
- **参数**:
  - `pc_id` (path): 人设卡ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "人设卡详情获取成功",
    "data": {
      "id": "pc_id",
      "name": "人设卡名称",
      "description": "人设卡描述",
      "uploader_id": "uploader_id",
      "is_public": true,
      "is_pending": false,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "downloads": 10,
      "star_count": 5,
      "tags": ["标签1", "标签2"],
      "copyright_owner": "版权所有者",
      "files": [
        {
          "file_id": "file_id",
          "original_name": "原始文件名",
          "file_size": 1024
        }
      ],
      "content": "内容",
      "base_path": "base_path",
      "download_url": "/api/persona/pc_id/download",
      "size": 1024,
      "author": "上传者用户名",
      "author_id": "uploader_id",
      "version": "1.0",
      "stars": 5
    }
  }
  ```

### 检查人设卡Star状态

- **路径**: `GET /persona/{pc_id}/starred`
- **描述**: 检查人设卡是否已被当前用户Star
- **认证**: 需要 JWT Token
- **参数**:
  - `pc_id` (path): 人设卡ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "Star状态检查成功",
    "data": {
      "starred": true
    }
  }
  ```

### 获取用户人设卡

- **路径**: `GET /persona/user/{user_id}`
- **描述**: 获取指定用户的人设卡
- **认证**: 需要 JWT Token
- **参数**:
  - `user_id` (path): 用户ID
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20, max=100): 每页数量
  - `name` (query, optional): 按名称搜索
  - `tag` (query, optional): 按标签搜索
  - `status` (query, default="all"): 状态过滤: all/pending/approved/rejected
  - `sort_by` (query, default="created_at"): 排序字段: created_at/updated_at/name/downloads/star_count
  - `sort_order` (query, default="desc"): 排序方向: asc/desc
- **响应**:
  ```json
  {
    "success": true,
    "message": "用户人设卡获取成功",
    "data": [
      {
        "id": "pc_id",
        "name": "人设卡名称",
        "description": "人设卡描述",
        "uploader_id": "uploader_id",
        "is_public": true,
        "is_pending": false,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "downloads": 10,
        "star_count": 5,
        "tags": ["标签1", "标签2"],
        "copyright_owner": "版权所有者",
        "files": [
          {
            "file_id": "file_id",
            "original_name": "原始文件名",
            "file_size": 1024
          }
        ],
        "content": "内容",
        "base_path": "base_path",
        "download_url": "/api/persona/pc_id/download",
        "size": 1024,
        "author": "上传者用户名",
        "author_id": "uploader_id",
      "version": "1.0",
      "stars": 5
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### 更新人设卡

- **路径**: `PUT /persona/{pc_id}`
- **描述**: 修改人设卡信息
- **认证**: 需要 JWT Token
- **参数**:
  - `pc_id` (path): 人设卡ID
  - `name` (form): 人设卡名称
  - `description` (form): 人设卡描述
  - `copyright_owner` (form, optional): 版权所有者
- **响应**:
  ```json
  {
    "success": true,
    "message": "人设卡更新成功",
    "data": {
      "id": "pc_id",
      "name": "人设卡名称",
      "description": "人设卡描述",
      "uploader_id": "uploader_id",
      "is_public": true,
      "is_pending": false,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "downloads": 10,
      "star_count": 5,
      "tags": ["标签1", "标签2"],
      "copyright_owner": "版权所有者",
      "files": [
        {
          "file_id": "file_id",
          "original_name": "原始文件名",
          "file_size": 1024
        }
      ],
      "content": "内容",
      "base_path": "base_path",
      "download_url": "/api/persona/pc_id/download",
      "size": 1024,
      "author": "上传者用户名",
      "author_id": "uploader_id",
      "version": "1.0",
      "stars": 5
    }
  }
  ```

### Star人设卡

- **路径**: `POST /persona/{pc_id}/star`
- **描述**: Star人设卡（如果已Star则取消Star）
- **认证**: 需要 JWT Token
- **参数**:
  - `pc_id` (path): 人设卡ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "Star成功",
    "data": null
  }
  ```

### 取消Star人设卡

- **路径**: `DELETE /persona/{pc_id}/star`
- **描述**: 取消Star人设卡
- **认证**: 需要 JWT Token
- **参数**:
  - `pc_id` (path): 人设卡ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "取消Star成功",
    "data": null
  }
  ```

### 删除人设卡

- **路径**: `DELETE /persona/{pc_id}`
- **描述**: 删除人设卡
- **认证**: 需要 JWT Token
- **参数**:
  - `pc_id` (path): 人设卡ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "人设卡删除成功",
    "data": null
  }
  ```

### 向人设卡添加文件

- **路径**: `POST /persona/{pc_id}/files`
- **描述**: 向人设卡添加文件
- **认证**: 需要 JWT Token
- **参数**:
  - `pc_id` (path): 人设卡ID
  - `files` (file): 文件（支持多文件）
- **响应**:
  ```json
  {
    "success": true,
    "message": "文件添加成功",
    "data": null
  }
  ```

### 从人设卡删除文件

- **路径**: `DELETE /persona/{pc_id}/{file_id}`
- **描述**: 从人设卡删除文件
- **认证**: 需要 JWT Token
- **参数**:
  - `pc_id` (path): 人设卡ID
  - `file_id` (path): 文件ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "文件删除成功",
    "data": null
  }
  ```

### 下载人设卡

- **路径**: `GET /persona/{pc_id}/download`
- **描述**: 下载人设卡文件
- **认证**: 需要 JWT Token
- **参数**:
  - `pc_id` (path): 人设卡ID
- **响应**: 文件下载

### 获取人设卡文件

- **路径**: `GET /persona/{pc_id}/file/{file_id}`
- **描述**: 获取人设卡中的特定文件
- **认证**: 需要 JWT Token
- **参数**:
  - `pc_id` (path): 人设卡ID
  - `file_id` (path): 文件ID
- **响应**: 文件内容

---

## 消息接口

### 发送消息

- **路径**: `POST /messages/send`
- **描述**: 发送消息
- **认证**: 需要 JWT Token
- **参数**:
  ```json
  {
    "recipient_id": "接收者ID",
    "recipient_ids": ["接收者ID列表"],
    "title": "消息标题",
    "content": "消息内容",
    "summary": "消息摘要",
    "message_type": "消息类型(direct/announcement)",
    "broadcast_scope": "广播范围(all_users)"
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "message": "消息发送成功",
    "data": {
      "message_ids": ["消息ID列表"],
      "status": "sent",
      "count": 1
    }
  }
  ```

### 获取消息详情

- **路径**: `GET /messages/{message_id}`
- **描述**: 获取消息详情
- **认证**: 需要 JWT Token
- **参数**:
  - `message_id` (path): 消息ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "消息详情获取成功",
    "data": {
      "id": "message_id",
      "sender_id": "发送者ID",
      "recipient_id": "接收者ID",
      "title": "消息标题",
      "content": "消息内容",
      "summary": "消息摘要",
      "message_type": "消息类型",
      "broadcast_scope": "广播范围",
      "is_read": false,
      "created_at": "2024-01-01T12:00:00Z"
    }
  }
  ```

### 获取消息列表

- **路径**: `GET /messages`
- **描述**: 获取消息列表
- **认证**: 需要 JWT Token
- **参数**:
  - `other_user_id` (query, optional): 与特定用户的对话ID
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20): 每页数量
- **响应**:
  ```json
  {
    "success": true,
    "message": "消息列表获取成功",
    "data": [
      {
        "id": "message_id",
        "sender_id": "发送者ID",
        "recipient_id": "接收者ID",
        "title": "消息标题",
        "content": "消息内容",
        "summary": "消息摘要",
        "message_type": "消息类型",
        "broadcast_scope": "广播范围",
        "is_read": false,
        "created_at": "2024-01-01T12:00:00Z"
      }
    ]
  }
  ```

### 标记消息为已读

- **路径**: `POST /messages/{message_id}/read`
- **描述**: 标记消息为已读
- **认证**: 需要 JWT Token
- **参数**:
  - `message_id` (path): 消息ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "消息已标记为已读",
    "data": null
  }
  ```

### 删除消息

- **路径**: `DELETE /messages/{message_id}`
- **描述**: 删除消息
- **认证**: 需要 JWT Token
- **参数**:
  - `message_id` (path): 消息ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "消息已删除",
    "data": {
      "deleted_count": 1
    }
  }
  ```

### 更新消息

- **路径**: `PUT /messages/{message_id}`
- **描述**: 修改消息
- **认证**: 需要 JWT Token
- **参数**:
  - `message_id` (path): 消息ID
  - `title` (body, optional): 消息标题
  - `content` (body, optional): 消息内容
  - `summary` (body, optional): 消息摘要
- **响应**:
  ```json
  {
    "success": true,
    "message": "消息已更新",
    "data": {
      "updated_count": 1
    }
  }
  ```

### 获取广播消息历史

- **路径**: `GET /admin/broadcast-messages`
- **描述**: 获取广播消息历史（仅限admin和moderator）
- **认证**: 需要 JWT Token（admin或moderator权限）
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20): 每页数量
- **响应**:
  ```json
  {
    "success": true,
    "message": "广播消息历史获取成功",
    "data": [
      {
        "id": "message_id",
        "sender_id": "发送者ID",
        "recipient_id": "接收者ID",
        "title": "消息标题",
        "content": "消息内容",
        "summary": "消息摘要",
        "message_type": "消息类型",
        "broadcast_scope": "广播范围",
        "is_read": false,
        "created_at": "2024-01-01T12:00:00Z"
      }
    ]
  }
  ```

---

## 管理员接口

### 获取管理员统计数据

- **路径**: `GET /admin/stats`
- **描述**: 获取管理员统计数据（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取统计数据成功",
    "data": {
      "totalUsers": 100,
      "totalKnowledge": 50,
      "totalPersonas": 30,
      "pendingKnowledge": 5,
      "pendingPersonas": 3
    }
  }
  ```

### 获取最近注册用户

- **路径**: `GET /admin/recent-users`
- **描述**: 获取最近注册的用户列表（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `page_size` (query, default=10): 每页数量
  - `page` (query, default=1): 页码
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取最近用户成功",
    "data": [
      {
        "id": "user_id",
        "username": "用户名",
        "email": "邮箱",
        "role": "角色",
        "createdAt": "2024-01-01T12:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total": 100,
      "total_pages": 10
    }
  }
  ```

### 获取所有用户

- **路径**: `GET /admin/users`
- **描述**: 获取所有用户列表（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `page_size` (query, default=20): 每页数量
  - `page` (query, default=1): 页码
  - `search` (query, optional): 搜索用户名或邮箱
  - `role` (query, optional): 按角色筛选（admin/moderator/user）
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取用户列表成功",
    "data": [
      {
        "id": "user_id",
        "username": "用户名",
        "email": "邮箱",
        "role": "角色",
        "is_active": true,
        "createdAt": "2024-01-01T12:00:00Z",
        "knowledgeCount": 5,
        "personaCount": 3
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### 更新用户角色

- **路径**: `PUT /admin/users/{user_id}/role`
- **描述**: 更新用户角色（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `user_id` (path): 用户ID
  - `role` (body): 角色 (user/moderator/admin)
- **响应**:
  ```json
  {
    "success": true,
    "message": "用户角色更新成功",
    "data": {
      "id": "user_id",
      "username": "用户名",
      "role": "新角色"
    }
  }
  ```

### 删除用户

- **路径**: `DELETE /admin/users/{user_id}`
- **描述**: 删除用户（仅限admin，软删除）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `user_id` (path): 用户ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "用户删除成功",
    "data": null
  }
  ```

### 管理员创建用户

- **路径**: `POST /admin/users`
- **描述**: 创建新用户（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  ```json
  {
    "username": "用户名",
    "email": "邮箱",
    "password": "密码",
    "role": "user/moderator/admin"
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "message": "用户创建成功",
    "data": {
      "id": "用户ID",
      "username": "用户名",
      "email": "邮箱",
      "role": "角色"
    }
  }
  ```

### 获取所有知识库（管理员视图）

- **路径**: `GET /admin/knowledge/all`
- **描述**: 获取所有知识库（管理员视图，仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20): 每页数量
  - `status` (query, optional): 状态筛选（pending/approved/rejected）
  - `search` (query, optional): 搜索名称或描述
  - `uploader` (query, optional): 上传者ID或用户名
  - `order_by` (query, default="created_at"): 排序字段
  - `order_dir` (query, default="desc"): 排序方向
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取知识库成功",
    "data": [
      {
        "id": "kb_id",
        "name": "知识库名称",
        "description": "知识库描述",
        "uploader_id": "uploader_id",
        "is_public": true,
        "is_pending": false,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "downloads": 10,
        "star_count": 5,
        "tags": ["标签1", "标签2"],
        "copyright_owner": "版权所有者",
        "files": [
          {
            "file_id": "file_id",
            "original_name": "原始文件名",
            "file_size": 1024
          }
        ],
        "content": "内容",
        "base_path": "[]",
        "download_url": "/api/knowledge/kb_id/download",
        "size": 1024,
        "author": "上传者用户名",
        "author_id": "uploader_id",
        "version": "1.0"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### 获取所有人设卡（管理员视图）

- **路径**: `GET /admin/persona/all`
- **描述**: 获取所有人设卡（管理员视图，仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20): 每页数量
  - `status` (query, optional): 状态筛选（pending/approved/rejected）
  - `search` (query, optional): 搜索名称或描述
  - `uploader` (query, optional): 上传者ID或用户名
  - `order_by` (query, default="created_at"): 排序字段
  - `order_dir` (query, default="desc"): 排序方向
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取人设卡成功",
    "data": [
      {
        "id": "pc_id",
        "name": "人设卡名称",
        "description": "人设卡描述",
        "uploader_id": "uploader_id",
        "is_public": true,
        "is_pending": false,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "downloads": 10,
        "star_count": 5,
        "tags": ["标签1", "标签2"],
        "copyright_owner": "版权所有者",
        "files": [
          {
            "file_id": "file_id",
            "original_name": "原始文件名",
            "file_size": 1024
          }
        ],
        "content": "内容",
        "base_path": "base_path",
        "download_url": "/api/persona/pc_id/download",
        "size": 1024,
        "author": "上传者用户名",
        "author_id": "uploader_id",
        "version": "1.0",
        "stars": 5
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### 撤销知识库审核

- **路径**: `POST /admin/knowledge/{kb_id}/revert`
- **描述**: 撤销知识库审核状态（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `kb_id` (path): 知识库ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "知识库审核状态已撤销",
    "data": null
  }
  ```

### 撤销人设卡审核

- **路径**: `POST /admin/persona/{pc_id}/revert`
- **描述**: 撤销人设卡审核状态（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `pc_id` (path): 人设卡ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "人设卡审核状态已撤销",
    "data": null
  }
  ```

### 获取上传历史（管理员）

- **路径**: `GET /admin/upload-history`
- **描述**: 获取上传历史（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=20): 每页数量
  - `type` (query, optional): 上传类型 (knowledge/persona)
  - `status` (query, optional): 状态 (pending/approved/rejected)
  - `uploader` (query, optional): 上传者ID或用户名
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取上传历史成功",
    "data": [
      {
        "id": "record_id",
        "uploader_id": "上传者ID",
        "target_id": "目标ID",
        "target_type": "目标类型",
        "name": "名称",
        "description": "描述",
        "status": "状态",
        "created_at": "2024-01-01T12:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
  ```

### 获取上传统计（管理员）

- **路径**: `GET /admin/upload-stats`
- **描述**: 获取上传统计信息（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取上传统计成功",
    "data": {
      "total_knowledge": 50,
      "total_persona": 30,
      "pending_knowledge": 5,
      "pending_persona": 3,
      "today_knowledge": 2,
      "today_persona": 1
    }
  }
  ```

### 批量删除消息

- **路径**: `POST /admin/messages/batch-delete`
- **描述**: 批量删除消息（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  ```json
  {
    "message_ids": ["消息ID列表"]
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "message": "消息批量删除成功",
    "data": {
      "deleted_count": 5
    }
  }
  ```

### 删除上传记录

- **路径**: `DELETE /admin/uploads/{upload_id}`
- **描述**: 删除上传记录（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `upload_id` (path): 上传记录ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "上传记录删除成功",
    "data": null
  }
  ```

### 重新处理上传

- **路径**: `POST /admin/uploads/{upload_id}/reprocess`
- **描述**: 重新处理上传（仅限admin）
- **认证**: 需要 JWT Token（admin权限）
- **参数**:
  - `upload_id` (path): 上传记录ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "上传重新处理成功",
    "data": null
  }
  ```

---

## 审核接口

### 获取待审核知识库

- **路径**: `GET /review/knowledge/pending`
- **描述**: 获取待审核的知识库（需要admin或moderator权限）
- **认证**: 需要 JWT Token（admin或moderator权限）
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=10, max=100): 每页数量
  - `name` (query, optional): 按名称搜索
  - `uploader_id` (query, optional): 按上传者ID筛选
  - `sort_by` (query, default="created_at"): 排序字段
  - `sort_order` (query, default="desc"): 排序方式
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取待审核知识库成功",
    "data": [
      {
        "id": "kb_id",
        "name": "知识库名称",
        "description": "知识库描述",
        "uploader_id": "uploader_id",
        "is_public": false,
        "is_pending": true,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "downloads": 0,
        "star_count": 0,
        "tags": ["标签1", "标签2"],
        "copyright_owner": "版权所有者",
        "files": [
          {
            "file_id": "file_id",
            "original_name": "原始文件名",
            "file_size": 1024
          }
        ],
        "content": "内容",
        "base_path": "[]",
        "download_url": "/api/knowledge/kb_id/download",
        "size": 1024,
        "author": "上传者用户名",
        "author_id": "uploader_id",
        "version": "1.0"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total": 100,
      "total_pages": 10
    }
  }
  ```

### 获取待审核人设卡

- **路径**: `GET /review/persona/pending`
- **描述**: 获取待审核的人设卡（需要admin或moderator权限）
- **认证**: 需要 JWT Token（admin或moderator权限）
- **参数**:
  - `page` (query, default=1): 页码
  - `page_size` (query, default=10, max=100): 每页数量
  - `name` (query, optional): 按名称搜索
  - `uploader_id` (query, optional): 按上传者ID筛选
  - `sort_by` (query, default="created_at"): 排序字段
  - `sort_order` (query, default="desc"): 排序方式
- **响应**:
  ```json
  {
    "success": true,
    "message": "获取待审核人设卡成功",
    "data": [
      {
        "id": "pc_id",
        "name": "人设卡名称",
        "description": "人设卡描述",
        "uploader_id": "uploader_id",
        "is_public": false,
        "is_pending": true,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "downloads": 0,
        "star_count": 0,
        "tags": ["标签1", "标签2"],
        "copyright_owner": "版权所有者",
        "files": [
          {
            "file_id": "file_id",
            "original_name": "原始文件名",
            "file_size": 1024
          }
        ],
        "content": "内容",
        "base_path": "base_path",
        "download_url": "/api/persona/pc_id/download",
        "size": 1024,
        "author": "上传者用户名",
        "author_id": "uploader_id",
        "version": "1.0",
        "stars": 0
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total": 100,
      "total_pages": 10
    }
  }
  ```

### 审核通过知识库

- **路径**: `POST /review/knowledge/{kb_id}/approve`
- **描述**: 审核通过知识库（需要admin或moderator权限）
- **认证**: 需要 JWT Token（admin或moderator权限）
- **参数**:
  - `kb_id` (path): 知识库ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "审核通过",
    "data": null
  }
  ```

### 审核拒绝知识库

- **路径**: `POST /review/knowledge/{kb_id}/reject`
- **描述**: 审核拒绝知识库（需要admin或moderator权限）
- **认证**: 需要 JWT Token（admin或moderator权限）
- **参数**:
  - `kb_id` (path): 知识库ID
  - `reason` (body): 拒绝原因
- **响应**:
  ```json
  {
    "success": true,
    "message": "审核拒绝，已发送通知",
    "data": null
  }
  ```

### 审核通过人设卡

- **路径**: `POST /review/persona/{pc_id}/approve`
- **描述**: 审核通过人设卡（需要admin或moderator权限）
- **认证**: 需要 JWT Token（admin或moderator权限）
- **参数**:
  - `pc_id` (path): 人设卡ID
- **响应**:
  ```json
  {
    "success": true,
    "message": "审核通过",
    "data": null
  }
  ```

### 审核拒绝人设卡

- **路径**: `POST /review/persona/{pc_id}/reject`
- **描述**: 审核拒绝人设卡（需要admin或moderator权限）
- **认证**: 需要 JWT Token（admin或moderator权限）
- **参数**:
  - `pc_id` (path): 人设卡ID
  - `reason` (body): 拒绝原因
- **响应**:
  ```json
  {
    "success": true,
    "message": "审核拒绝，已发送通知",
    "data": null
  }
  ```
