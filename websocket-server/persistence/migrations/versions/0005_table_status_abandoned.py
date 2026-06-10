"""widen tables.status CHECK to allow 'abandoned'

Table-lifecycle cleanup: the reaper marks idle playing games 'abandoned' (a
terminal status) so they stop accumulating. Just widens the existing CHECK — no
new column. Incremental on the S2.5 schema.

Revision ID: 0005_status_abandoned
Revises: 0004_entitlements_wallet
Create Date: 2026-06-10
"""
from alembic import op

revision = "0005_status_abandoned"
down_revision = "0004_entitlements_wallet"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_table_status", "tables", type_="check")
    op.create_check_constraint(
        "ck_table_status", "tables",
        "status IN ('waiting', 'playing', 'finished', 'abandoned')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_table_status", "tables", type_="check")
    op.create_check_constraint(
        "ck_table_status", "tables",
        "status IN ('waiting', 'playing', 'finished')",
    )
