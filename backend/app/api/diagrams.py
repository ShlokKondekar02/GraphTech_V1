from fastapi import APIRouter

router = APIRouter(prefix="/diagrams", tags=["Diagrams"])


@router.get("/")
async def list_diagrams_placeholder():
    """Placeholder for listing user diagram requests."""
    return {"diagrams": []}
