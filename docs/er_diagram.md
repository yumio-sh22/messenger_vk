# ER-диаграмма

```mermaid
erDiagram
    USERS ||--o{ CHAT_MEMBERS : participates
    CHATS ||--o{ CHAT_MEMBERS : contains
    USERS ||--o{ CHATS : creates
    CHATS ||--o{ MESSAGES : has
    USERS ||--o{ MESSAGES : sends
    MESSAGES ||--o{ REACTIONS : has
    USERS ||--o{ REACTIONS : adds
    MESSAGES ||--o{ ATTACHMENTS : has
    USERS ||--o{ AUDIT_LOGS : produces

    USERS {
        int id PK
        varchar email UK
        varchar username UK
        varchar password_hash
        enum role
        bool is_active
        timestamptz created_at
    }

    CHATS {
        int id PK
        varchar title
        enum type
        int created_by_id FK
        timestamptz created_at
    }

    CHAT_MEMBERS {
        int id PK
        int chat_id FK
        int user_id FK
        enum role
        timestamptz joined_at
    }

    MESSAGES {
        int id PK
        int chat_id FK
        int sender_id FK
        text body
        enum status
        timestamptz created_at
        timestamptz edited_at
    }

    REACTIONS {
        int id PK
        int message_id FK
        int user_id FK
        varchar emoji
        timestamptz created_at
    }

    ATTACHMENTS {
        int id PK
        int message_id FK
        varchar file_name
        varchar file_url
        varchar mime_type
        timestamptz created_at
    }

    AUDIT_LOGS {
        int id PK
        int user_id FK
        varchar action
        varchar entity_type
        int entity_id
        text details
        timestamptz created_at
    }
```

## Связи

- `users` 1:N `messages` - один пользователь отправляет много сообщений.
- `chats` 1:N `messages` - один чат содержит много сообщений.
- `users` N:N `chats` через `chat_members`.
- `messages` 1:N `reactions`.
- `messages` 1:N `attachments`.
- `users` 1:N `audit_logs`.

