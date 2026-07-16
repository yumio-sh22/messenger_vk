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

## Обновление: файловые сообщения

Мессенджер поддерживает отправку файлов вместе с сообщением. Сценарий работы состоит из двух шагов:

1. Клиент загружает файл через `POST /api/uploads`.
2. Клиент отправляет сообщение через `POST /api/chats/{chat_id}/messages` и передает полученные метаданные файла в поле `attachments`.

`POST /api/uploads` принимает `multipart/form-data` с полем `file` и возвращает:

```json
{
  "file_name": "report.pdf",
  "file_url": "/uploads/8a1b2c3d4e.pdf",
  "mime_type": "application/pdf"
}
```

Пример сообщения с вложением:

```json
{
  "body": "Отчет по проекту",
  "attachments": [
    {
      "file_name": "report.docx",
      "file_url": "/uploads/4f2b1c_report.docx",
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
  ]
}
```

Ограничения файловых сообщений:

- к одному сообщению можно прикрепить не больше 3 файлов;
- в строке отправки нельзя прикрепить один и тот же файл больше одного раза;
- если к файлам добавлена текстовая подпись, она не должна превышать 200 слов;
- файловое сообщение можно переслать в «Избранное», удалить, открыть в новой вкладке и использовать как сообщение, на которое отвечают;
- вложения копируются в «Избранное» вместе с исходным сообщением, при этом сохраняется ссылка на исходный чат и исходное сообщение.
