"""initial schema

Revision ID: 3e2bdbc88501
Revises:
Create Date: 2026-11-20 01:07:10.803510

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3e2bdbc88501"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CAMPAIGN_INDEX = "ix_stream_drafts_campaign_id"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "stream_drafts",
        sa.Column(
            "stream_id", sa.Integer(), autoincrement=False, nullable=False
        ),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("stream_id"),
    )
    op.create_index(
        op.f(CAMPAIGN_INDEX), "stream_drafts", ["campaign_id"], unique=False
    )
    op.create_table(
        "draft_offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("removed", sa.Boolean(), nullable=False),
        sa.Column("published_share", sa.Integer(), nullable=True),
        sa.Column("published_active", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["stream_id"], ["stream_drafts.stream_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_id", "offer_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("draft_offers")
    op.drop_index(op.f(CAMPAIGN_INDEX), table_name="stream_drafts")
    op.drop_table("stream_drafts")
