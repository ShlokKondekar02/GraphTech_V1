"""Security utilities: JWT creation/verification and the get_current_user FastAPI dependency."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT containing *data* with an expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SESSION_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT. Returns payload dict or None on any error."""
    try:
        payload = jwt.decode(token, settings.SESSION_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(
    access_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """FastAPI dependency — reads the httpOnly cookie, verifies JWT, loads User from DB.

    Raises 401 if the cookie is missing, the JWT is invalid, or the user no longer exists.
    """
    from app.models.users import User  # local import to avoid circular deps

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not access_token:
        raise credentials_exception

    payload = decode_access_token(access_token)
    if payload is None:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise credentials_exception

    return user
