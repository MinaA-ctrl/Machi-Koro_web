"""add players.identity (auth principal for seat ownership)

Stage 2 S2.3. The guest-identity stand-in (and, from S2.4, the JWT subject) that
owns a seat — used for server-authoritative seat-ownership checks (rename). NULL
for pre-existing rows. Incremental migration on top of the S2.2 baseline.

Revision ID: 0002_player_identity
Revises: 0001_baseline
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_player_identity"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("players", sa.Column("identity", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("players", "identity")
