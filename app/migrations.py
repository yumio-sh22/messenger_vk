from sqlalchemy import text

from app.database import engine


def run_lightweight_migrations() -> None:
    """Small idempotent migrations for existing demo Docker volumes."""
    statements = [
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS reply_to_message_id INTEGER REFERENCES messages(id) ON DELETE SET NULL",
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE",
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
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
