from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me")
async def get_current_user_placeholder():
    """Placeholder for authenticated user profile endpoint."""
    return {"message": "Auth endpoint placeholder"}
