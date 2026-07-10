INSERT INTO users (id, email, username, password_hash, role)
VALUES
    (1, 'admin@example.com', 'admin', crypt('Password123!', gen_salt('bf')), 'admin'),
    (2, 'writer@example.com', 'writer', crypt('Password123!', gen_salt('bf')), 'writer'),
    (3, 'reader@example.com', 'reader', crypt('Password123!', gen_salt('bf')), 'reader')
ON CONFLICT (id) DO NOTHING;

SELECT setval('users_id_seq', GREATEST((SELECT max(id) FROM users), 1), true);

INSERT INTO chats (id, title, type, created_by_id)
VALUES (1, 'Demo chat', 'group', 1)
ON CONFLICT (id) DO NOTHING;

SELECT setval('chats_id_seq', GREATEST((SELECT max(id) FROM chats), 1), true);

INSERT INTO chat_members (chat_id, user_id, role)
VALUES
    (1, 1, 'owner'),
    (1, 2, 'member'),
    (1, 3, 'readonly')
ON CONFLICT (chat_id, user_id) DO NOTHING;

INSERT INTO messages (chat_id, sender_id, body, status)
VALUES
    (1, 1, 'Добро пожаловать в демо-чат мессенджера.', 'read'),
    (1, 2, 'Это сообщение можно найти через поиск.', 'delivered')
ON CONFLICT DO NOTHING;

