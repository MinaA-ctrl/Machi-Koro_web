"""add scores.points

Persist each registered player's final score (2× opened-landmark cost + leftover
coins + finishing-place bonus) so the per-game history can show points and the
account can total points across all games. Non-null with a 0 default — older score
rows (which predate stored points) read back as 0.

Revision ID: 0007_score_points
Revises: 0006_score_place
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_score_points"
down_revision = "0006_score_place"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scores",
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("scores", "points")
