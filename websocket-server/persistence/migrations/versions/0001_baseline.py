"""baseline: game-data tables (tables, players, game_states, scores)

Stage 2 S2.2. Replaces the WordPress dbDelta/mk_migrate bootstrap with
migrations-as-code for the new Postgres backend. Users/entitlements/wallet are
deliberately NOT here — they land as their own migrations in S2.4/S2.5.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("join_code", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("game_version", sa.String(length=16), nullable=False, server_default="harbour"),
        sa.Column("sharp", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("variable_supply", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("creator_id", sa.String(length=64), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="waiting"),
        sa.Column("max_players", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('waiting', 'playing', 'finished')", name="ck_table_status"),
    )
    op.create_index("ix_tables_join_code", "tables", ["join_code"], unique=True)

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("seat", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("is_host", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("table_id", "seat", name="uq_player_table_seat"),
    )
    op.create_index("ix_players_table_id", "players", ["table_id"])

    op.create_table(
        "game_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("game_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("table_id", name="uq_game_state_table"),
    )

    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("landmarks_built", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coins_at_end", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("won", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("played_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("table_id", "game_seq", "user_id", name="uq_score_table_seq_user"),
    )
    op.create_index("ix_scores_table_id", "scores", ["table_id"])


def downgrade() -> None:
    op.drop_table("scores")
    op.drop_table("game_states")
    op.drop_table("players")
    op.drop_table("tables")
