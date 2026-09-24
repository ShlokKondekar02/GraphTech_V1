"""Protected /api/me endpoint — proof that the session actually gates access."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.users import User
from app.schemas.users import UserResponse

router = APIRouter(tags=["Me"])


@router.get("/me", response_model=UserResponse, summary="Return authenticated user profile")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the profile of the currently authenticated user.
    Requires a valid session cookie — returns 401 if absent or expired.
    """
    return current_user
