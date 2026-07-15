# API

## Auth

`POST /api/auth/register`

```json
{
  "email": "user@example.com",
  "username": "user",
  "password": "Password123!"
}
```

`POST /api/auth/login`

```json
{
  "email": "user@example.com",
  "password": "Password123!"
}
```

## Users

- `GET /api/users/me` - текущий пользователь.
- `GET /api/users` - список пользователей, только `admin`.

## Chats

`GET /api/chats` - список чатов пользователя.

`POST /api/chats`

```json
{
  "title": "Project chat",
  "type": "group",
  "members": [
    { "user_id": 2, "role": "member" }
  ]
}
```

## Messages

`GET /api/chats/{chat_id}/messages` - история сообщений.

Параметры:

- `limit` - размер страницы, по умолчанию 50.
- `before_id` - загрузить сообщения старше указанного сообщения, используется для пагинации вверх.
- `anchor_id` - загрузить страницу истории вокруг исходного сообщения, используется при переходе из пересланного сообщения.

`POST /api/chats/{chat_id}/messages`

```json
{
  "body": "Привет!"
}
```

`GET /api/messages/search?q=привет` - поиск.

## Reactions

`POST /api/messages/{message_id}/reactions`

```json
{
  "emoji": "like"
}
```

## Attachments

`POST /api/messages/{message_id}/attachments`

```json
{
  "file_name": "report.pdf",
  "file_url": "https://example.com/report.pdf",
  "mime_type": "application/pdf"
}
```

## WebSocket

```text
ws://localhost:8000/ws/chats/{chat_id}?token=<jwt>
```

Событие нового сообщения:

```json
{
  "event": "message.created",
  "message": {
    "id": 10,
    "chat_id": 1,
    "sender_id": 2,
    "body": "Привет!",
    "status": "sent",
    "created_at": "2026-07-09T10:00:00Z",
    "edited_at": null
  }
}
```
