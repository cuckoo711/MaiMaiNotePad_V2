# WebSocket 与消息推送

## 概述

系统使用 Django Channels 实现 WebSocket 实时通信，主要用于消息中心的实时推送。

## 连接方式

```
ws://<host>/ws/<jwt_token>/
```

客户端使用 JWT token 作为 URL 参数进行身份验证。连接成功后，服务端会：
- 将用户加入以 `user_<user_id>` 命名的 Channel Group
- 推送连接成功消息或未读消息提醒

## 消息格式

```json
{
  "sender": "system",
  "contentType": "SYSTEM",
  "content": "您已上线",
  "unread": 0
}
```

| 字段 | 说明 |
|------|------|
| sender | 发送者标识 |
| contentType | 消息类型（SYSTEM 等） |
| content | 消息内容 |
| unread | 未读消息数量 |

## 消息中心

消息中心（`MessageCenter`）支持按目标类型推送：

- 用户消息：指定目标用户
- 部门消息：指定目标部门
- 角色消息：指定目标角色
- 系统通知：全体用户

消息通过 `MessageCenterTargetUser` 关联表追踪每个用户的已读状态。

## 审核通知推送

AI 审核完成后，`ReviewNotificationService` 会：
1. 创建站内消息（MessageCenter 记录）
2. 通过 WebSocket 实时推送给上传者

## 技术栈

- Django Channels：WebSocket 协议支持
- channels-redis：Channel Layer 后端
- ASGI：异步服务器网关接口

## 配置

ASGI 入口：`application/asgi.py`

WebSocket 路由：`application/ws_routing.py`

Channel Layer 使用 Redis 作为后端，配置在 `application/settings.py` 中。

## 相关文件

- WebSocket 消费者：`application/websocketConfig.py`
- WebSocket 路由：`application/ws_routing.py`
- 消息中心视图：`mainotebook/system/views/message_center.py`
- 审核通知服务：`mainotebook/content/services/review_notification.py`
