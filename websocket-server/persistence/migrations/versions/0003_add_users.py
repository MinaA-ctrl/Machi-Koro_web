"""add users (accounts: guest | registered)

Stage 2 S2.4 — JWT auth. The JWT subject is guest:<id> / user:<id> keyed on this
table's id. Registered accounts carry a unique email + argon2 password_hash;
guests are persisted with kind='guest'. Incremental migration on the S2.2/S2.3
schema. (entitlements / wallet arrive in S2.5.)

Revision ID: 0003_add_users
Revises: 0002_player_identity
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_add_users"
down_revision = "0002_player_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("avatar", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('guest', 'registered')", name="ck_user_kind"),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )


def downgrade() -> None:
    op.drop_table("users")
