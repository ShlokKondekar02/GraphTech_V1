"""Sprint 3 -- Add dsl_code and svg_content columns to diagram_requests

Revision ID: 0005_sprint3_rendering
Revises: 0004_sprint2_diagram_columns
Create Date: 2026-10-02 12:00:00.000000

New columns added to diagram_requests:
  dsl_code    -- TEXT, nullable: compiled DSL string (Mermaid, PlantUML, or DOT)
  svg_content -- TEXT, nullable: rendered SVG markup from Kroki
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_sprint3_rendering"
down_revision: Union[str, None] = "0004_sprint2_diagram_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "diagram_requests",
        sa.Column("dsl_code", sa.Text(), nullable=True),
    )
    op.add_column(
        "diagram_requests",
        sa.Column("svg_content", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("diagram_requests", "svg_content")
    op.drop_column("diagram_requests", "dsl_code")
