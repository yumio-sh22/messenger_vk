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

