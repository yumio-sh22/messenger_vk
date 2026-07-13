# Messenger Case 1

Готовый MVP мессенджера для кейса №1: сервер и клиент для быстрого обмена сообщениями с авторизацией, чатами и поиском по сообщениям.

## Что реализовано

- Сервер мессенджера на Python/FastAPI.
- PostgreSQL как основная база данных.
- Регистрация и авторизация пользователей через JWT.
- Безопасное хранение паролей: bcrypt-хеши, открытый пароль не сохраняется.
- Роли: `reader`, `writer`, `admin` с разными правами доступа.
- Личные и групповые чаты.
- Участники чатов и проверка доступа к чужим данным.
- Быстрая отправка и получение сообщений через REST и WebSocket.
- Поиск по сообщениям внутри доступных пользователю чатов.
- Статусы сообщений: `sent`, `delivered`, `read`.
- Реакции на сообщения.
- Вложения как метаданные файла.
- Ограничение частоты отправки сообщений.
- Аудит действий пользователя.
- Web UI-клиент: `http://localhost:8000`.
- CLI-клиент: `python -m client.cli`.
- SQL-скрипты, ER-диаграмма, модель авторизации и описание ролей.

## Быстрый запуск

1. Скопируйте настройки окружения:

```bash
cp .env.example .env
```

2. Запустите PostgreSQL и приложение:

```bash
docker compose up --build
```

3. Откройте:

```text
http://localhost:8000
```

4. Документация API:

```text
http://localhost:8000/docs
```

## Тестовые пользователи

Демо-данные создаются SQL-скриптом `db/init/002_seed.sql`.

Пароль для всех тестовых пользователей:

```text
Password123!
```

Пользователи:

- `admin@example.com` - роль `admin`.
- `writer@example.com` - роль `writer`.
- `reader@example.com` - роль `reader`.

## CLI-клиент

После запуска сервера:

```bash
python -m client.cli register alice@example.com alice Password123!
python -m client.cli login alice@example.com Password123!
python -m client.cli chats
python -m client.cli create-chat "Project chat" --member writer@example.com
python -m client.cli send 1 "Привет!"
python -m client.cli search "Привет"
python -m client.cli listen 1
```

## Основные эндпоинты

- `POST /api/auth/register` - регистрация.
- `POST /api/auth/login` - вход и получение JWT.
- `GET /api/users/me` - текущий пользователь.
- `GET /api/users` - список пользователей, только для `admin`.
- `GET /api/chats` - список доступных чатов.
- `POST /api/chats` - создание чата.
- `GET /api/chats/{chat_id}/messages` - история сообщений.
- `POST /api/chats/{chat_id}/messages` - отправка сообщения.
- `GET /api/messages/search?q=...` - поиск по сообщениям.
- `POST /api/messages/{message_id}/reactions` - реакция.
- `POST /api/messages/{message_id}/attachments` - добавить вложение.
- `WS /ws/chats/{chat_id}?token=...` - живой канал сообщений.

## Материалы для защиты

- `docs/report.md` - отчет по проекту.
- `docs/er_diagram.md` - ER-диаграмма Mermaid.
- `docs/auth_model.md` - модель авторизации.
- `docs/roles.md` - роли и права доступа.
- `docs/api.md` - описание API.
- `docs/sql_queries.md` - SQL-запросы с JOIN, GROUP BY и подзапросами.
- `docs/demo_scenarios.md` - сценарии демонстрации.
- `docs/contribution.md` - описание вклада участников.
