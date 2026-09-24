"""
Google OAuth 2.0 Authorization Code flow.

Endpoints
---------
GET  /api/auth/google/login     — redirect browser to Google consent screen
GET  /api/auth/google/callback  — exchange code, upsert user, set httpOnly JWT cookie
GET  /api/auth/session          — return current authenticated user or 401
POST /api/auth/logout           — clear the session cookie
"""

import secrets
import urllib.parse
from datetime import timedelta

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token, get_current_user
from app.models.users import User
from app.schemas.users import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ──────────────────────────────────────────────────────────────
# Google OAuth constants
# ──────────────────────────────────────────────────────────────
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds


# ──────────────────────────────────────────────────────────────
# GET /api/auth/google/login
# ──────────────────────────────────────────────────────────────
@router.get("/google/login", summary="Redirect to Google consent screen")
async def google_login(response: Response):
    """Build the Google OAuth authorization URL and redirect the browser."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured (GOOGLE_CLIENT_ID missing).",
        )

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    redirect = RedirectResponse(url=auth_url)
    # Store state in a short-lived httpOnly cookie for CSRF validation
    redirect.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600,  # 10 min
        secure=settings.ENVIRONMENT == "production",
    )
    return redirect


# ──────────────────────────────────────────────────────────────
# GET /api/auth/google/callback
# ──────────────────────────────────────────────────────────────
@router.get("/google/callback", summary="Handle Google OAuth callback")
async def google_callback(
    code: str,
    state: str,
    response: Response,
    db: Session = Depends(get_db),
    oauth_state: str = Cookie(default=None),
):
    """
    Exchange the authorization code for tokens, fetch the Google user profile,
    upsert into the `users` table, and set a signed JWT in an httpOnly cookie.
    """
    # ── CSRF state validation ──────────────────────────────────
    if not oauth_state or oauth_state != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state.")

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured.",
        )

    # ── Exchange code for tokens ───────────────────────────────
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google token exchange failed: {token_response.text}",
        )

    token_data = token_response.json()
    google_access_token = token_data.get("access_token")
    if not google_access_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No access_token in Google response.")

    # ── Fetch user profile from Google ─────────────────────────
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
        )

    if userinfo_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch Google user info.",
        )

    userinfo = userinfo_response.json()
    google_id: str = userinfo.get("sub")
    email: str = userinfo.get("email", "")
    name: str = userinfo.get("name", "")
    avatar_url: str = userinfo.get("picture", "")

    if not google_id or not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incomplete profile from Google.")

    # ── Upsert user in database ────────────────────────────────
    user = db.query(User).filter(User.google_id == google_id).first()
    if user is None:
        # Try to find by email (e.g. if they had an account before OAuth was added)
        user = db.query(User).filter(User.email == email).first()

    if user is None:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
        db.add(user)
    else:
        # Update mutable fields on each login
        user.google_id = google_id
        user.name = name
        user.avatar_url = avatar_url

    db.commit()
    db.refresh(user)

    # ── Issue JWT in httpOnly cookie ───────────────────────────
    jwt_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    redirect = RedirectResponse(url=settings.FRONTEND_URL, status_code=302)
    redirect.delete_cookie("oauth_state")
    redirect.set_cookie(
        key=COOKIE_NAME,
        value=jwt_token,
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        secure=settings.ENVIRONMENT == "production",
    )
    return redirect


# ──────────────────────────────────────────────────────────────
# GET /api/auth/session
# ──────────────────────────────────────────────────────────────
@router.get("/session", response_model=UserResponse, summary="Return current session user")
async def get_session(
    access_token: str = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """Return the authenticated user derived from the session cookie, or 401."""
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(access_token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session payload")

    try:
        import uuid as _uuid
        user_uuid = _uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session payload")

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


# ──────────────────────────────────────────────────────────────
# POST /api/auth/logout
# ──────────────────────────────────────────────────────────────
@router.post("/logout", summary="Clear session cookie")
async def logout(response: Response):
    """Clear the httpOnly JWT cookie to end the session."""
    response.delete_cookie(key=COOKIE_NAME, samesite="lax")
    return {"message": "Logged out successfully"}
