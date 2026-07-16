# SQL-запросы

Полный файл запросов находится в `db/queries.sql`.

## JOIN

```sql
SELECT c.id, c.title, c.type, cm.role, c.created_at
FROM chats c
JOIN chat_members cm ON cm.chat_id = c.id
JOIN users u ON u.id = cm.user_id
WHERE u.email = 'writer@example.com'
ORDER BY c.created_at DESC;
```

## GROUP BY

```sql
SELECT c.id, c.title, count(m.id) AS message_count
FROM chats c
LEFT JOIN messages m ON m.chat_id = c.id
GROUP BY c.id, c.title
ORDER BY message_count DESC;
```

## Подзапрос

```sql
SELECT m.id, m.body, m.created_at
FROM messages m
WHERE m.chat_id IN (
    SELECT cm.chat_id
    FROM chat_members cm
    JOIN users u ON u.id = cm.user_id
    WHERE u.email = 'writer@example.com'
)
AND m.body ILIKE '%поиск%'
ORDER BY m.created_at DESC;
```


## Запросы для вложений

Получить сообщения вместе с количеством вложений:

```sql
SELECT m.id,
       m.chat_id,
       m.sender_id,
       m.body,
       count(a.id) AS attachments_count,
       m.created_at
FROM messages m
LEFT JOIN attachments a ON a.message_id = m.id
GROUP BY m.id, m.chat_id, m.sender_id, m.body, m.created_at
ORDER BY m.created_at DESC;
```

Получить список файлов конкретного сообщения:

```sql
SELECT a.id, a.file_name, a.file_url, a.mime_type, a.created_at
FROM attachments a
WHERE a.message_id = 10
ORDER BY a.created_at ASC;
```

Найти файловые сообщения пользователя:

```sql
SELECT m.id, c.title AS chat_title, a.file_name, a.file_url, m.created_at
FROM messages m
JOIN chats c ON c.id = m.chat_id
JOIN attachments a ON a.message_id = m.id
WHERE m.sender_id = 2
ORDER BY m.created_at DESC;
```
