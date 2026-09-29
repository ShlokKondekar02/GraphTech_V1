"""Sprint 2 -- Add complexity metrics, rejection reason, and source columns

Revision ID: 0004_sprint2_diagram_columns
Revises: 0003_vector_index
Create Date: 2026-09-26 18:00:00.000000

New columns added to diagram_requests:
  rejection_reason  -- TEXT, nullable: human-readable rejection reason
  complexity_score  -- FLOAT, nullable: independently computed complexity score
  complexity_metrics -- JSONB, nullable: full complexity metrics dict
  source            -- VARCHAR(20), nullable: "fresh" | "cache"

New index:
  ix_diagram_requests_status -- for efficient querying by pipeline status
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_sprint2_diagram_columns"
down_revision: Union[str, None] = "0003_vector_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add rejection_reason column
    op.add_column(
        "diagram_requests",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )

    # Add independently-computed complexity score (float, not a Groq value)
    op.add_column(
        "diagram_requests",
        sa.Column("complexity_score", sa.Float(), nullable=True),
    )

    # Add full complexity metrics dict (JSONB)
    op.add_column(
        "diagram_requests",
        sa.Column(
            "complexity_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Add source column: "fresh" | "cache"
    op.add_column(
        "diagram_requests",
        sa.Column("source", sa.String(length=20), nullable=True),
    )

    # Add index on status for efficient querying
    op.create_index(
        "ix_diagram_requests_status",
        "diagram_requests",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_diagram_requests_status", table_name="diagram_requests")
    op.drop_column("diagram_requests", "source")
    op.drop_column("diagram_requests", "complexity_metrics")
    op.drop_column("diagram_requests", "complexity_score")
    op.drop_column("diagram_requests", "rejection_reason")
