"""
History API Endpoints -- Sprint 5.

Provides CRUD endpoints for managing user diagram generation history:
  - GET /api/history: List all persisted diagram requests (sorted by created_at desc)
  - GET /api/history/{id}: Fetch single diagram request full specification & SVG
  - DELETE /api/history/{id}: Remove a diagram request from persistent storage
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.diagram_requests import DiagramRequest
from app.schemas.diagrams import GenerateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History"])


@router.get(
    "",
    response_model=List[Dict[str, Any]],
    summary="List persisted diagram request history",
    description="Returns chronological history of diagram requests from the database.",
)
def list_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Fetch history items sorted by creation timestamp descending.
    """
    rows = (
        db.query(DiagramRequest)
        .order_by(desc(DiagramRequest.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for r in rows:
        title = "Architecture Diagram"
        if r.structured_json and isinstance(r.structured_json, dict):
            attrs = r.structured_json.get("attributes", {})
            title = attrs.get("title", title)

        nodes_count = 0
        edges_count = 0
        if r.structured_json and isinstance(r.structured_json, dict):
            nodes_count = len(r.structured_json.get("nodes", []))
            edges_count = len(r.structured_json.get("edges", []))

        results.append({
            "id": str(r.id),
            "prompt": r.prompt,
            "title": title,
            "type": r.diagram_type or "architecture",
            "diagram_type": r.diagram_type or "architecture",
            "renderer": r.renderer or "mermaid",
            "complexity": r.complexity or "Moderate",
            "status": r.status,
            "source": r.source or "fresh",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "nodesCount": nodes_count,
            "edgesCount": edges_count,
            "dsl_code": r.dsl_code,
            "svg_content": r.svg_content,
            "dslCode": r.dsl_code,
            "svgContent": r.svg_content,
            "attempt_count": r.attempt_count or 1,
            "validation_status": r.validation_status or r.status,
            "structured_json": r.structured_json,
        })

    return results


@router.get(
    "/{request_id}",
    response_model=Dict[str, Any],
    summary="Get single diagram request from history",
)
def get_history_item(
    request_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Fetch full detail of a specific diagram request by UUID.
    """
    try:
        req_uuid = uuid.UUID(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {request_id}") from exc

    row = db.query(DiagramRequest).filter(DiagramRequest.id == req_uuid).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Diagram request {request_id} not found")

    title = "Architecture Diagram"
    if row.structured_json and isinstance(row.structured_json, dict):
        title = row.structured_json.get("attributes", {}).get("title", title)

    return {
        "id": str(row.id),
        "prompt": row.prompt,
        "title": title,
        "type": row.diagram_type or "architecture",
        "diagram_type": row.diagram_type or "architecture",
        "renderer": row.renderer or "mermaid",
        "complexity": row.complexity or "Moderate",
        "status": row.status,
        "source": row.source or "fresh",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "structured_json": row.structured_json,
        "dsl_code": row.dsl_code,
        "svg_content": row.svg_content,
        "dslCode": row.dsl_code,
        "svgContent": row.svg_content,
        "attempt_count": row.attempt_count or 1,
        "validation_status": row.validation_status or row.status,
        "repair_history": row.repair_history,
    }


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete diagram request from history",
)
def delete_history_item(
    request_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Delete a persisted diagram request by UUID.
    """
    try:
        req_uuid = uuid.UUID(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {request_id}") from exc

    row = db.query(DiagramRequest).filter(DiagramRequest.id == req_uuid).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Diagram request {request_id} not found")

    db.delete(row)
    db.commit()
    logger.info("Deleted diagram_request id=%s from history", request_id)
    return {"success": True, "message": f"Deleted diagram request {request_id}", "id": request_id}
