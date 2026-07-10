from sqlalchemy import text

from app.database import engine


def run_lightweight_migrations() -> None:
    """Small idempotent migrations for existing demo Docker volumes."""
    statements = [
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS reply_to_message_id INTEGER REFERENCES messages(id) ON DELETE SET NULL",
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(120)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT",
        "ALTER TABLE users ALTER COLUMN avatar_url TYPE TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(120)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS age INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS status_text VARCHAR(160)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_online BOOLEAN NOT NULL DEFAULT TRUE",
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
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
