from sqlalchemy import text

from app.database import engine


def run_lightweight_migrations() -> None:
    """Small idempotent migrations for existing demo Docker volumes."""
    statements = [
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS reply_to_message_id INTEGER REFERENCES messages(id) ON DELETE SET NULL",
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(40)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT",
        "ALTER TABLE users ALTER COLUMN avatar_url TYPE TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(80)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS age INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS status_text VARCHAR(120)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_online BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE chat_members ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE",
        "UPDATE users SET display_name = left(display_name, 40) WHERE display_name IS NOT NULL AND length(display_name) > 40",
        "UPDATE users SET city = left(city, 80) WHERE city IS NOT NULL AND length(city) > 80",
        "UPDATE users SET status_text = left(status_text, 120) WHERE status_text IS NOT NULL AND length(status_text) > 120",
        "ALTER TABLE users ALTER COLUMN display_name TYPE VARCHAR(40)",
        "ALTER TABLE users ALTER COLUMN city TYPE VARCHAR(80)",
        "ALTER TABLE users ALTER COLUMN status_text TYPE VARCHAR(120)",
        "CREATE INDEX IF NOT EXISTS ix_messages_reply_to_message_id ON messages(reply_to_message_id)",
        """
        CREATE TABLE IF NOT EXISTS favorite_messages (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_favorite_message UNIQUE (user_id, message_id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_favorite_messages_user_id ON favorite_messages(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_favorite_messages_message_id ON favorite_messages(message_id)",
        """
        CREATE TABLE IF NOT EXISTS message_read_receipts (
            id SERIAL PRIMARY KEY,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            read_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_message_read_receipt UNIQUE (message_id, user_id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_message_read_receipts_message_id ON message_read_receipts(message_id)",
        "CREATE INDEX IF NOT EXISTS ix_message_read_receipts_user_id ON message_read_receipts(user_id)",
        "CREATE TABLE IF NOT EXISTS app_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())",
        """
        UPDATE chat_members AS member
        SET role = 'member'
        FROM chats AS chat
        WHERE member.chat_id = chat.id
          AND chat.type = 'group'
          AND member.role = 'owner'
          AND member.user_id <> chat.created_by_id
          AND NOT EXISTS (
              SELECT 1 FROM app_migrations WHERE name = 'normalize_initial_group_owners'
          )
        """,
        """
        INSERT INTO app_migrations (name)
        VALUES ('normalize_initial_group_owners')
        ON CONFLICT (name) DO NOTHING
        """,
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
