from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class DiagramGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language prompt describing the diagram")
    renderer_preference: Optional[str] = Field(None, description="Optional preferred renderer (e.g. mermaid, plantuml, graphviz)")


class DiagramResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    prompt: str
    structured_json: Optional[Dict[str, Any]] = None
    complexity: Optional[str] = None
    renderer: Optional[str] = None
    diagram_type: Optional[str] = None
    status: str
    output_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
