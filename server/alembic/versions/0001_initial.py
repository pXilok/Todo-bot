"""Initial schema: users, settings, states, tasks, messages, processed_events, outbox.

Revision ID: 0001
Revises:
Create Date: 2026-10-17 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIG_INT_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
UTC_DATETIME = sa.DateTime(timezone=True)
ENUM_LENGTH = 32


def _enum(name: str, *values: str) -> sa.Enum:
    """Строковая (не native) Enum-колонка, как str_enum() в db/base.py."""
    return sa.Enum(*values, name=name, native_enum=False, length=ENUM_LENGTH)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("last_seen_at", UTC_DATETIME, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_last_seen_at"), "users", ["last_seen_at"])

    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("tz_offset_minutes", sa.Integer(), nullable=False),
        sa.Column("reminders_enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_user_settings_user_id_users"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_settings")),
    )

    op.create_table(
        "user_states",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "state",
            _enum(
                "botstate",
                "MAIN_MENU", "ADD_TASK", "LIST_TASKS", "DELETE_TASK",
                "SET_REMINDER", "SETTINGS", "SETTINGS_TIMEZONE",
            ),
            nullable=False,
        ),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_user_states_user_id_users"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_states")),
    )

    op.create_table(
        "tasks",
        sa.Column("id", BIG_INT_PK, autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False),
        sa.Column("remind_at", UTC_DATETIME, nullable=True),
        sa.Column("reminded_at", UTC_DATETIME, nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("done_at", UTC_DATETIME, nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_tasks_user_id_users"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
    )
    op.create_index(op.f("ix_tasks_user_id"), "tasks", ["user_id"])
    op.create_index("ix_tasks_due_reminders", "tasks", ["remind_at", "reminded_at"])

    op.create_table(
        "messages",
        sa.Column("id", BIG_INT_PK, autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("direction", _enum("messagedirection", "in", "out"), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("callback_data", sa.String(length=64), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_messages_user_id_users"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_index(op.f("ix_messages_user_id"), "messages", ["user_id"])
    op.create_index(op.f("ix_messages_created_at"), "messages", ["created_at"])

    op.create_table(
        "processed_events",
        sa.Column("id", BIG_INT_PK, autoincrement=True, nullable=False),
        sa.Column("platform", _enum("platform", "telegram"), nullable=False),
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("processed_at", UTC_DATETIME, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processed_events")),
        sa.UniqueConstraint(
            "platform", "update_id", name=op.f("uq_processed_events_platform_update_id")
        ),
    )

    op.create_table(
        "outbox",
        sa.Column("id", BIG_INT_PK, autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("task_id", sa.BigInteger(), nullable=True),
        sa.Column("kind", _enum("outboxkind", "reminder", "broadcast"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "status",
            _enum("outboxstatus", "pending", "claimed", "sent", "failed"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("claimed_at", UTC_DATETIME, nullable=True),
        sa.Column("sent_at", UTC_DATETIME, nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_outbox_user_id_users"), ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"],
            name=op.f("fk_outbox_task_id_tasks"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox")),
    )
    op.create_index("ix_outbox_status_created", "outbox", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_status_created", table_name="outbox")
    op.drop_table("outbox")
    op.drop_table("processed_events")
    op.drop_index(op.f("ix_messages_created_at"), table_name="messages")
    op.drop_index(op.f("ix_messages_user_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_tasks_due_reminders", table_name="tasks")
    op.drop_index(op.f("ix_tasks_user_id"), table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("user_states")
    op.drop_table("user_settings")
    op.drop_index(op.f("ix_users_last_seen_at"), table_name="users")
    op.drop_table("users")