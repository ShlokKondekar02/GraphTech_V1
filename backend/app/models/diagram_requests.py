import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base


class DiagramRequest(Base):
    __tablename__ = "diagram_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    prompt = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=True)
    structured_json = Column(JSONB, nullable=True)
    complexity = Column(String(50), nullable=True)
    renderer = Column(String(50), nullable=True)
    diagram_type = Column(String(50), nullable=True)
    status = Column(String(50), default="pending", nullable=False)
    output_path = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="diagram_requests")
