# MaiMaiNotePad 用户前端（mai_f_old）

面向普通用户的前端应用，基于 Vue 3 + Vite + Element Plus 构建，提供知识库广场、人设卡广场、文件上传下载、收藏、评论、消息通知等完整的用户交互界面。

对应后端项目：`../backend`（Django + DRF）

## 技术栈

- Vue 3（`<script setup>` 风格）
- Vite 7 构建工具
- Element Plus UI 组件库
- Pinia 状态管理
- Vue Router 4 路由管理
- Axios HTTP 客户端
- ECharts 数据可视化
- Monaco Editor 代码预览
- WebSocket 实时通信
- Tippy.js 工具提示
- vue3-calendar-heatmap 热力图

## 项目结构

```
mai_f_old/
├── src/
│   ├── api/                    # API 接口封装
│   │   ├── index.js            # Axios 实例、拦截器、Token 自动刷新
│   │   ├── user.js             # 用户相关接口
│   │   ├── knowledge.js        # 知识库相关接口
│   │   ├── persona.js          # 人设卡相关接口
│   │   ├── comments.js         # 评论相关接口
│   │   ├── messages.js         # 站内消息接口
│   │   ├── stats.js            # 统计数据接口
│   │   ├── admin.js            # 管理员接口
│   │   └── dictionary.js       # 数据字典接口
│   ├── components/             # 公共组件
│   │   ├── CommentSection.vue  # 评论区组件
│   │   ├── FileListTable.vue   # 文件列表表格
│   │   ├── FileViewerDialog.vue # 文件预览对话框
│   │   ├── MyRepoList.vue      # 我的仓库列表
│   │   └── ReviewList.vue      # 审核列表组件
│   ├── composables/            # 组合式函数
│   │   └── useFileViewer.js    # 文件预览/下载统一逻辑
│   ├── router/
│   │   └── index.js            # 路由配置与导航守卫
│   ├── stores/                 # Pinia 状态管理
│   │   ├── user.js             # 用户信息与角色
│   │   ├── knowledge.js        # 知识库状态
│   │   ├── persona.js          # 人设卡状态
│   │   ├── messages.js         # 消息状态
│   │   ├── stats.js            # 统计数据状态
│   │   └── connection.js       # WebSocket 连接状态
│   ├── utils/                  # 工具函数
│   │   ├── api.js              # 统一通知、错误处理、格式化工具
│   │   ├── author.js           # 作者信息展示工具
│   │   └── websocket.js        # WebSocket 管理（心跳、重连、状态订阅）
│   ├── views/                  # 页面视图
│   │   ├── auth/               # 认证页面
│   │   ├── layout/             # 布局组件
│   │   ├── persona/            # 人设卡模块
│   │   ├── knowledge/          # 知识库模块
│   │   ├── favorites/          # 收藏模块
│   │   ├── admin/              # 管理员模块
│   │   └── user/               # 用户中心
│   ├── App.vue                 # 根组件
│   ├── main.js                 # 入口文件
│   └── style.css               # 全局样式
├── .env.development            # 开发环境配置
├── .env.production             # 生产环境配置
├── api_documentation.md        # API 使用文档
├── vite.config.js              # Vite 配置（含代理）
└── package.json                # 依赖配置
```

## 快速开始

### 环境要求

- Node.js >= 16
- 后端服务运行在 `http://localhost:8000`

### 安装与运行

```bash
# 安装依赖
npm install

# 开发模式启动
npm run dev

# 构建生产版本
npm run build

# 预览构建产物
npm run preview
```

### 环境变量

开发环境（`.env.development`）：
```
VITE_API_BASE_URL=/api
```

生产环境（`.env.production`）：
```
VITE_API_BASE_URL=https://your-production-api.com/api
```

开发模式下 Vite 会将 `/api` 和 `/media` 请求代理到 `http://localhost:8000`。

## 页面路由

### 公开页面（无需登录）

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | Login | 用户登录 |
| `/register` | Register | 用户注册 |
| `/verify-email` | VerifyEmail | 邮箱验证 |
| `/reset-password` | ResetPassword | 重置密码 |

### 用户页面（需登录，嵌套在 Home 布局内）

| 路径 | 页面 | 说明 |
|------|------|------|
| `/persona-card` | PersonaCard | 人设卡广场（默认首页） |
| `/my-persona` | MyPersona | 我的人设卡管理 |
| `/persona-upload` | PersonaUpload | 创建/上传人设卡 |
| `/knowledge-base` | KnowledgeBase | 知识库广场 |
| `/my-knowledge` | MyKnowledge | 我的知识库管理 |
| `/knowledge-upload` | KnowledgeUpload | 上传知识库 |
| `/favorite-persona` | FavoritePersona | 收藏的人设卡 |
| `/favorite-knowledge` | FavoriteKnowledge | 收藏的知识库 |
| `/user-center` | UserCenter | 个人中心 |

### 管理员页面（需管理员权限）

| 路径 | 页面 | 说明 |
|------|------|------|
| `/persona-review` | PersonaReview | 人设卡审核 |
| `/knowledge-review` | KnowledgeReview | 知识库审核 |
| `/admin-dashboard` | AdminDashboard | 运营看板 |
| `/admin-users` | AdminUserManagement | 用户管理 |
| `/admin-mute` | AdminMuteManagement | 禁言管理 |
| `/admin-announcement` | AdminAnnouncement | 发布公告 |

## 核心功能

### 认证与 Token 管理

- JWT 认证，Token 存储在 `localStorage`
- 请求头格式：`Authorization: JWT {access_token}`
- 401 响应自动触发 Token 刷新（`/api/token/refresh/`）
- 刷新失败自动跳转登录页
- 并发请求排队等待 Token 刷新完成后统一重试

### 响应拦截

后端成功响应格式为 `{ code: 2000, msg: "...", data: {...} }`，前端拦截器在 `code === 2000` 时：
- 设置 `response.success = true`
- 将 `msg` 映射为 `message`
- 直接返回 `response.data`（解包后的对象）

### WebSocket 实时通信

- 连接地址：`ws://{host}:{port}/ws/{token}/`
- 心跳间隔：20 秒
- 指数退避重连：3s → 6s → 12s → ... 最大 60s，最多 10 次
- 页面切回前台自动检测并重连
- 状态订阅机制：`subscribeStatus(listener)` / `unsubscribeStatus(listener)`

### 统一工具函数

`utils/api.js` 提供：
- `handleApiResponse` / `handleApiError`：统一 API 响应/错误处理
- `showSuccessNotification` / `showErrorNotification` / `showWarningNotification`：全局通知（玻璃拟态样式，支持复制内容）
- `formatDate` / `formatFileSize` / `normalizeTags`：格式化工具

### 文件预览与下载

`composables/useFileViewer.js` 提供统一的文件操作逻辑：
- 支持 TOML / JSON / TXT 等文本文件在线预览
- 单文件下载与整库压缩包下载
- 权限校验与错误处理

## 角色权限

| 角色 | 说明 | 可访问模块 |
|------|------|-----------|
| `user` | 普通用户 | 广场、我的、收藏、个人中心 |
| `moderator` | 审核员 | 以上 + 审核页面 |
| `admin` | 管理员 | 以上 + 用户管理、禁言管理、公告、运营看板 |
| `super_admin` | 超级管理员 | 全部权限，可管理管理员账号 |

左侧菜单根据用户角色动态显示管理入口（后端通过 `is_admin` / `is_super_admin` 字段控制）。

## 与后端的对接

- 后端 API 基础地址由 `VITE_API_BASE_URL` 环境变量配置
- 认证方式：JWT Token（`JWT` 前缀，非 `Bearer`）
- 后端成功响应：`{ code: 2000, msg: "...", data: {...} }`
- 分页接口解包后：`response.data` 为数组，`response.total` 为总数
- 后端时间字段：`create_datetime` / `update_datetime`
- 后端框架：Django + DRF（dvadmin 兼容层）

## 开发约定

- 所有 API 请求通过 `src/api/` 下的封装发起，不在视图中直接拼接 URL
- 错误处理统一使用 `utils/api.js` 中的工具函数
- 时间展示使用 `formatDate`，文件大小使用 `formatFileSize`
- 作者信息使用 `utils/author.js` 中的 `getAuthorName` / `getAuthorDisplay`
- 文件预览/下载使用 `composables/useFileViewer.js`
- 新增页面在 `src/views/` 下创建，对应 API 在 `src/api/` 下添加，路由在 `router/index.js` 中注册
