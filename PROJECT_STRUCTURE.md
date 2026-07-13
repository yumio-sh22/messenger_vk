# Полная структура проекта

```text
messenger_project/
├── app/
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── chats.py
│   │   ├── messages.py
│   │   └── users.py
│   ├── static/
│   │   └── index.html
│   ├── __init__.py
│   ├── audit.py
│   ├── config.py
│   ├── database.py
│   ├── deps.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   └── ws.py
├── client/
│   ├── __init__.py
│   └── cli.py
├── db/
│   ├── init/
│   │   ├── 001_schema.sql
│   │   └── 002_seed.sql
│   └── queries.sql
├── docs/
│   ├── api.md
│   ├── auth_model.md
│   ├── contribution.md
│   ├── demo_scenarios.md
│   ├── er_diagram.md
│   ├── report.md
│   ├── roles.md
│   └── sql_queries.md
├── scripts/
│   └── smoke_test.py
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── PROJECT_STRUCTURE.md
├── docker-compose.yml
└── requirements.txt
```

## Куда вставлять код

В этом архиве уже создана вся структура. Если переносить проект вручную, создайте папки как в дереве выше и вставьте содержимое каждого файла в файл с таким же путем:

- Backend-код вставляется в `app/`.
- REST-роуты вставляются в `app/routers/`.
- HTML-клиент вставляется в `app/static/index.html`.
- CLI-клиент вставляется в `client/cli.py`.
- SQL-схема и seed-данные вставляются в `db/init/`.
- SQL-запросы для защиты вставляются в `db/queries.sql`.
- Документация для сдачи вставляется в `docs/`.

Главная точка входа сервера: `app/main.py`.

