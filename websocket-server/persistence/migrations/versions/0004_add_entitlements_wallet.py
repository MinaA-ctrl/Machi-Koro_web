"""add entitlements + wallet (+ ledger) — the monetization seam (free by default)

Stage 2 S2.5. Per-user host-rights / subscription (entitlements) and a Koro Coins
wallet + ledger. All defaults are permissive/free — nothing is gated today; the
shape lets a later default-flip enforce the host-pays model. Incremental on the
S2.4 users table.

Revision ID: 0004_entitlements_wallet
Revises: 0003_add_users
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_entitlements_wallet"
down_revision = "0003_add_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entitlements",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("host_harbour", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("host_sharp", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("free_host_harbour_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("free_host_sharp_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("harbour_pass", sa.String(length=8), nullable=False, server_default="none"),
        sa.Column("harbour_pass_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ad_free", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("harbour_pass IN ('none', 'active')", name="ck_harbour_pass"),
    )

    op.create_table(
        "wallets",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("koro_coins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "wallet_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_wallet_ledger_user_id", "wallet_ledger", ["user_id"])


def downgrade() -> None:
    op.drop_table("wallet_ledger")
    op.drop_table("wallets")
    op.drop_table("entitlements")
