"""Sprint 1 — Add HNSW vector index on diagram_requests.embedding

Revision ID: 0003_vector_index
Revises: 0002_add_google_id
Create Date: 2026-09-25

pgvector 0.8.x supports both ivfflat and hnsw.  We use hnsw here because it
gives better recall at query time without needing to pre-set nlist/nprobe, and
it supports incremental inserts without degrading performance.  The operator
class ``vector_cosine_ops`` matches our cosine-similarity queries (<=>).

Index parameters chosen conservatively for a development/small dataset:
  m          = 16   (connections per node — default)
  ef_construction = 64  (search width during build — default)

These can be tuned upward in production via a separate migration.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0003_vector_index"
down_revision: Union[str, None] = "0002_add_google_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # hnsw index for cosine similarity (<=>)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_diagram_requests_embedding_hnsw
        ON diagram_requests
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_diagram_requests_embedding_hnsw")
