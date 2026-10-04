"""
DiagramRequest SQLAlchemy model -- updated for Sprint 2.

Sprint 2 additions:
  rejection_reason  -- human-readable reason for any rejection (TEXT)
  complexity_score  -- independently computed float score (FLOAT)
  complexity_metrics -- full metrics dict (JSONB) -- all computed fields
  source            -- "fresh" | "cache" -- origin of the structured_json

Status vocabulary (status column):
  "pending"              -- row created but pipeline not yet run (legacy)
  "validated"            -- fresh generation passed all checks, ready for Sprint 3 rendering
  "cache_reused"         -- returned from pgvector cache after re-validation
  "rejected_invalid"     -- failed Pydantic or graph validation
  "rejected_complexity"  -- valid structure but complexity exceeds ceiling
  "error"                -- unexpected runtime failure during the pipeline
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base


class DiagramRequest(Base):
    __tablename__ = "diagram_requests"

    # ---- Primary key & foreign keys ----------------------------------------
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # ---- Core prompt / embedding -------------------------------------------
    prompt = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=True)

    # ---- Structured output -------------------------------------------------
    structured_json = Column(JSONB, nullable=True)
    diagram_type = Column(String(50), nullable=True)

    # ---- Complexity (always independently computed -- NEVER from Groq) -----
    complexity = Column(String(50), nullable=True)         # label bucket
    complexity_score = Column(Float, nullable=True)         # raw float score
    complexity_metrics = Column(JSONB, nullable=True)       # full metrics dict

    # ---- Pipeline metadata -------------------------------------------------
    renderer = Column(String(50), nullable=True)            # set in Sprint 3
    dsl_code = Column(Text, nullable=True)                  # set in Sprint 3
    svg_content = Column(Text, nullable=True)               # set in Sprint 3
    source = Column(String(20), nullable=True)              # "fresh" | "cache"
    status = Column(String(50), default="pending", nullable=False, index=True)
    rejection_reason = Column(Text, nullable=True)          # non-null on rejection
    output_path = Column(String(1024), nullable=True)       # set in Sprint 3

    # ---- Timestamps --------------------------------------------------------
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ---- Relationships -----------------------------------------------------
    user = relationship("User", back_populates="diagram_requests")
