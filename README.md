<div align="center">

# Messenger

### Современный мессенджер на Python, FastAPI и PostgreSQL

Messenger — веб-приложение для обмена сообщениями с авторизацией, личными и групповыми чатами, избранным, ролями участников, профилями, WebSocket-сообщениями, файловыми вложениями и адаптивным интерфейсом со светлой и темной темами.

<br>

![Python](https://img.shields.io/badge/Python-3.x-7B3FF2?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-7B3FF2?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-7B3FF2?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-7B3FF2?style=for-the-badge&logo=docker&logoColor=white)

</div>

---

## О проекте

Проект включает:

- backend на **FastAPI**;
- базу данных **PostgreSQL**;
- авторизацию через **JWT**;
- обмен сообщениями через **REST API** и **WebSocket**;
- отправку файловых вложений в сообщениях;
- веб-интерфейс без отдельного frontend-фреймворка;
- Docker-запуск;
- роли пользователей и участников групп;
- личные чаты, группы и избранное.

---

## Навигация

- [Функциональность](#-функциональность)
- [Роли и права](#-роли-и-права)
- [Стек технологий](#-стек-технологий)
- [Структура проекта](#-структура-проекта)
- [Быстрый запуск](#-быстрый-запуск)
- [Makefile-команды](#-makefile-команды)
- [Тестовые аккаунты](#-тестовые-аккаунты)
- [API](#-api)
- [Работа с базой данных](#-работа-с-базой-данных)
- [Обзор работы приложения](#-обзор-работы-приложения)
---

## Функциональность

### Авторизация

- регистрация пользователя;
- вход по email и паролю;
- JWT-токены;
- безопасное хранение паролей;
- при регистрации пользователь создается как обычный пользователь;
- смена глобальной роли пользователя не доступна через форму регистрации.

### Чаты

- список доступных чатов;
- личные чаты один на один;
- групповые чаты;
- личный чат **Избранное**;
- поиск по чатам;
- поиск внутри текущего чата;
- отображение последнего сообщения в списке чатов;
- корректное отображение личного чата для обоих участников.

### Сообщения

- отправка сообщений;
- получение сообщений в реальном времени через WebSocket;
- ответы на конкретные сообщения;
- редактирование своих сообщений;
- удаление сообщений без служебной заглушки;
- добавление сообщений в избранное;
- удаление сообщений из избранного;
- переход из избранного к исходному сообщению;
- подсветка исходного сообщения при переходе;
- отправка файлов вместе с сообщением;
- отправка до 3 файлов в одном сообщении;
- защита от повторного выбора одного и того же файла;
- предварительный просмотр выбранных файлов перед отправкой;
- удаление выбранных файлов из строки отправки по одному;
- отправка файлов любого формата;
- открытие файлов из сообщения в новой вкладке браузера;
- отправка файла вместе с текстовой подписью;
- ограничение подписи к файловому сообщению до 200 слов;
- добавление файловых сообщений в избранное;
- переход из избранного к исходному файловому сообщению;
- статусы сообщений:
  - отправлено;
  - доставлено;
  - прочитано.

Статусы сообщений отображаются только отправителю.

### Профиль

- аватар пользователя;
- никнейм;
- возраст;
- город;
- короткий статус;
- индикатор online/offline;
- ограничения на длину полей;
- ограничение возраста до 200 лет;
- просмотр профиля собеседника в личном чате.

### Интерфейс

- светлая и темная темы;
- переключение темы одной кнопкой;
- современный фиолетовый дизайн;
- кастомные модальные окна;
- кастомные уведомления;
- адаптированные панели действий;
- аккуратная работа с меню, профилем и списком чатов.

---

## Роли и права

В проекте есть два уровня ролей:

1. **Глобальная роль пользователя в системе**
2. **Роль участника внутри конкретной группы**

### Глобальные роли

| Роль | Описание |
|---|---|
| `admin` | Администратор приложения |
| `writer` | Обычный пользователь |
| `reader` | Пользователь с ограниченными правами |

При обычной регистрации пользователь создается как `writer`.

### Роли внутри группы

| Роль в группе | Возможности |
|---|---|
| `admin` | Управляет участниками группы |
| `writer` | Может читать и писать сообщения |
| `reader` | Может читать сообщения, но не писать в группе |

Создатель группы автоматически становится админом этой группы.

Админ группы может:

- добавлять участников;
- удалять участников;
- менять роли участников;
- назначать другого участника админом группы.

---

## Стек технологий

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT
- WebSocket

### Database

- PostgreSQL 16
- SQL-инициализация базы
- прикладные миграции

### Frontend

- HTML
- CSS
- JavaScript

### Infrastructure

- Docker
- Docker Compose
- Makefile

---

## Структура проекта

```text
messenger_project/
├── app/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── chats.py
│   │   ├── messages.py
│   │   └── users.py
│   ├── static/
│   │   └── index.html
│   ├── uploads/
│   │   └── .gitkeep
│   ├── audit.py
│   ├── config.py
│   ├── database.py
│   ├── deps.py
│   ├── main.py
│   ├── migrations.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   └── ws.py
├── client/
├── db/
│   ├── init/
│   │   ├── 001_schema.sql
│   │   └── 002_seed.sql
│   └── queries.sql
├── scripts/
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
└── README.md
```

---

## Быстрый запуск

Создайте `.env` из примера:

```powershell
Copy-Item .env.example .env
```

Запустите проект:

```powershell
docker compose up -d --build
```

После запуска приложение будет доступно по адресу:

```text
http://localhost:8000
```

Swagger-документация API:

```text
http://localhost:8000/docs
```

---

## Makefile

В проекте есть `Makefile`, поэтому можно запускать приложение короткими командами.

```powershell
make help
```

| Команда | Описание |
|---|---|
| `make up` | Запустить контейнеры в фоне |
| `make build` | Пересобрать и запустить контейнеры |
| `make down` | Остановить контейнеры |
| `make restart` | Перезапустить контейнеры |
| `make logs` | Показать все логи |
| `make logs-api` | Показать логи API |
| `make logs-db` | Показать логи базы данных |
| `make ps` | Показать контейнеры |
| `make shell` | Открыть shell внутри API-контейнера |
| `make db` | Открыть PostgreSQL внутри контейнера |
| `make migrate` | Запустить миграции приложения |
| `make clean` | Остановить контейнеры и удалить volume базы |

---

## Переменные окружения

Файл `.env.example`:

```env
APP_NAME=Messenger Case 1
APP_ENV=local
SECRET_KEY=change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=postgresql+psycopg://messenger:messenger@db:5432/messenger
RATE_LIMIT_MESSAGES_PER_MINUTE=30
```

Перед использованием проекта в реальной среде нужно заменить `SECRET_KEY`.

---

## Тестовые аккаунты

После первого запуска база заполняется тестовыми данными из:

```text
db/init/002_seed.sql
```

Доступные аккаунты:

| Email | Роль |
|---|---|
| `admin@example.com` | admin |
| `writer@example.com` | writer |
| `reader@example.com` | reader |

Пароль для тестовых аккаунтов:

```text
Password123!
```

---

## Основные страницы

| Страница | Описание |
|---|---|
| `/` | Главная точка входа |
| `/login` | Вход |
| `/register` | Регистрация |
| `/app` | Мессенджер |
| `/profile` | Профиль |
| `/docs` | Swagger API |

---

## API

### Auth

| Метод | Endpoint | Описание |
|---|---|---|
| `POST` | `/api/auth/register` | Регистрация |
| `POST` | `/api/auth/login` | Вход |

### Users

| Метод | Endpoint | Описание |
|---|---|---|
| `GET` | `/api/users/me` | Получить текущего пользователя |
| `GET` | `/api/users` | Получить список пользователей |
| `PATCH` | `/api/users/me/profile` | Обновить профиль |
| `POST` | `/api/users/me/avatar` | Загрузить аватар |

### Chats

| Метод | Endpoint | Описание |
|---|---|---|
| `GET` | `/api/chats` | Получить список чатов |
| `POST` | `/api/chats/direct` | Создать личный чат |
| `POST` | `/api/chats/group` | Создать группу |
| `DELETE` | `/api/chats/{chat_id}` | Удалить или скрыть чат |
| `POST` | `/api/chats/{chat_id}/members` | Добавить участника |
| `DELETE` | `/api/chats/{chat_id}/members/{user_id}` | Удалить участника |
| `PATCH` | `/api/chats/{chat_id}/members/{user_id}` | Изменить роль участника |

### Messages

| Метод | Endpoint | Описание |
|---|---|---|
| `GET` | `/api/chats/{chat_id}/messages` | Получить сообщения |
| `POST` | `/api/chats/{chat_id}/messages` | Отправить сообщение |
| `PATCH` | `/api/messages/{message_id}` | Редактировать сообщение |
| `DELETE` | `/api/messages/{message_id}` | Удалить сообщение |
| `POST` | `/api/messages/{message_id}/favorite` | Добавить в избранное |
| `DELETE` | `/api/messages/{message_id}/favorite` | Убрать из избранного |
| `POST` | `/api/uploads` | Загрузить файл для сообщения |
| `POST` | `/api/messages/{message_id}/attachments` | Добавить вложение к сообщению |

Файлы сначала загружаются через `/api/uploads`, после чего полученные метаданные передаются при отправке сообщения. В одном сообщении поддерживается до 3 файлов.

### WebSocket

```text
/ws/chats/{chat_id}?token=...
```

Используется для получения новых сообщений в реальном времени.

---

## Работа с базой данных

Открыть PostgreSQL внутри контейнера:

```powershell
make db
```

Или напрямую:

```powershell
docker exec -it messenger_db psql -U messenger -d messenger
```

Посмотреть пользователей:

```sql
select id, email, username, role from users;
```

Посмотреть файловые вложения сообщений:

```sql
select id, message_id, file_name, file_url, mime_type, created_at
from attachments
order by created_at desc;
```

Полностью пересоздать базу:

```powershell
make clean
make build
```

> Важно: `make clean` удаляет Docker volume с данными PostgreSQL.

---

## Проверка проекта

Проверить Python-файлы:

```powershell
docker exec -it messenger_api python -m compileall app
```

Проверить контейнеры:

```powershell
docker ps
```

Посмотреть логи API:

```powershell
make logs-api
```

Посмотреть логи базы:

```powershell
make logs-db
```

---

## Обзор работы приложения

<img width="2876" height="1534" alt="Снимок экрана 2026-07-15 143843" src="https://github.com/user-attachments/assets/9b22bbd1-007d-4cba-828c-8d75dc689961" />
<img width="2876" height="1530" alt="Снимок экрана 2026-07-15 143642" src="https://github.com/user-attachments/assets/f7e19239-4164-429a-81e5-350c295cdf0d" />
<img width="1348" height="1502" alt="Снимок экрана 2026-07-15 143933" src="https://github.com/user-attachments/assets/a9ca6c7d-7002-4ca4-8720-beced0b5ff3b" />
<img width="2872" height="1542" alt="Снимок экрана 2026-07-15 144029" src="https://github.com/user-attachments/assets/8cfc4cc7-f206-438b-b629-c445d0c94690" />
<img width="1826" height="1534" alt="Снимок экрана 2026-07-15 144129" src="https://github.com/user-attachments/assets/02717499-f911-4912-876a-05c8363c7d57" />

*С остальным функционалом приложения вы можете ознакомиться непосредственно внутри мессенджера*

С ❤️,  
yumio_sh22
