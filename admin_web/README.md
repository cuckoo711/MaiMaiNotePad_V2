# MaiMaiNotePad 管理后台前端（admin_web）

管理后台前端项目，基于 [django-vue3-admin](https://gitee.com/huge-dream/django-vue3-admin) 框架二次开发，提供内容审核、用户管理、数据统计等后台管理功能。

## 技术栈

- Vue 3 + Composition API + TypeScript
- Vite 5 构建工具
- Element Plus UI 组件库
- Fast-Crud 快速 CRUD 框架
- Pinia 状态管理
- Vue Router 4 路由管理
- vue-i18n 国际化
- ECharts 数据可视化
- WebSocket 实时通信
- Sass + Tailwind CSS 样式

## 项目结构

```
admin_web/
├── src/
│   ├── api/                    # API 接口定义
│   │   ├── login/              # 登录相关接口
│   │   └── menu/               # 菜单相关接口
│   ├── components/             # 公共组件
│   │   ├── auth/               # 权限组件
│   │   ├── editor/             # 富文本编辑器
│   │   ├── table/              # 表格组件
│   │   ├── importExcel/        # Excel 导入组件
│   │   ├── fileSelector/       # 文件选择器
│   │   └── ...                 # 其他通用组件
│   ├── composables/            # 组合式函数
│   │   └── content/            # 内容管理相关
│   │       ├── useBatchOperation.ts    # 批量操作
│   │       ├── useDataExport.ts        # 数据导出
│   │       ├── useDataImport.ts        # 数据导入
│   │       ├── searchUtils.ts          # 搜索工具
│   │       └── permissionControlUtils.ts # 权限控制
│   ├── directive/              # 自定义指令
│   │   ├── authDirective.ts    # 权限指令
│   │   └── sizeDirective.ts    # 尺寸指令
│   ├── i18n/                   # 国际化配置
│   ├── layout/                 # 布局组件
│   ├── plugin/                 # 插件
│   │   └── permission/         # 权限插件
│   ├── router/                 # 路由配置
│   │   ├── backEnd.ts          # 后端控制路由
│   │   ├── frontEnd.ts         # 前端控制路由
│   │   └── route.ts            # 路由定义
│   ├── stores/                 # Pinia 状态管理
│   │   ├── userInfo.ts         # 用户信息
│   │   ├── messageCenter.ts    # 消息中心
│   │   ├── btnPermission.ts    # 按钮权限
│   │   ├── columnPermission.ts # 列权限
│   │   ├── dictionary.ts       # 数据字典
│   │   ├── systemConfig.ts     # 系统配置
│   │   └── themeConfig.ts      # 主题配置
│   ├── theme/                  # 主题样式
│   ├── types/                  # TypeScript 类型定义
│   ├── utils/                  # 工具函数
│   │   ├── request.ts          # Axios 请求封装
│   │   ├── baseUrl.ts          # 基础 URL 处理
│   │   ├── websocket.ts        # WebSocket 工具
│   │   ├── authFunction.ts     # 权限校验函数
│   │   ├── commonCrud.ts       # 通用 CRUD 配置
│   │   ├── storage.ts          # 本地存储工具
│   │   └── ...
│   ├── views/                  # 页面视图
│   │   ├── content/            # 内容管理模块
│   │   ├── system/             # 系统管理模块
│   │   ├── plugins/            # 插件模块
│   │   └── template/           # 模板页面
│   ├── App.vue                 # 根组件
│   ├── main.ts                 # 入口文件
│   └── settings.ts             # Fast-Crud 全局配置
├── .env.development            # 开发环境配置
├── .env.production             # 生产环境配置
├── index.html                  # HTML 入口
├── package.json                # 依赖配置
└── vite.config.js              # Vite 配置
```

## 快速开始

### 环境要求

- Node.js >= 16.0.0
- npm >= 7.0.0

### 安装与运行

```bash
# 安装依赖
npm install

# 开发模式启动（端口 8060）
npm run dev

# 构建生产版本
npm run build

# 构建开发版本
npm run build:dev
```

### 环境变量

开发环境（`.env.development`）：
```
VITE_API_URL = 'http://127.0.0.1:8000'   # 后端 API 地址
VITE_PORT = 8060                           # 开发服务器端口
VITE_PM_ENABLED = true                     # 是否启用按钮权限
```

生产环境（`.env.production`）：
```
VITE_API_URL = '/api'                      # 生产环境 API 代理路径
VITE_PM_ENABLED = true
```

## 核心模块

### 内容管理（`views/content/`）

管理后台的核心业务模块，包含以下子模块：

| 模块 | 路径 | 说明 |
|------|------|------|
| 知识库管理 | `content/knowledge-base/` | 知识库 CRUD、审核、文件查看、批量操作、导入导出 |
| 人设卡管理 | `content/persona-card/` | 人设卡 CRUD、审核、文件查看、批量操作、导入导出 |
| 内容审核 | `content/review/` | 统一审核面板、AI 审核、批量审核、审核报告查看 |
| 评论管理 | `content/comment/` | 评论列表、删除管理 |
| 收藏记录 | `content/star-record/` | 用户收藏记录查看 |
| 上传记录 | `content/upload-record/` | 上传行为记录 |
| 下载记录 | `content/download-record/` | 下载行为记录 |
| 数据统计 | `content/statistics/` | 概览指标、审核分布饼图、趋势折线图、热门排行榜 |

### 系统管理（`views/system/`）

基于 django-vue3-admin 框架的系统管理模块：

| 模块 | 路径 | 说明 |
|------|------|------|
| 用户管理 | `system/user/` | 用户 CRUD、封禁/解封、禁言 |
| 角色管理 | `system/role/` | 角色权限配置 |
| 部门管理 | `system/dept/` | 部门树形结构管理 |
| 菜单管理 | `system/menu/` | 动态菜单配置 |
| 数据字典 | `system/dictionary/` | 系统字典管理 |
| 系统配置 | `system/config/` | 系统参数配置 |
| 操作日志 | `system/log/` | 操作日志查看 |
| 消息中心 | `system/messageCenter/` | 站内消息管理 |
| 文件管理 | `system/fileList/` | 上传文件管理 |
| 登录页 | `system/login/` | 管理员登录 |
| 注册页 | `system/register/` | 用户注册 |
| 邮箱验证 | `system/verify-email/` | 邮箱验证码验证 |

## 架构说明

### 路由机制

项目采用后端控制路由模式（`router/backEnd.ts`）：

1. 用户登录后，前端请求后端菜单接口获取路由数据
2. 后端根据用户角色返回对应的菜单权限
3. 前端动态注册路由并渲染侧边栏菜单

静态路由（`router/route.ts`）仅包含登录、注册、邮箱验证等无需权限的页面。

### 权限控制

权限粒度达到按钮级别和列级别：

- 按钮权限：通过 `auth('module:Action')` 函数控制按钮显示/隐藏
- 列权限：通过 `columnPermission` store 控制表格列的显示
- 路由权限：后端菜单接口控制可访问的页面

### 请求封装

`utils/request.ts` 基于 Axios 封装：

- 自动附加 Token（从 Session 存储读取）
- 响应拦截：`code !== 0` 时视为错误，`401/4001` 自动跳转登录
- 超时设置：50 秒
- 参数序列化：支持嵌套对象（`qs` 的 `allowDots` 模式）

### Fast-Crud 配置

`settings.ts` 中配置了 Fast-Crud 的全局行为：

- 请求转换：将分页参数转为 `page` + `limit` 格式
- 响应转换：将后端返回的 `data/total` 映射为 Fast-Crud 所需格式
- 文件上传：通过 `/api/system/file/` 接口上传
- 表单提交：`code === 2000` 时显示成功提示

### WebSocket

`utils/websocket.ts` 实现实时消息推送：

- 连接地址：`ws://{baseURL}/ws/{token}/`
- 心跳间隔：2 秒
- 自动重连：最多 3 次，间隔 5 秒
- 连接状态同步到 `userInfo` store

### 组合式函数（Composables）

`composables/content/` 提供内容管理的可复用逻辑：

| 函数 | 说明 |
|------|------|
| `useBatchOperation` | 批量审核通过/拒绝/删除，含选中状态管理 |
| `useDataExport` | 高级导出（支持 Excel/CSV、字段选择、选中导出） |
| `useDataImport` | 数据导入（模板下载、文件上传、结果展示） |
| `searchUtils` | 搜索工具函数 |
| `permissionControlUtils` | 权限控制工具 |

## 与后端的对接

- 后端 API 基础地址由 `VITE_API_URL` 环境变量配置
- 认证方式：JWT Token，存储在 Session Storage 中
- 后端成功响应格式：`{ code: 2000, msg: "...", data: {...} }`
- 分页接口返回：`{ code: 2000, data: [...], total: N, page: N, limit: N }`
- 后端框架：Django + DRF + django-vue3-admin（dvadmin）
