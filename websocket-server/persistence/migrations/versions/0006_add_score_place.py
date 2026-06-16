"""add scores.place + scores.total_players

Game-history support: store each registered player's finishing place (1 = winner)
and the table size at finish, computed from the full final standings (guests
included) so the place is accurate even in guest-heavy games. Nullable — older
score rows simply have no place.

Revision ID: 0006_score_place
Revises: 0005_status_abandoned
Create Date: 2026-06-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0006_score_place"
down_revision = "0005_status_abandoned"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scores", sa.Column("place", sa.Integer(), nullable=True))
    op.add_column("scores", sa.Column("total_players", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("scores", "total_players")
    op.drop_column("scores", "place")
