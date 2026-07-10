-- 1. Список чатов пользователя: JOIN users -> chat_members -> chats
SELECT c.id, c.title, c.type, cm.role, c.created_at
FROM chats c
JOIN chat_members cm ON cm.chat_id = c.id
JOIN users u ON u.id = cm.user_id
WHERE u.email = 'writer@example.com'
ORDER BY c.created_at DESC;

-- 2. История сообщений с именами отправителей
SELECT m.id, c.title AS chat_title, u.username AS sender, m.body, m.status, m.created_at
FROM messages m
JOIN chats c ON c.id = m.chat_id
JOIN users u ON u.id = m.sender_id
WHERE c.id = 1
ORDER BY m.created_at;

-- 3. Количество сообщений по чатам: GROUP BY
SELECT c.id, c.title, count(m.id) AS message_count
FROM chats c
LEFT JOIN messages m ON m.chat_id = c.id
GROUP BY c.id, c.title
ORDER BY message_count DESC;

-- 4. Поиск по сообщениям, доступным пользователю
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

-- 5. Пользователи, которые еще не писали сообщений: подзапрос
SELECT u.id, u.email, u.username
FROM users u
WHERE u.id NOT IN (SELECT DISTINCT sender_id FROM messages);

